import asyncio
import datetime

import aiohttp
from db import DbSession, SwapiPeople, close_orm, init_orm

MAX_REQUESTS = 5


async def get_json_from_url(session: aiohttp.ClientSession, url):
    response = await session.get(url)
    json_data = await response.json()
    return json_data


async def get_all_urls(session: aiohttp.ClientSession):
    url = 'https://swapi.py4e.com/api/people/'
    pages = [url]
    while url:
        data = await get_json_from_url(session, url)
        if data.get('next') is not None:
            pages.append(data.get('next'))
            url = data.get('next')
        else:
            break

    return pages


def prepare_data(data):
    models_col = {'url', 'birth_year', 'eye_color', 'gender',
                  'hair_color', 'homeworld', 'mass',
                  'name', 'skin_color'}
    result = []

    for person in data:
        filtered = {}
        for key in models_col:
            if key in person:
                if key == 'url':
                    filtered['id'] = int(person[key].rstrip('/').split('/')[-1])

                else:
                    filtered[key] = person[key]

        result.append(filtered)

    return result


async def get_people():
    async with aiohttp.ClientSession() as session:
        pages = await get_all_urls(session)
        all_person = []
        coros = [get_json_from_url(session, page) for page in pages]
        results = await asyncio.gather(*coros)

        for res in results:
            all_person.extend(res.get('results'))

        clear_person = prepare_data(all_person)

    return clear_person


async def insert_people(people_list):
    async with DbSession() as db_session:
        db_objects = [SwapiPeople(**item) for item in people_list]
        db_session.add_all(db_objects)
        await db_session.commit()


async def main():
    await init_orm()
    people = await get_people()
    await insert_people(people)
    await close_orm()


start = datetime.datetime.now()
asyncio.run(main())
end = datetime.datetime.now()
print(end - start)

