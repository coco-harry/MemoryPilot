"""
First real test of x402 payments on Base mainnet.

This makes ONE real paid web search request to Exa's API. The agent
wallet automatically pays a few cents of USDC (on Base) to unlock the
result. This proves the whole mechanism -- discovery, signing, payment,
on-chain settlement -- works end to end with real money before we wire
it into the main agent.

Cost: about $0.007 (less than a cent) for this one search.
"""

import os
import json
import base64
import requests
from eth_account import Account
from dotenv import load_dotenv

from x402 import x402ClientSync
from x402.http.clients import wrapRequestsWithPayment
from x402.mechanisms.evm.exact import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner

load_dotenv()


def main():
    private_key = os.environ["AGENT_WALLET_PRIVATE_KEY"]
    account = Account.from_key(private_key)
    print(f"Paying from agent wallet: {account.address}\n")

    client = x402ClientSync()
    register_exact_evm_client(
        client,
        EthAccountSigner(account),
        networks="eip155:*",
    )

    session = wrapRequestsWithPayment(requests.Session(), client)

    print("Sending paid search request to Exa...\n")
    response = session.post(
        "https://api.exa.ai/search",
        json={
            "query": "Base blockchain latest news",
            "numResults": 3,
        },
    )

    print(f"HTTP status: {response.status_code}\n")

    if response.status_code != 200:
        print("Request did not succeed. Raw response:")
        print(response.text)
        return

    data = response.json()
    print("Search results:")
    for result in data.get("results", []):
        print(f"  - {result.get('title')}  ({result.get('url')})")

    payment_response_header = response.headers.get("PAYMENT-RESPONSE")
    if payment_response_header:
        receipt = json.loads(base64.b64decode(payment_response_header))
        print("\nPayment settled on-chain.")
        print(f"Transaction hash: {receipt.get('transaction')}")
        print(f"View on BaseScan: https://basescan.org/tx/{receipt.get('transaction')}")
    else:
        print("\nNo PAYMENT-RESPONSE header found -- check if payment was actually required.")


if __name__ == "__main__":
    main()
