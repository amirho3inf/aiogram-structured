from aiogram.types import ChatType, CallbackQuery, Message
from config import SUDOERS


def IsGroup(m):
    if isinstance(m, Message):
        return ChatType.is_group_or_super_group(m)
    elif isinstance(m, CallbackQuery):
        return ChatType.is_group_or_super_group(m.message)


def IsPrivate(m):
    if isinstance(m, Message):
        return ChatType.is_private(m)
    elif isinstance(m, CallbackQuery):
        return ChatType.is_private(m.message)


def IsChannel(m):
    if isinstance(m, Message):
        return ChatType.is_channel(m)
    elif isinstance(m, CallbackQuery):
        return ChatType.is_channel(m.message)


def IsSudo(m):
    return (m.from_user.id in SUDOERS)
