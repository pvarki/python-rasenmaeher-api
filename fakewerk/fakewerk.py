"""Emulate KRAFTWERK init"""
from pathlib import Path
import logging
import uuid
import shutil
import json
import os

from libadvian.logging import init_logging
from multikeyjwt.keygen import generate_keypair
from multikeyjwt import Issuer
from multikeyjwt.config import Secret


TP_PUBKEY_PATH = Path("/pvarki/publickeys/tilauspalvelu.pub")
TP_PRIVKEY_PATH = Path("/data/persistent/privkeys/tilauspalvelu.key")
FP_MANIFEST_PATH = Path("/pvarki/kraftwerk-init.json")
RM_MANIFEST_PATH = Path("/pvarki/kraftwerk-rasenmaeher-init.json")
LOGGER = logging.getLogger(__name__)


def get_key_pass(keypath: Path) -> str:
    """read the .pass -file corresponding to the key"""
    pwdfile_path = keypath.with_suffix(".pass")
    with pwdfile_path.open("rt", encoding="utf-8") as fpntr:
        return fpntr.read()


def ensure_directories() -> None:
    """Make sure the directories exist"""
    check_dirs = (TP_PUBKEY_PATH.parent, TP_PRIVKEY_PATH.parent)
    for pkdir in check_dirs:
        if not pkdir.exists():
            LOGGER.info("Creating directory {}".format(pkdir))
            pkdir.mkdir(parents=True)


def create_tilauspalvelu_keypair() -> None:
    """Create JWT keypair for fake TILAUSPALVELU"""
    pwdfile_path = TP_PRIVKEY_PATH.with_suffix(".pass")
    if not pwdfile_path.exists():
        with pwdfile_path.open("wt", encoding="utf-8") as fpntr:
            fpntr.write(str(uuid.uuid4()))
    _genkey, genpub = generate_keypair(TP_PRIVKEY_PATH, get_key_pass(TP_PRIVKEY_PATH))
    shutil.copy(genpub, TP_PUBKEY_PATH)


def create_fakeproduct_manifest() -> None:
    """create manisfest for fakeproduct"""
    issuer = Issuer(
        privkeypath=TP_PRIVKEY_PATH, keypasswd=Secret(get_key_pass(TP_PRIVKEY_PATH))
    )
    issuer.config.lifetime = 3600 * 24  # 24h
    token = issuer.issue(
        {
            "sub": "fakeproduct",
            "csr": True,
        }
    )
    rm_port = int(os.environ.get("RASENMAEHER_HTTPS_PORT", "4439"))
    rm_host = os.environ.get("RASENMAEHER_HOST", "localmaeher.pvarki.fi")
    if rm_port != 443:
        rm_uri = f"https://{rm_host}:{rm_port}/"
    else:
        rm_uri = f"https://{rm_host}/"
    manifest = {
        "rasenmaeher": {"base_uri": rm_uri, "csr_jwt": token},
        "product": {"dns": "fake.localmaeher.pvarki.fi"},
    }
    with FP_MANIFEST_PATH.open("wt", encoding="utf-8") as fpntr:
        json.dump(manifest, fpntr)


def create_rasenmaeher_manifest() -> None:
    """create manifest for RASENMAEHER"""
    manifest = {
        "dns": "localmaeher.pvarki.fi",
        "products": {"fake": "fake.localmaeher.pvarki.fi"},
    }
    with RM_MANIFEST_PATH.open("wt", encoding="utf-8") as fpntr:
        json.dump(manifest, fpntr)


def main() -> None:
    """Do the needful"""
    ensure_directories()
    if not TP_PUBKEY_PATH.exists():
        LOGGER.info("Creating TILAUSPALVELU JWT keypair")
        create_tilauspalvelu_keypair()
    LOGGER.info("Writing product manifest for RASENMAEHER")
    create_rasenmaeher_manifest()
    LOGGER.info("Writing product manifest for fakeproduct")
    create_fakeproduct_manifest()


if __name__ == "__main__":
    init_logging(logging.DEBUG)
    LOGGER.setLevel(logging.DEBUG)
    main()
