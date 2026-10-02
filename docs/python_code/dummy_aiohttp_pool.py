import aiohttp
import asyncio
from dataclasses import dataclass

base_url = "https://jsonplaceholder.typicode.com/todos/"
TIMEOUT = 15
CONCURRENCY = 3

@dataclass
class APIData:
    url: str
    status_code: int
    data: dict
    error: None | str = None

async def get_api_data(session, semaphore, url: str) -> dict:
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as response:
                data = APIData(
                    url=url,
                    status_code=response.status,
                    data=await response.json(),
                )
        except Exception as exc:
            data = APIData(
                url=url,
                status_code=-1,
                data={},
                error=repr(exc)
            )
    return data

async def get_all_data():
    results = []
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        tasks = [get_api_data(session, semaphore, url) for url in [f"{base_url}{i}" for i in range(1, 201)]]
        results = await asyncio.gather(*tasks)

        # for coro in asyncio.as_completed(tasks):
        #     result = await coro
        #     results.append(result)
    return results



if __name__ == "__main__":
    results = asyncio.run(get_all_data())
    print(results)
