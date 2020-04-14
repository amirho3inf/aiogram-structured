from config import API_TOKEN
from bot import bot

session = bot.session
BASE_URL = f'https://api.telegram.org/bot{API_TOKEN}'

# make http requests with bot aiohttp session


async def get_my_ip():
    async with session.get("https://ipinfo.io/json") as r:
        jdata = await r.json()
        return jdata.get("ip")
