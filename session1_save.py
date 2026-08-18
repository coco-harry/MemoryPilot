"""
SESSION 1 -- run this first.

Simulates the user telling the agent something meaningful. The agent
saves it to Sibyl Memory, then this process exits completely.
Nothing is kept in memory (RAM) after this script ends -- only what's
written to Sibyl's SQLite database on disk survives.
"""

import asyncio
from memory_client import remember


USER_STATEMENT = (
    "I prefer conservative decisions. I don't want recommendations "
    "involving more than $100 of risk."
)


async def main():
    print("SESSION 1")
    print("=" * 50)
    print(f"User says: \"{USER_STATEMENT}\"\n")

    print("Agent: Saving this to long-term memory...")
    result = await remember(
        category="preferences",
        name="risk_tolerance",
        body={
            "statement": USER_STATEMENT,
            "max_risk_usd": 100,
            "style": "conservative",
        },
    )
    print("Agent: Saved.\n")
    print("Raw tool result:", result)
    print("\nSession 1 ending now. Close this terminal or press Ctrl+C.")
    print("Then open a NEW terminal and run session2_recall.py for the fresh-session test.")


if __name__ == "__main__":
    asyncio.run(main())
