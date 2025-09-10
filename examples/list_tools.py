# examples/basic_usage.py
import asyncio
from paylink import PayLink

async def main():
    client = PayLink(base_url="http://0.0.0.0:5002/mcp")
    tools = await client.list_tools()
    print("Available tools:", tools)
    
if __name__ == "__main__":
    asyncio.run(main())
