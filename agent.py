"""
MemoryPilot -- the real interactive agent.

Run this, have a conversation. The agent:
  1. On startup, automatically loads whatever it already knows about you
     from Sibyl Memory (genuine fresh-session recall, not scripted).
  2. During the conversation, the LLM itself decides when something is
     worth remembering (e.g. a stated preference or constraint) and
     calls the "remember_fact" tool on its own.
  3. Uses remembered facts to change its actual recommendations.

Each run of this script is a brand new process -- nothing survives
between runs except what's in Sibyl's database on disk.
"""

import asyncio
import json
import os
import base64
import requests
from openai import OpenAI
from dotenv import load_dotenv
from eth_account import Account
from x402 import x402ClientSync
from x402.http.clients import wrapRequestsWithPayment
from x402.mechanisms.evm.exact import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner
from memory_client import remember, search, list_all

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "anthropic/claude-sonnet-5"

# Set up the paid web search client (x402 on Base) once, at startup
_agent_account = Account.from_key(os.environ["AGENT_WALLET_PRIVATE_KEY"])
_x402_client = x402ClientSync()
register_exact_evm_client(_x402_client, EthAccountSigner(_agent_account), networks="eip155:*")
_paid_session = wrapRequestsWithPayment(requests.Session(), _x402_client)


def paid_web_search(query: str) -> str:
    """
    Performs a real web search by autonomously paying a small amount of
    USDC on Base to Exa's search API via the x402 protocol. Returns the
    results as a string, plus the on-chain transaction hash as proof.
    """
    response = _paid_session.post(
        "https://api.exa.ai/search",
        json={"query": query, "numResults": 3},
    )
    if response.status_code != 200:
        return f"Search failed (status {response.status_code}): {response.text}"

    data = response.json()
    lines = []
    for r in data.get("results", []):
        lines.append(f"- {r.get('title')} ({r.get('url')})")

    payment_header = response.headers.get("PAYMENT-RESPONSE")
    tx_hash = None
    if payment_header:
        receipt = json.loads(base64.b64decode(payment_header))
        tx_hash = receipt.get("transaction")

    result = "Search results:\n" + "\n".join(lines)
    if tx_hash:
        result += f"\n\n(Paid for via Base on-chain transaction: {tx_hash})"
    return result

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": (
                "Save an important, durable fact about the user to long-term "
                "memory -- a stated preference, constraint, or piece of "
                "context that should influence future advice. Do NOT save "
                "small talk or one-off details that don't matter later."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Grouping, e.g. 'preferences', 'facts', 'goals'.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Short unique key, e.g. 'risk_tolerance'.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "The fact itself, in plain language.",
                    },
                },
                "required": ["category", "name", "summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search long-term memory for anything relevant to the current question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search terms."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "paid_web_search",
            "description": (
                "Search the live web for current information (e.g. news about "
                "a specific crypto token, project, or company) by autonomously "
                "paying a small amount of USDC on Base. Use this when you need "
                "up-to-date, real-world information to evaluate something the "
                "user is asking about -- not for general knowledge you already have."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                },
                "required": ["query"],
            },
        },
    },
]


async def run_tool(name: str, args: dict) -> str:
    """Execute a tool call the LLM asked for, return a string result."""
    if name == "remember_fact":
        await remember(
            category=args["category"],
            name=args["name"],
            body={"summary": args["summary"]},
        )
        return f"Saved to memory: [{args['category']}/{args['name']}] {args['summary']}"

    if name == "search_memory":
        result = await search(args["query"])
        return json.dumps(result)

    if name == "paid_web_search":
        return paid_web_search(args["query"])

    return f"Unknown tool: {name}"


async def load_known_facts() -> str:
    """Pull everything currently in memory to seed the system prompt."""
    result = await list_all(limit=50)
    if not result or not result.get("results"):
        return "You don't know anything about this user yet."

    lines = ["Here is what you already know about this user, from past sessions:"]
    for entity in result["results"]:
        summary = entity["body"].get("summary", entity["body"])
        lines.append(f"- [{entity['category']}/{entity['name']}] {summary}")
    return "\n".join(lines)


async def main():
    print("MemoryPilot -- risk-aware investment assistant")
    print("Loading what I remember about you...\n")

    known_facts = await load_known_facts()
    print(known_facts)
    print("\n(Type 'exit' to end the session.)\n")

    system_prompt = (
        "You are MemoryPilot, a cautious, helpful financial assistant. "
        "You have persistent memory across sessions via tools. "
        "When the user states a preference, constraint, or important fact "
        "about themselves, call remember_fact to save it. "
        "Use what you already know (below) to tailor every recommendation.\n\n"
        f"{known_facts}"
    )

    messages = [{"role": "system", "content": system_prompt}]

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Session ending. Nothing else is kept except what's in memory.")
            break
        if not user_input:
            continue  # ignore stray blank lines (e.g. from a multi-line paste)

        messages.append({"role": "user", "content": user_input})

        # Loop in case the model chains multiple tool calls
        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg.model_dump(exclude_none=True))
                for call in msg.tool_calls:
                    args = json.loads(call.function.arguments)
                    result = await run_tool(call.function.name, args)
                    print(f"  [agent used tool: {call.function.name}] {result}")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": result,
                        }
                    )
                continue  # let the model respond to the tool result

            print(f"Agent: {msg.content}\n")
            messages.append({"role": "assistant", "content": msg.content})
            break


if __name__ == "__main__":
    asyncio.run(main())
