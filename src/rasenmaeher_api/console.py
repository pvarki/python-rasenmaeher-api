"""CLI entrypoints for python-rasenmaeher-api"""
import logging

import click

from libadvian.logging import init_logging
from rasenmaeher_api import __version__


LOGGER = logging.getLogger(__name__)


@click.command()
@click.version_option(version=__version__)
@click.option("-l", "--loglevel", help="Python log level, 10=DEBUG, 20=INFO, 30=WARNING, 40=CRITICAL", default=30)
@click.option("-v", "--verbose", count=True, help="Shorthand for info/debug loglevel (-v/-vv)")
def rasenmaeher_api_cli(loglevel: int, verbose: int) -> None:
    """python-rasenmaeher-api"""
    if verbose == 1:
        loglevel = 20
    if verbose >= 2:
        loglevel = 10
    init_logging(loglevel)
    LOGGER.setLevel(loglevel)

    click.echo("Do your thing")
