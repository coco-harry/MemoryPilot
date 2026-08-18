"""
SESSION 2 -- run this in a NEW terminal / NEW process, after session1_save.py
has already finished and exited.

This script has no idea what happened in session 1. It starts fresh,
recalls whatever is in Sibyl Memory, and asks an investment question
to the LLM TWICE:

  Decision A: the LLM answers with NO memory context (baseline).
  Decision B: the LLM answers WITH the recalled preference injected.

If A and B differ, the recalled memory is what caused the difference --
that's the core proof the hackathon requires.
"""

import asyncio
import os
from openai import OpenAI
from dotenv import load_dotenv
from memory_client import recall

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "anthropic/claude-sonnet-5"

QUESTION = (
    "A friend is offering me a chance to put money into a brand-new "
    "crypto token that just launched. Should I do it, and how much "
    "should I put in?"
)


def ask_llm(system_prompt: str, question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


async def main():
    print("SESSION 2 (fresh process, no memory of session 1)")
    print("=" * 50)

    print("Step 1 -- Decision A: asking the LLM with NO memory context...\n")
    decision_a = ask_llm(
        system_prompt="You are a helpful financial assistant. Give a short, direct recommendation.",
        question=QUESTION,
    )
    print("DECISION A (no memory):")
    print(decision_a)
    print("\n" + "-" * 50 + "\n")

    print("Step 2 -- Recalling saved preference from Sibyl Memory...\n")
    entity = await recall(category="preferences", name="risk_tolerance")

    if entity is None:
        print("Nothing found in memory. Did you run session1_save.py first?")
        return

    remembered_statement = entity["body"]["statement"]
    print(f"Recalled: \"{remembered_statement}\"")
    print(f"(Saved at: {entity['created_at']})\n")

    print("Step 3 -- Decision B: asking the LLM WITH the recalled memory...\n")
    decision_b = ask_llm(
        system_prompt=(
            "You are a helpful financial assistant. Give a short, direct "
            f"recommendation. Important context you remember about this "
            f"user: \"{remembered_statement}\""
        ),
        question=QUESTION,
    )
    print("DECISION B (with recalled memory):")
    print(decision_b)
    print("\n" + "=" * 50)
    print("Compare Decision A vs Decision B above.")
    print("If B is visibly more conservative / references the $100 limit,")
    print("the recalled memory caused a real behavior change.")


if __name__ == "__main__":
    asyncio.run(main())
