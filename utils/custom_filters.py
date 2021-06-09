from aiogram.types import ChatType
from aiogram.dispatcher.filters import ChatTypeFilter
from config import SUDOERS


def IsGroup(m):
    return ChatTypeFilter([ChatType.GROUP, ChatType.SUPERGROUP])


def IsPrivate(m):
    return ChatTypeFilter(ChatType.PRIVATE)


def IsChannel(m):
    return ChatTypeFilter(ChatType.CHANNEL)


def IsSudo(m):
    return (m.from_user.id in SUDOERS)
