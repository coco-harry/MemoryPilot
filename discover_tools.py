"""
Diagnostic script: connects to the sibyl-memory-mcp server (the same one
Claude Code was just wired up to use) and prints every tool it exposes,
along with the exact input schema for each one.

We run this BEFORE writing any real save/recall code, so we know the real
tool names and parameters instead of guessing.
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="sibyl-memory-mcp",
        args=[],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()

            print(f"\nFound {len(tools_result.tools)} tool(s) on sibyl-memory-mcp:\n")
            print("=" * 70)

            for tool in tools_result.tools:
                print(f"\nTool name: {tool.name}")
                print(f"Description: {tool.description}")
                print("Input schema:")
                import json
                print(json.dumps(tool.inputSchema, indent=2))
                print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
