"""Tool-calling loop: question in, drink recommendation out.

Retrieval never happens here. This module orchestrates the conversation and
forwards the model's tool calls to the MCP server, so the corpus stays behind
the search_drinks / get_drink tools.

Two providers are supported, selected by LLM_PROVIDER. They each get their own
loop rather than a shared abstraction: the SDKs disagree about tool schemas,
how tool calls come back, and how results are fed in, so one adapter would leak
those differences anyway. The loops are short and the shared pieces (prompt,
turn cap, drink extraction) live above them.
"""

import json
from typing import Any

from anthropic import AsyncAnthropic
from groq import AsyncGroq

from app.config import settings
from app.mcp_client import mcp_connection

# Each turn is one model call. Two covers the normal path (search, then
# answer); the headroom lets it also fetch a full recipe before answering
# without ever looping indefinitely.
MAX_TURNS = 4

SYSTEM_PROMPT = """You are the bartender for Goji & Gin, a four drink home cocktail menu.

Always call search_drinks first to find candidates for what the user describes.
You may call get_drink if you need more detail about one before deciding.

Only ever pick a drink that search_drinks actually returned — never invent a
drink that isn't in the corpus. If nothing in the search results is a good
match, say so plainly and offer the closest option rather than pretending it
fits.

search_drinks ranks by similarity, which is a starting point, not the decision.
Read the candidates and pick the one that genuinely fits — it is often not the
top hit.

When you've decided, call recommend_drink. That is how you answer; do not reply
with plain text instead. Its `why` is two or three sentences on why this drink
matches what they asked for — the flavors, the effort, or the occasion they
mentioned. Talk like a bartender, not a search engine.

Three hard rules for `why`:
- No recipe. No ingredients, measurements, or method — explain the match.
- Don't name the drink. Its name is already on screen directly above your text,
  so repeating it reads twice. Start with "It" or with the flavor itself.
- Plain sentences. No markdown, no bold, no bullet points, no headings.

The one time to break the naming rule: if nothing really fits, say so first
("We don't have a true X, but...") so they know it's a substitute."""

GAVE_UP = "I couldn't settle on a recommendation — try rephrasing what you're in the mood for."


class GenerationError(RuntimeError):
    """Configuration we can detect ourselves. Surfaced as a 503."""


# The model answers by calling this rather than replying with text, so the
# drink it picked is stated outright. Inferring it from the last tool result
# got this wrong: search_drinks ranks by embedding similarity, and the model
# frequently (correctly) chooses a lower-ranked candidate.
RECOMMEND_TOOL = {
    "name": "recommend_drink",
    "description": (
        "Give your final answer. Call this once you have decided which drink to "
        "recommend. Do not reply with plain text instead."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "drink_id": {
                "type": "string",
                "description": "id of the chosen drink, exactly as search_drinks returned it.",
            },
            "why": {
                "type": "string",
                "description": (
                    "Two or three plain sentences on why this drink matches the request. "
                    "No recipe, no measurements, no markdown."
                ),
            },
        },
        "required": ["drink_id", "why"],
    },
}


async def _finish(arguments: dict) -> dict | None:
    """Resolve a recommend_drink call into the API response.

    Looks the id up in the corpus, which both supplies the canonical name and
    rejects an id the model invented. Returns None if the id is unknown, so the
    caller can ask the model to try again.
    """
    record = await mcp_connection.call_tool(
        "get_drink", {"drink_id": arguments.get("drink_id", "")}
    )
    if not isinstance(record, dict) or "id" not in record:
        return None
    return {
        "answer": (arguments.get("why") or "").strip(),
        "drink": {"id": record["id"], "name": record["name"]},
    }


def _require(api_key: str, env_var: str) -> str:
    if not api_key:
        raise GenerationError(f"{env_var} is not set. Add it to backend/.env and restart.")
    return api_key


def _require_tools() -> list[dict]:
    # Without the retrieval tools the model would answer from memory, which is
    # exactly what this app must never do.
    if not mcp_connection.tools:
        raise GenerationError("The drink search tools aren't available. Is the MCP server running?")
    return mcp_connection.tools


# --- Groq (OpenAI-compatible tool calling) ---------------------------------

_groq_client: AsyncGroq | None = None


def _get_groq() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=_require(settings.GROQ_API_KEY, "GROQ_API_KEY"))
    return _groq_client


async def _ask_groq(question: str) -> dict:
    client = _get_groq()
    tools = [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        }
        for tool in [*_require_tools(), RECOMMEND_TOOL]
    ]

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for _ in range(MAX_TURNS):
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            max_tokens=settings.MAX_TOKENS,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            # The model answered in prose instead of calling recommend_drink,
            # so there's no reliable drink to name alongside it.
            return {"answer": message.content or "", "drink": None}

        # Echo the assistant turn back explicitly rather than dumping the SDK
        # model, so only fields the API accepts are sent.
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in message.tool_calls
                ],
            }
        )

        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")

            if call.function.name == "recommend_drink":
                answer = await _finish(arguments)
                if answer is not None:
                    return answer
                result: Any = {"error": "Unknown drink_id. Use one search_drinks returned."}
            else:
                result = await mcp_connection.call_tool(call.function.name, arguments)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

    return {"answer": GAVE_UP, "drink": None}


# --- Anthropic -------------------------------------------------------------

_anthropic_client: AsyncAnthropic | None = None


def _get_anthropic() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = AsyncAnthropic(
            api_key=_require(settings.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY")
        )
    return _anthropic_client


async def _ask_anthropic(question: str) -> dict:
    client = _get_anthropic()
    tools = [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["parameters"],
        }
        for tool in [*_require_tools(), RECOMMEND_TOOL]
    ]

    messages: list[dict] = [{"role": "user", "content": question}]

    for _ in range(MAX_TURNS):
        response = await client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            # Answered in prose instead of calling recommend_drink, so there's
            # no reliable drink to name alongside it.
            answer = "".join(block.text for block in response.content if block.type == "text")
            return {"answer": answer, "drink": None}

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "recommend_drink":
                answer = await _finish(block.input)
                if answer is not None:
                    return answer
                result: Any = {"error": "Unknown drink_id. Use one search_drinks returned."}
            else:
                result = await mcp_connection.call_tool(block.name, block.input)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return {"answer": GAVE_UP, "drink": None}


async def ask(question: str) -> dict:
    """Answer a question with the configured provider. Returns {answer, drink}."""
    if settings.LLM_PROVIDER == "groq":
        return await _ask_groq(question)
    return await _ask_anthropic(question)
