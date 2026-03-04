"""Search for available phone numbers and buy one.

Prerequisites:
    pip install plivo_agent

Environment variables:
    PLIVO_AUTH_ID      -- Your Plivo auth ID
    PLIVO_AUTH_TOKEN   -- Your Plivo auth token

Run:
    python buy_number.py
"""

import asyncio

from plivo_agent import AsyncClient


async def main():
    async with AsyncClient() as client:
        # Search for available US local numbers
        results = await client.numbers.search("US", type="local", limit=5)

        numbers = results.get("objects", [])
        if not numbers:
            print("No numbers available.")
            return

        print("Available numbers:")
        for num in numbers:
            print(f"  {num['number']}  ({num.get('region', 'N/A')})")

        # Buy the first available number
        first = numbers[0]["number"]
        print(f"\nBuying {first}...")

        purchase = await client.numbers.buy(first)
        print("Purchased:", purchase)


if __name__ == "__main__":
    asyncio.run(main())
