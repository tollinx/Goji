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
You may call get_drink to pull the exact recipe for the drink you're about to recommend.

Only ever recommend a drink that search_drinks actually returned — never invent
a drink or improvise a recipe that isn't in the corpus. If nothing in the
search results is a good match for the request, say so plainly and suggest the
closest option instead of pretending it's a perfect fit.

Keep the answer short: which drink, why it fits what they asked for, and the
key build details (spirit, amount, one line of method). Talk like a bartender,
not a search engine."""

GAVE_UP = "I couldn't settle on a recommendation — try rephrasing what you're in the mood for."


class GenerationError(RuntimeError):
    """Configuration we can detect ourselves. Surfaced as a 503."""


def _drink_ref(tool_name: str, result: Any) -> dict | None:
    """Pick out which drink a tool result points at, for the API response."""
    if tool_name == "get_drink" and isinstance(result, dict) and "id" in result:
        return {"id": result["id"], "name": result["name"]}
    # Fall back to the top search hit, in case the model answers without
    # calling get_drink.
    if tool_name == "search_drinks" and isinstance(result, list) and result:
        return {"id": result[0]["id"], "name": result[0]["name"]}
    return None


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
        for tool in _require_tools()
    ]

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    drink: dict | None = None

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
            return {"answer": message.content or "", "drink": drink}

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
            result = await mcp_connection.call_tool(call.function.name, arguments)
            drink = _drink_ref(call.function.name, result) or drink
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

    return {"answer": GAVE_UP, "drink": drink}


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
        for tool in _require_tools()
    ]

    messages: list[dict] = [{"role": "user", "content": question}]
    drink: dict | None = None

    for _ in range(MAX_TURNS):
        response = await client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            answer = "".join(block.text for block in response.content if block.type == "text")
            return {"answer": answer, "drink": drink}

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = await mcp_connection.call_tool(block.name, block.input)
            drink = _drink_ref(block.name, result) or drink
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return {"answer": GAVE_UP, "drink": drink}


async def ask(question: str) -> dict:
    """Answer a question with the configured provider. Returns {answer, drink}."""
    if settings.LLM_PROVIDER == "groq":
        return await _ask_groq(question)
    return await _ask_anthropic(question)
