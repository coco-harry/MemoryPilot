"""
Debug script: prints the RAW result of calling memory_list, with no
assumptions about its shape. Run this to see exactly what structure
memory_list actually returns, so we can fix load_known_facts() in
agent.py to match reality instead of a guess.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(command="sibyl-memory-mcp", args=[], env=None)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("memory_list", arguments={"limit": 50})

            print("Raw content blocks:")
            for block in result.content:
                if block.type == "text":
                    print(block.text)
                    print("\nParsed as JSON:")
                    print(json.dumps(json.loads(block.text), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
