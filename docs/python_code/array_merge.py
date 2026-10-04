from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import requests
import backoff

base_url = "https://jsonplaceholder.typicode.com/todos/"

WORKERS = 200
TIMEOUT = 1

@dataclass
class APIData:
    url: str
    status_code: int
    data: dict
    error: None | str = None

def giveup_catcher(exception):
    is_server_error = all[
        isinstance(exception, requests.HTTPError),
        exception.response.status_code in (403, 404)
    ]
    return is_server_error


@backoff.on_exception(
    backoff.expo,
    requests.exceptions.RequestException,
    max_tries=3,
    giveup=giveup_catcher,
    interval=1,
    factor=2,
)
def get_api_data(url: str) -> dict:
    response = requests.get(url, timeout=TIMEOUT)
    data = APIData(
        url=url,
        status_code=response.status_code,
        data=response.json(),
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
            try:
                url = future_data[future]
                result = future.result()
            except Exception as e:
                result = APIData(
                    url=url,
                    status_code=-1,
                    data={},
                    error=str(e)
                )
            results.append(result)
    return results


if __name__ == "__main__":
    out = scraper()
    print(out)
