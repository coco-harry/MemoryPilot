"""
Read-only sanity check: connects to Base mainnet and prints the agent
wallet's ETH balance (for gas) and USDC balance (for x402 payments).

No transactions are sent. This just confirms the wallet is funded and
reachable before we build payment logic on top of it.
"""

import os
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

BASE_RPC = "https://mainnet.base.org"
USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

# Minimal ERC-20 ABI, just the two functions we need
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]


def main():
    private_key = os.environ["AGENT_WALLET_PRIVATE_KEY"]
    account = Account.from_key(private_key)
    address = account.address

    print(f"Agent wallet address: {address}\n")

    w3 = Web3(Web3.HTTPProvider(BASE_RPC))

    if not w3.is_connected():
        print("Could not connect to Base RPC. Check your internet connection.")
        return

    print(f"Connected to Base (chain id: {w3.eth.chain_id})\n")

    # ETH balance (for gas)
    eth_balance_wei = w3.eth.get_balance(address)
    eth_balance = w3.from_wei(eth_balance_wei, "ether")
    print(f"ETH balance:  {eth_balance} ETH")

    # USDC balance (ERC-20 token)
    usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
    usdc_raw = usdc_contract.functions.balanceOf(address).call()
    usdc_decimals = usdc_contract.functions.decimals().call()
    usdc_balance = usdc_raw / (10 ** usdc_decimals)
    print(f"USDC balance: {usdc_balance} USDC")


if __name__ == "__main__":
    main()
