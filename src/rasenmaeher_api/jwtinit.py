"""Init JWT issuer"""
from typing import Optional, Union
import logging
import os
import asyncio
from pathlib import Path

from multikeyjwt import Issuer
from multikeyjwt.keygen import generate_keypair

LOGGER = logging.getLogger(__name__)
DEFAULT_KEY_PATH = Path("/data/persistent/private/rasenmaeher_jwt.key")
DEFAULT_PUB_PATH = Path("/data/persistent/public/rasenmaeher_jwt.pub")
KRAFTWERK_KEYS_PATH = Path(os.environ.get("PVARKI_PUBLICKEYS_PATH", "/pvarki/publickeys"))


def check_public_keys() -> bool:
    """Check public keys"""
    pubkeydir: Union[Path, Optional[str]] = os.environ.get("JWT_PUBKEY_PATH")
    LOGGER.debug("initial pubkeydir={}".format(pubkeydir))
    if pubkeydir:
        pubkeydir = Path(pubkeydir)
        if pubkeydir.exists() and not pubkeydir.is_dir():
            pubkeydir = pubkeydir.parent
    else:
        pubkeydir = DEFAULT_PUB_PATH.parent
    LOGGER.debug("final pubkeydir={}".format(pubkeydir))
    if not pubkeydir.exists():
        pubkeydir.mkdir(parents=True)

    if KRAFTWERK_KEYS_PATH.exists():
        LOGGER.info("Making sure KRAFTWERK provided keys are in {}".format(pubkeydir))
        for fpath in KRAFTWERK_KEYS_PATH.iterdir():
            tgtpath = pubkeydir / fpath.name
            LOGGER.debug("Checking {} vs {} (exists={})".format(fpath, tgtpath, tgtpath.exists()))
            if tgtpath.exists():
                continue
            # Copy the pubkey
            LOGGER.info("Copying {} to {}".format(fpath, tgtpath))
            tgtpath.write_bytes(fpath.read_bytes())
    else:
        LOGGER.warning("{} does not exist, not copying KRAFTWERK public keys".format(KRAFTWERK_KEYS_PATH))
    return True


def check_private_key() -> bool:
    """Check that we instantiate the issuer"""
    try:
        # ENV based defaults
        if Issuer.singleton():
            return True
    except ValueError:
        try:
            # Our default key path
            if Issuer.singleton(privkeypath=DEFAULT_KEY_PATH):
                return True
        except ValueError:
            return False
    except Exception:
        LOGGER.exception("Something went very wrong with issuer init")
        raise
    return False


def check_jwt_init() -> bool:
    """Check that we have key we can use for issuing and decoding JWTs"""
    if not check_private_key():
        return False
    return check_public_keys()


async def jwt_init() -> None:
    """If needed: Create keypair"""
    if check_jwt_init():
        return
    keypath: Union[Path, Optional[str]] = os.environ.get("JWT_PRIVKEY_PATH")
    if keypath:
        keypath = Path(str(keypath))
        if keypath.exists():
            LOGGER.warning(
                "We have defined private key path and file exists but it seems not be usable, will overwrite it with new key"  # pylint: disable=C0301
            )
    else:
        keypath = DEFAULT_KEY_PATH
    if not keypath.parent.exists():
        keypath.parent.mkdir(parents=True, mode=0o760)
    if keypass := os.environ.get("JWT_PRIVKEY_PASS"):
        LOGGER.info("Private key password defined in ENV, going to use it")

    LOGGER.info("Running keygen in executor")
    genpubpath: Optional[Path] = None
    genprivpath: Optional[Path] = None
    genprivpath, genpubpath = await asyncio.get_running_loop().run_in_executor(None, generate_keypair, keypath, keypass)
    if not genprivpath or not genprivpath.exists():
        raise RuntimeError("Returned private key does not exist!")
    if not genpubpath or not genpubpath.exists():
        raise RuntimeError("Returned private key does not exist!")

    pubkeypath: Union[Path, Optional[str]] = os.environ.get("JWT_PUBKEY_PATH")
    LOGGER.debug("initial pubkeypath={}".format(pubkeypath))
    if pubkeypath:
        pubkeypath = Path(pubkeypath)
        if pubkeypath.exists() and pubkeypath.is_dir():
            pubkeypath = pubkeypath / genpubpath.name
        LOGGER.info("JWT_PUBKEY_PATH defined, copying our key there")
    else:
        pubkeypath = DEFAULT_PUB_PATH
    LOGGER.debug("final pubkeypath={}".format(pubkeypath))

    if not pubkeypath.parent.exists():
        pubkeypath.parent.mkdir(parents=True)
    LOGGER.debug("Copy generated pubkey to {}".format(pubkeypath))
    pubkeypath.write_bytes(genpubpath.read_bytes())
    # Make sure KRAFTWERK public keys get copied
    check_public_keys()
