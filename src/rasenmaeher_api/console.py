"""CLI entrypoints for python-rasenmaeher-api"""
from typing import Dict, Any
import logging
import json
import asyncio

import click
from libadvian.logging import init_logging

from rasenmaeher_api import __version__
from rasenmaeher_api.web.api.tokens.views import create_code_backend


LOGGER = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
@click.pass_context
@click.option("-l", "--loglevel", help="Python log level, 10=DEBUG, 20=INFO, 30=WARNING, 40=CRITICAL", default=30)
@click.option("-v", "--verbose", count=True, help="Shorthand for info/debug loglevel (-v/-vv)")
def cli_group(ctx: click.Context, loglevel: int, verbose: int) -> None:
    """CLI helpers for RASENMAEHER developers"""
    if verbose == 1:
        loglevel = 20
    if verbose >= 2:
        loglevel = 10

    LOGGER.setLevel(loglevel)
    ctx.ensure_object(dict)


@cli_group.command(name="addcode")
@click.pass_context
@click.argument("claims_json", required=False, default="""{"anon_admin_session": true}""", type=str)
def add_code(ctx: click.Context, claims_json: str) -> None:
    """
    Add new single-use login code
    """
    claims = json.loads(claims_json)
    LOGGER.debug("Parsed claims={}".format(claims))
    if not claims:
        click.echo("Must specify claims", err=True)
        ctx.exit(1)

    async def call_backend(claims: Dict[str, Any]) -> int:
        """Call the backend"""
        code = await create_code_backend(claims)
        click.echo(code)
        return 0

    ctx.exit(asyncio.get_event_loop().run_until_complete(call_backend(claims)))


def rasenmaeher_api_cli() -> None:
    """python-rasenmaeher-api"""
    init_logging(logging.WARNING)
    cli_group()  # pylint: disable=no-value-for-parameter
