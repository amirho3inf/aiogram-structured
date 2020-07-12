#!/usr/bin/env python3

import os
import click
import inspect
import importlib
import traceback as tb
from datetime import datetime

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from redis import Redis

from alembic.config import Config
from alembic import command as alembic
from alembic.util.exc import CommandError

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore

MAIN_MODULE_NAME = os.path.basename(__file__)[:-3]

try:
    from config import API_TOKEN, PROXY, PROXY_AUTH, DATABASE_URL, \
        REDIS_URL, HANDLERS, SKIP_UPDATES, HANDLERS_DIR, MODELS_DIR, \
        CONTEXT_FILE, ENABLE_APSCHEDULER, PARSE_MODE
except ModuleNotFoundError:
    click.echo(click.style(
        "Config file not found!\n"
        "Please create config.py file according to config.py.example",
        fg='bright_red'))
    exit()


class SQLAlchemy(object):
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Model = declarative_base(self.engine)

        self.sessionmaker = sessionmaker(bind=self.engine)
        self.session = scoped_session(self.sessionmaker)

        self.Model.query = self.session.query_property()

    @property
    def metadata(self):
        return self.Model.metadata


class Context(object):
    def __init__(self, _context_obj):
        self._context_obj = _context_obj

    def __getattr__(self, name):
        r = getattr(self._context_obj, name, None)

        if r is None:
            return f"< {name} > not defined in context."

        frame = inspect.currentframe()
        try:
            caller_locals = frame.f_back.f_locals
            r = r.format_map(caller_locals)
        finally:
            del frame

        return r


def set_bot_properties(executor, bot):
    loop = executor.asyncio.get_event_loop()
    _ = loop.run_until_complete(bot.get_me())
    for prop, val in _:
        setattr(bot, prop, val)


def get_alembic_conf():
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "migrations")
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    alembic_cfg.config_file_name = os.path.join("migrations", 'alembic.ini')
    if os.path.isdir('migrations') is False:
        click.echo(click.style("Initiating alembic...", fg='bright_blue'))
        alembic.init(alembic_cfg, 'migrations')
        with open('migrations/env.py', 'r+') as f:
            content = f.read()
            content = content.replace(
                'target_metadata = None',
                f'from {MAIN_MODULE_NAME} import db\ntarget_metadata = db.metadata')
            f.seek(0)
            f.write(content)

    return alembic_cfg


def get_async_scheduler(redis):
    cfg = redis.connection_pool.connection_kwargs
    jobstores = {
        'default': RedisJobStore(host=cfg.get("host"),
                                 port=cfg.get("port"),
                                 db=cfg.get("db"),
                                 password=cfg.get("password"))
    }
    job_defaults = {
        "misfire_grace_time": 3600
    }
    return AsyncIOScheduler(jobstores=jobstores, job_defaults=job_defaults)


class CliGroup(click.Group):
    def list_commands(self, ctx):
        return [
            "showmigrations",
            "makemigrations",
            "migrate",
            "run"
        ]


@click.group(cls=CliGroup)
def cli():
    pass


@cli.command()
def run():
    THIS = importlib.import_module(MAIN_MODULE_NAME)

    handlers = [m[:-3] for m in os.listdir(HANDLERS_DIR) if m.endswith(".py")]
    for handler in (HANDLERS or handlers):
        print(f"Loading {handler}...  ", end="")
        print(f"\r\t\t\t\t", end="")

        try:
            importlib.import_module(f'{HANDLERS_DIR}.{handler}')
            click.echo(click.style("loaded", fg='bright_green'))
        except Exception as err:
            click.echo(click.style("error", fg='bright_red'))
            click.echo(click.style(f"↳  {tb.format_exc()}", fg='bright_red'))

    click.echo('Bot running as ' +
               click.style(f'@{THIS.bot.username}', fg='bright_blue'))

    if ENABLE_APSCHEDULER is True:
        THIS.scheduler.start()

    THIS.executor.start_polling(THIS.dp, skip_updates=SKIP_UPDATES)


@cli.command()
@click.option('--verbose', default=False, is_flag=True)
def showmigrations(verbose):
    try:
        cfg = get_alembic_conf()
        history = alembic.history(cfg, verbose=verbose)
        click.echo(history)
    except CommandError as err:
        click.echo(click.style(
            str(err),
            fg='bright_red'))


@cli.command()
@click.option('-m', '--message', default=None)
def makemigrations(message):
    if message is None:
        click.echo(click.style(
            "Optinal: "
            "Use -m <msg>, --message=<msg> to give a message string to this migrate script.",
            fg='yellow'))
        message = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    models = [m[:-3] for m in os.listdir(MODELS_DIR) if m.endswith(".py")]
    for model in models:
        print(f"Loading {model}...  ", end="")
        print(f"\r\t\t\t", end="")

        try:
            importlib.import_module(f'{MODELS_DIR}.{model}')
            click.echo(click.style("loaded", fg='bright_green'))

        except Exception as err:
            click.echo(click.style("error", fg='bright_red'))
            click.echo(click.style(f"↳  {tb.format_exc()}", fg='bright_red'))

    try:
        cfg = get_alembic_conf()
        alembic.revision(config=cfg,
                         message=message,
                         autogenerate=True,
                         sql=False,
                         head="head",
                         splice=False,
                         branch_label=None,
                         version_path=None,
                         rev_id=None)
    except CommandError as err:
        click.echo(click.style(
            str(err),
            fg='bright_red'))

        if str(err) == "Target database is not up to date.":
            click.echo(click.style(
                "run \"python bot.py migrate\"",
                fg='yellow'))


@cli.command()
@click.option('-r', '--revision', default="head")
@click.option('--upgrade/--downgrade', default=True, help="Default is upgrade")
def migrate(revision, upgrade):
    try:
        cfg = get_alembic_conf()
        if upgrade is True:
            alembic.upgrade(cfg, revision)
        else:
            alembic.downgrade(cfg, "-1" if revision == "head" else revision)
    except CommandError as err:
        click.echo(click.style(
            str(err),
            fg='bright_red'))


if __name__ == MAIN_MODULE_NAME:
    bot = Bot(token=API_TOKEN,
              proxy=PROXY,
              proxy_auth=PROXY_AUTH,
              parse_mode=PARSE_MODE)
    dp = Dispatcher(bot, storage=MemoryStorage())

    if DATABASE_URL is not None:
        db = SQLAlchemy(DATABASE_URL)

    if REDIS_URL is not None:
        redis = Redis.from_url(
            REDIS_URL, encoding='utf-8', decode_responses=True)

    if CONTEXT_FILE is not None:
        context = importlib.import_module(CONTEXT_FILE)
        text = Context(context)

    if ENABLE_APSCHEDULER is True:
        if REDIS_URL is None:
            click.echo(click.style(
                "APScheduler requires REDIS_URL that is not set!",
                fg='bright_red'))
            exit()

        scheduler = get_async_scheduler(redis)

    set_bot_properties(executor, bot)


if __name__ == '__main__':
    cli()
