# examples/basic_usage.py
import asyncio
from paylink import PayLink

async def main():
    client = PayLink(base_url="http://0.0.0.0:5002/mcp")
    tools = await client.list_tools()
    print("Available tools:", tools)

    if "stk_push" in tools:
        res = await client.call_tool("stk_push", {
            "amount": "1",
            "phone_number": "2547XXXXXXXX",
            "account_reference": "ORDER123",
            "transaction_desc": "TestPayment"
        })
        print("STK push response:", res)

if __name__ == "__main__":
    asyncio.run(main())
