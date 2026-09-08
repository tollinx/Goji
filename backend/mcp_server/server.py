"""MCP server exposing retrieval tools over the Goji & Gin drink corpus.

Run directly (``python -m mcp_server.server``) to serve over stdio. The
FastAPI backend spawns this as a subprocess via mcp_client.py; it can also be
added to Claude Desktop's MCP config to ask about drinks from a normal chat.
"""

from mcp.server.fastmcp import FastMCP

from mcp_server import corpus

mcp = FastMCP("goji-drinks")


@mcp.tool()
def search_drinks(query: str, top_k: int = 3) -> list[dict]:
    """Semantically search the drink corpus for the best matching recipes.

    Always call this before recommending a drink — never invent one outside
    what this tool returns.

    Args:
        query: The mood, flavor, or occasion described by the user.
        top_k: How many candidate drinks to return, ranked by relevance.
    """
    return corpus.search(query, top_k=top_k)


@mcp.tool()
def get_drink(drink_id: str) -> dict:
    """Fetch the full recipe (base, additions, method) for a drink id.

    Use this after search_drinks to get the exact ingredients and steps to
    quote back to the user.

    Args:
        drink_id: The id returned by search_drinks, e.g. "osmanthus-gin-sour".
    """
    drink = corpus.get(drink_id)
    if drink is None:
        return {"error": f"No drink found with id '{drink_id}'"}
    return drink


if __name__ == "__main__":
    mcp.run()
