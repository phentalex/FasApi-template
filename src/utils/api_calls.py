import httpx
import asyncio
from config import OPENALEX_API_URL


async def fetch_json(ids: list):
    async with httpx.AsyncClient() as client:
        tasks = []
        for id in ids:
            id_upper = id.upper() if id.lower().startswith("w") else f"W{id}"
            full_id = f"{OPENALEX_API_URL}/works/{id_upper}"
            tasks.append((id_upper, client.get(full_id)))

        responses = await asyncio.gather(*[task[1] for task in tasks])

        results = {}
        for id_upper, response in zip([task[0] for task in tasks], responses):
            if response.status_code == 200:
                results[id_upper] = response.json()
            else:
                print(f"Ошибка при получении данных для {id_upper}: {response.status_code}")

        return results
