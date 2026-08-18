"""
Shared helper for talking to Sibyl Memory through its MCP server.

Both session1_save.py and session2_recall.py import from here.
Each script run is its OWN process (its own Python interpreter), so
there is zero shared memory between them at the code level -- the
ONLY thing connecting session 1 and session 2 is whatever got written
to Sibyl's SQLite database on disk. That's what makes the "genuinely
fresh session" proof honest.
"""

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager


@asynccontextmanager
async def sibyl_session():
    """Open a connection to the sibyl-memory-mcp server for one call block."""
    server_params = StdioServerParameters(
        command="sibyl-memory-mcp",
        args=[],
        env=None,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def remember(category: str, name: str, body: dict):
    """Save something to long-term memory. Returns the tool's raw result."""
    async with sibyl_session() as session:
        result = await session.call_tool(
            "memory_remember",
            arguments={"category": category, "name": name, "body": body},
        )
        return result


async def recall(category: str, name: str):
    """
    Read something back from long-term memory.
    Returns the parsed entity dict, or None if not found.
    """
    async with sibyl_session() as session:
        result = await session.call_tool(
            "memory_recall",
            arguments={"category": category, "name": name},
        )
        # MCP tool results come back as a list of content blocks;
        # for this server it's a single text block containing JSON.
        import json
        for block in result.content:
            if block.type == "text":
                data = json.loads(block.text)
                if data.get("ok"):
                    return data["entity"]
                return None
        return None


async def search(query: str, limit: int = 10):
    """Full-text search across memory. Returns the raw parsed JSON result."""
    async with sibyl_session() as session:
        result = await session.call_tool(
            "memory_search",
            arguments={"query": query, "limit": limit},
        )
        import json
        for block in result.content:
            if block.type == "text":
                return json.loads(block.text)
        return None


async def list_all(category: str | None = None, limit: int = 50):
    """List entities, optionally filtered by category."""
    async with sibyl_session() as session:
        result = await session.call_tool(
            "memory_list",
            arguments={"category": category, "limit": limit},
        )
        import json
        for block in result.content:
            if block.type == "text":
                return json.loads(block.text)
        return None
