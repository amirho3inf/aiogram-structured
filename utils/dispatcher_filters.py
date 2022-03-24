from aiogram.types import ChatType, Message
from aiogram.dispatcher.filters import ChatTypeFilter
from config import SUDOERS
from bot import context


def IsGroup(m):
    return ChatTypeFilter([ChatType.GROUP, ChatType.SUPER_GROUP])


def IsPrivate(m):
    return ChatTypeFilter(ChatType.PRIVATE)


def IsChannel(m):
    return ChatTypeFilter(ChatType.CHANNEL)


def IsSudo(m):
    return (m.from_user.id in SUDOERS)


def ContextButton(context_key: str, classes: list = ["en"]):
    """
    This filter checks button's text when have a multi-language context
    example: ContextButton("cancel", ["en", "fa"])
    """
    def inner(m):
        if not(isinstance(m, Message) and m.text):
            return

        for cls in classes:
            if m.text == getattr(context[cls], context_key):
                return True
    return inner
