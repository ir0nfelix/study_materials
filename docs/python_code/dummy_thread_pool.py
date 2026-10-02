from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import requests

base_url = "https://jsonplaceholder.typicode.com/todos/"

WORKERS = 200
TIMEOUT = 1

@dataclass
class APIData:
    url: str
    status_code: int
    data: dict
    error: None | str = None


def get_api_data(url: str) -> dict:
    try:
        response = requests.get(url, timeout=TIMEOUT)
        data = APIData(
            url=url,
            status_code=response.status_code,
            data=response.json(),
        )
    except Exception as exc:
        data = APIData(
            url=url,
            status_code=-1,
            data={},
            error=str(exc)
        )

    return data


def scraper():
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        future_data = {
            executor.submit(get_api_data, url): url for url in
            [f"{base_url}{i}" for i in range(1, 201)]
        }
        for future in as_completed(future_data):
            result = future.result()
            results.append(result)

    return results


if __name__ == "__main__":
    out = scraper()
    print(out)
