import asyncio
import datetime

import aiohttp
from db import DbSession, SwapiPeople


async def get_json(session, url, semaphore, retries=3):
    for attempt in range(retries):
        try:
            async with semaphore:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()

                    if response.status in {429, 500, 502, 503, 504}:
                        await asyncio.sleep(1 * (attempt + 1))
                        continue

                    raise RuntimeError(f"Ошибка {response.status} для {url}")

        except Exception:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(1 * (attempt + 1))


async def prepare_person(session: aiohttp.ClientSession, person, semaphore):
    detail = await get_json(session, person["url"], semaphore)
    person_data = detail["result"]["properties"]

    person_id = int(person_data["url"].rstrip("/").split("/")[-1])
    homeworld_name = await get_planet_name(session, person_data["homeworld"], semaphore)

    return {
        "id": person_id,
        "birth_year": person_data.get("birth_year"),
        "eye_color": person_data.get("eye_color"),
        "gender": person_data.get("gender"),
        "hair_color": person_data.get("hair_color"),
        "homeworld": homeworld_name,
        "mass": person_data.get("mass"),
        "name": person_data.get("name"),
        "skin_color": person_data.get("skin_color"),
    }


async def get_people_page(session: aiohttp.ClientSession, url, semaphore):
    data = await get_json(session, url, semaphore)
    return data


async def get_planet_name(session: aiohttp.ClientSession, url, semaphore):
    data = await get_json(session, url, semaphore)
    return data["result"]["properties"]["name"]


async def get_all_people(session: aiohttp.ClientSession, semaphore):
    url = "https://www.swapi.tech/api/people"
    all_people = []

    while url:
        data = await get_people_page(session, url, semaphore)
        all_people.extend(data["results"])
        url = data.get("next")

    return all_people


async def insert_people(people_list):
    async with DbSession() as db_session:
        db_objects = [SwapiPeople(**item) for item in people_list]
        db_session.add_all(db_objects)
        await db_session.commit()


async def main():
    semaphore = asyncio.Semaphore(5)

    async with aiohttp.ClientSession() as session:
        people = await get_all_people(session, semaphore)
        coros = [prepare_person(session, person, semaphore) for person in people]
        prepared_people = await asyncio.gather(*coros)

    await insert_people(prepared_people)


start = datetime.datetime.now()
asyncio.run(main())
end = datetime.datetime.now()
print(end - start)
