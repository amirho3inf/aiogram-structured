from config import API_TOKEN
from bot import bot


async def get_my_ip():
    session = await bot.get_session()
    async with session.get("https://ipinfo.io/json") as r:
        jdata = await r.json()
        return jdata.get("ip")


async def delete_msg(chat_id, msg_id):
    session = await bot.get_session()
    async with session.get(f'https://api.telegram.org/bot{API_TOKEN}/deleteMessage?'
                           f'chat_id={chat_id}&message_id={msg_id}'):
        return
