from aiogram.dispatcher.filters import CommandStart, Text
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot import dp, db, text
from models.user import User
from forms.register import Register
from utils.custom_filters import IsPrivate


@dp.message_handler(CommandStart(), IsPrivate)
async def start(msg):
    user = User.query.filter(User.id == msg.from_user.id).first()
    if user is not None:
        return await msg.reply(text.already_registered)

    await Register.name.set()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(text.cancel)
    return await msg.reply(text.ask_name, reply_markup=markup)


@dp.message_handler(IsPrivate, Text(equals=text.cancel), state=Register.all_states)
async def cancel(msg, state):
    await state.finish()
    return await msg.reply(text.register_canceled, reply_markup=ReplyKeyboardRemove())


@dp.message_handler(IsPrivate, state=Register.name)
async def enter_name(msg, state):
    async with state.proxy() as data:
        data['name'] = msg.text
    await Register.next()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(text.cancel)
    return await msg.reply(text.ask_age, reply_markup=markup)


@dp.message_handler(IsPrivate, state=Register.age)
async def enter_age(msg, state):
    if not msg.text.isnumeric() or not (8 < int(msg.text) < 100):
        return await msg.reply(text.invalid_input)

    async with state.proxy() as data:
        data['age'] = int(msg.text)

    await Register.next()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(text.cancel)
    return await msg.reply(text.ask_phone_number, reply_markup=markup)


@dp.message_handler(IsPrivate, state=Register.phone_number)
async def enter_phone_number(msg, state):
    if not msg.text.startswith("+") or not msg.text.strip("+").isnumeric():
        return await msg.reply(text.invalid_input)

    async with state.proxy() as data:
        name = data['name']
        age = data['age']
        phone_number = int(msg.text.strip("+"))
    await state.finish()

    user = User()
    user.id = msg.from_user.id
    user.name = name
    user.age = age
    user.phone_number = phone_number
    user.username = msg.from_user.username
    db.session.add(user)
    try:
        db.session.commit()
        return await msg.reply(text.user_registered, reply_markup=ReplyKeyboardRemove())
    except Exception as err:
        print(f"Database commit error: {err}")
        db.session.rollback()
        db.session.remove()
        return await msg.reply(text.error_occurred, reply_markup=ReplyKeyboardRemove())
