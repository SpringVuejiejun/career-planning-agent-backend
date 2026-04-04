import asyncio
from sandbox_client import execute_python_code

async def test():
    result = await execute_python_code('print("Hello!")')
    print(result)

asyncio.run(test())
