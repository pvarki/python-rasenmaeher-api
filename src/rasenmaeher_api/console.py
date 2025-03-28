"""CLI entrypoints for python-rasenmaeher-api"""

from typing import Dict, Any
import logging
import json
import asyncio
import pprint
import uuid
from pathlib import Path

import aiohttp
import click
from libadvian.logging import init_logging
from multikeyjwt import Issuer

from rasenmaeher_api import __version__
from rasenmaeher_api.jwtinit import jwt_init
from rasenmaeher_api.testhelpers import create_test_users
from rasenmaeher_api.db import LoginCode, init_db, Person
from rasenmaeher_api.db.config import DBConfig
from rasenmaeher_api.db.middleware import DBWrapper
from rasenmaeher_api.db.errors import NotFound
from rasenmaeher_api.web.application import get_app_no_init

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
    init_logging(loglevel)

    LOGGER.setLevel(loglevel)
    ctx.ensure_object(dict)
    ctx.obj["loop"] = asyncio.get_event_loop()
    ctx.obj["dbwrapper"] = DBWrapper(config=DBConfig.singleton())


@cli_group.command(name="openapi")
@click.pass_context
def dump_openapi(ctx: click.Context) -> None:
    """
    Dump autogenerate openapi spec as JSON
    """
    app = get_app_no_init()
    click.echo(json.dumps(app.openapi()))
    ctx.exit(0)


@cli_group.command(name="healthcheck")
@click.option("--host", default="localhost", help="The host to connect to")
@click.option("--port", default=8000, help="The port to connect to")
@click.option("--timeout", default=2.0, help="The timeout in seconds")
@click.option("--services", default=False, help="Check services status too", is_flag=True)
@click.pass_context
def do_http_healthcheck(ctx: click.Context, host: str, port: int, timeout: float, services: bool) -> None:
    """
    Do a GET request to the healthcheck api and dump results to stdout
    """

    async def doit() -> int:
        """The actual work"""
        nonlocal host, port, timeout, services
        if "://" not in host:
            host = f"http://{host}"
        suffix = ""
        if services:
            suffix = "/services"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(f"{host}:{port}/api/v1/healthcheck{suffix}") as resp:
                if resp.status != 200:
                    return int(resp.status)
                payload = await resp.json()
                click.echo(json.dumps(payload))
                if services:
                    if not payload["all_ok"]:
                        return 1
                if payload["healthcheck"] != "success":
                    return 1
        return 0

    ctx.exit(ctx.obj["loop"].run_until_complete(doit()))


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
        nonlocal ctx
        await ctx.obj["dbwrapper"].app_startup_event()
        code = await LoginCode.create_for_claims(claims)
        await ctx.obj["dbwrapper"].app_startup_event()
        click.echo(code)
        return 0

    ctx.exit(ctx.obj["loop"].run_until_complete(call_backend(claims)))


@cli_group.command(name="getpfx")
@click.pass_context
@click.option("--admin", is_flag=True, help="If a new user, make admin")
@click.argument("callsign", required=True, type=str)
def get_pfx(ctx: click.Context, callsign: str, admin: bool) -> None:
    """Get PFX for cert+key for the given user, will create the user if needed"""

    async def do_the_needful() -> int:
        """Do what is needed"""
        nonlocal callsign, admin
        await init_db()

        try:
            person = await Person.by_callsign(callsign)
        except NotFound:
            person = await Person.create_with_cert(callsign)
            if admin:
                await person.assign_role("admin")
        tgtfile = Path(f"{callsign}.pfx")
        tgtfile.write_bytes((await person.create_pfx()).read_bytes())
        click.echo(f"Wrote {tgtfile}")

        return 0

    ctx.exit(ctx.obj["loop"].run_until_complete(do_the_needful()))


@cli_group.command(name="revokeuser")
@click.pass_context
@click.option("--reason", type=str, help="Reason", default="unspecified")
@click.argument("callsign", required=True, type=str)
def revoke_user(ctx: click.Context, callsign: str, reason: str) -> None:
    """Revoke user by callsign"""

    async def do_the_needful() -> int:
        """Do what is needed"""
        nonlocal callsign, reason
        await init_db()

        person = await Person.by_callsign(callsign)
        await person.revoke(reason)
        click.echo(f"{callsign} revoked")

        return 0

    ctx.exit(ctx.obj["loop"].run_until_complete(do_the_needful()))


@cli_group.command(name="getjwt")
@click.pass_context
@click.option("--nonce", is_flag=True, help="Add nonce field with UUID as value")
@click.argument("claims_json", required=False, default="""{"anon_admin_session": true}""", type=str)
def get_jwt(ctx: click.Context, claims_json: str, nonce: bool) -> None:
    """
    Get RASENMAEHER signed JWT
    """
    claims = json.loads(claims_json)
    if nonce:
        claims["nonce"] = str(uuid.uuid4())
    LOGGER.debug("Parsed claims={}".format(claims))
    if not claims:
        click.echo("Must specify claims", err=True)
        ctx.exit(1)

    async def call_backend(claims: Dict[str, Any]) -> int:
        """Call the backend"""
        await jwt_init()
        token = Issuer.singleton().issue(claims)
        click.echo(token)
        return 0

    ctx.exit(ctx.obj["loop"].run_until_complete(call_backend(claims)))


@cli_group.command(name="getadminjwt")
@click.pass_context
@click.argument("claims_json", required=False, default="""{"sub": "pyteststuff"}""", type=str)
def get_adminjwt(ctx: click.Context, claims_json: str) -> None:
    """
    Get RASENMAEHER signed admin user JWT
    """
    claims = json.loads(claims_json)
    LOGGER.debug("Parsed claims={}".format(claims))
    if not claims:
        click.echo("Must specify claims", err=True)
        ctx.exit(1)

    async def call_backend(claims: Dict[str, Any]) -> int:
        """Call the backend"""
        await jwt_init()
        token = Issuer.singleton().issue(claims)
        click.echo(token)
        return 0

    ctx.exit(ctx.obj["loop"].run_until_complete(call_backend(claims)))


@cli_group.command(name="addtestusers")
@click.pass_context
def add_test_users(ctx: click.Context) -> None:
    """
    Create the test users defined in testhelpers.create_test_users
    """

    async def call_testusers() -> int:
        """Start db connection, call the helper"""
        await init_db()
        ret = await create_test_users()
        click.echo(pprint.pformat(ret))
        return 0

    ctx.exit(ctx.obj["loop"].run_until_complete(call_testusers()))


def rasenmaeher_api_cli() -> None:
    """python-rasenmaeher-api"""
    init_logging(logging.WARNING)
    cli_group()  # pylint: disable=no-value-for-parameter
