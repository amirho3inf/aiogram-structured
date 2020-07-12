import os
import bot
import click
import importlib
import traceback as tb
from datetime import datetime

from alembic.config import Config
from alembic import command as alembic
from alembic.util.exc import CommandError

from config import DATABASE_URL, HANDLERS, SKIP_UPDATES, HANDLERS_DIR, \
    MODELS_DIR, ENABLE_APSCHEDULER


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
                f'from {bot.MAIN_MODULE_NAME} import db\ntarget_metadata = db.metadata')
            f.seek(0)
            f.write(content)

    return alembic_cfg


def set_bot_properties():
    loop = bot.executor.asyncio.get_event_loop()
    _ = loop.run_until_complete(bot.bot.get_me())
    for prop, val in _:
        setattr(bot.bot, prop, val)


def load_handlers():
    handlers = [m[:-3] for m in os.listdir(HANDLERS_DIR) if m.endswith(".py")]
    for handler in (HANDLERS or handlers):
        print(f"Loading {handler}...  ", end="")
        print(f"\r\t\t\t\t", end="")

        try:
            importlib.import_module(f'{HANDLERS_DIR}.{handler}')
            click.echo(click.style("loaded", fg='bright_green'))
        except Exception:
            click.echo(click.style("error", fg='bright_red'))
            click.echo(click.style(f"↳  {tb.format_exc()}", fg='bright_red'))


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
    click.echo(click.style('Connecting to Telegram...', fg='green'))

    set_bot_properties()

    load_handlers()

    click.echo('Bot running as ' +
               click.style(f'@{bot.bot.username}', fg='bright_blue'))

    if ENABLE_APSCHEDULER is True:
        bot.scheduler.start()

    bot.executor.start_polling(bot.dp, skip_updates=SKIP_UPDATES)


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

        except Exception:
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
