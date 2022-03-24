#!/usr/bin/env python3

import os
import re
import click
import inspect
import importlib

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from redis import Redis

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore

MAIN_MODULE_NAME = os.path.basename(__file__)[:-3]

try:
    from config import API_TOKEN, SKIP_UPDATES, PARSE_MODE, PROXY, \
        PROXY_AUTH, DATABASE_URL, REDIS_URL, HANDLERS_DIR, MODELS_DIR, \
        CONTEXT_FILE, ENABLE_APSCHEDULER, SUDOERS, HANDLERS
except ModuleNotFoundError:
    click.echo(click.style(
        "Config file not found!\n"
        "Please create config.py file according to config.py.example",
        fg='bright_red'))
    exit()
except ImportError as err:
    var = re.match(r"cannot import name '(\w+)' from", err.msg).groups()[0]
    click.echo(click.style(
        f"{var} is not defined in the config file",
        fg='bright_red'))
    exit()


class _SQLAlchemy(object):
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Model = declarative_base(self.engine)

        self.sessionmaker = sessionmaker(bind=self.engine)
        self.session = scoped_session(self.sessionmaker)

        self.Model.query = self.session.query_property()

    @property
    def metadata(self):
        return self.Model.metadata


class _Context(object):
    def __init__(self, _context_obj):
        self._context_obj = _context_obj

    def __getattr__(self, name):
        r = getattr(self._context_obj, name, None)

        if r is None:
            return f"\"{name}\" is not defined."

        if isinstance(r, str):
            frame = inspect.currentframe()
            try:
                caller_locals = frame.f_back.f_locals
                r = r.format_map(caller_locals)
            finally:
                del frame

            return r
        elif isinstance(r, type):
            return _Context(r)

    def __getitem__(self, name):
        r = getattr(self._context_obj, name, None)

        if r is None:
            return f"\"{name}\" is not defined."

        if isinstance(r, str):
            frame = inspect.currentframe()
            try:
                caller_locals = frame.f_back.f_locals
                r = r.format_map(caller_locals)
            finally:
                del frame

            return r
        elif isinstance(r, type):
            return _Context(r)


class _NotDefinedModule(Exception):
    pass


class _NoneModule(object):
    def __init__(self, module_name, attr_name):
        self.module_name = module_name
        self.attr_name = attr_name

    def __getattr__(self, attr):
        msg = f"You are using {self.module_name} while the {self.attr_name} is not set in config"
        raise _NotDefinedModule(msg)


def _get_bot_obj():
    bot = Bot(
        token=API_TOKEN,
        proxy=PROXY,
        proxy_auth=PROXY_AUTH,
        parse_mode=PARSE_MODE
    )
    return bot


def _get_redis_obj():
    if REDIS_URL is not None:
        redis = Redis.from_url(
            REDIS_URL,
            encoding='utf-8',
            decode_responses=True
        )
    else:
        redis = _NoneModule("redis", "REDIS_URL")

    return redis


def _get_dp_obj(bot, redis):
    if not isinstance(redis, _NoneModule):
        cfg = redis.connection_pool.connection_kwargs
        storage = RedisStorage2(
            host=cfg.get("host", "localhost"),
            port=cfg.get("port", 6379),
            db=cfg.get("db", 0),
            password=cfg.get("password")
        )
    else:
        storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    return dp


def _get_db_obj():
    if DATABASE_URL is not None:
        db = _SQLAlchemy(DATABASE_URL)
    else:
        db = _NoneModule("db", "DATABASE_URL")

    return db


def _get_context_obj():
    if CONTEXT_FILE is not None:
        _module = importlib.import_module(CONTEXT_FILE)
        context = _Context(_module)
    else:
        context = _NoneModule("text", "CONTEXT_FILE")

    return context


def _get_scheduler_obj(redis):
    job_defaults = {
        "misfire_grace_time": 3600
    }

    if not isinstance(redis, _NoneModule):
        cfg = redis.connection_pool.connection_kwargs
        jobstores = {
            'default': RedisJobStore(host=cfg.get("host", "localhost"),
                                     port=cfg.get("port", 6379),
                                     db=cfg.get("db", 0),
                                     password=cfg.get("password"))
        }
    else:
        jobstores = {
            "default": MemoryJobStore()
        }

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        job_defaults=job_defaults
    )

    return scheduler


__all__ = [
    "bot",
    "dp",
    "db",
    "redis",
    "context",
    "scheduler"
]


if __name__ == MAIN_MODULE_NAME:
    bot = _get_bot_obj()
    redis = _get_redis_obj()
    dp = _get_dp_obj(bot, redis)
    db = _get_db_obj()
    context = _get_context_obj()
    scheduler = _get_scheduler_obj(redis)


if __name__ == '__main__':
    from cli import cli
    cli()
