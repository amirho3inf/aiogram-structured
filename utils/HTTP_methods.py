from config import API_TOKEN
from bot import bot

session = bot.session
BASE_URL = f'https://api.telegram.org/bot{API_TOKEN}'

# make http requests with bot aiohttp session


async def get_my_ip():
    async with session.get("https://ipinfo.io/json") as r:
        jdata = await r.json()
        return jdata.get("ip")


async def delete_msg(chat_id, msg_id):
    async with session.get(f'{BASE_URL}/deleteMessage?'
                           f'chat_id={chat_id}&message_id={msg_id}'):
        return
