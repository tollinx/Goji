"""Connection to the goji-drinks MCP server subprocess.

The server is spawned once at app startup and one ClientSession is kept open
for the app's lifetime, rather than starting a subprocess per request.
"""

import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import settings

BACKEND_ROOT = Path(__file__).parent.parent


class MCPConnection:
    """Owns the MCP subprocess, its session, and the tool list it advertises."""

    def __init__(self) -> None:
        self.session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None
        # Provider-neutral: {"name", "description", "parameters"} where
        # parameters is the tool's JSON Schema. generation.py reshapes these
        # into whichever format the configured LLM expects.
        self.tools: list[dict] = []

    async def connect(self) -> None:
        self._stack = AsyncExitStack()

        env = os.environ.copy()
        env["EMBEDDING_MODEL"] = settings.EMBEDDING_MODEL

        # sys.executable keeps the subprocess on the same interpreter as the
        # API, so it inherits the venv without needing it to be activated.
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            cwd=str(BACKEND_ROOT),
            env=env,
        )

        read, write = await self._stack.enter_async_context(stdio_client(server_params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

        listed = await self.session.list_tools()
        self.tools = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            }
            for tool in listed.tools
        ]

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call an MCP tool and decode its JSON text blocks back to Python."""
        if self.session is None:
            raise RuntimeError("MCP session is not connected")

        result = await self.session.call_tool(name, arguments)

        # FastMCP serializes each returned value as a JSON text block: one
        # block for a dict, one per element for a list.
        values = []
        for block in result.content:
            text = getattr(block, "text", None)
            if text is None:
                continue
            try:
                values.append(json.loads(text))
            except json.JSONDecodeError:
                values.append(text)

        return values[0] if len(values) == 1 else values

    async def close(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self.session = None


mcp_connection = MCPConnection()
