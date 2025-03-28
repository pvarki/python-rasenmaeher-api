"""Enduser API views."""

import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from ....db import Person
from ..middleware.user import ValidUser

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.get("/{callsign}.pfx")
@router.get("/{callsign}")
async def get_user_pfx(
    callsign: str,
    person: Person = Depends(ValidUser(auto_error=True)),
) -> FileResponse:
    """
    Method to check if bundle is available
    :param callsign: OTTER1.pfx
    :returns pfx or 403 error
    """
    if callsign.endswith(".pfx"):
        callsign = callsign[:-4]
    LOGGER.debug("Called with callsign={}".format(callsign))
    if person.callsign != callsign:
        raise HTTPException(status_code=403, detail="Callsign must match authenticated user")
    # Make sure the pfx exists, this is no-op if it does
    await person.create_pfx()

    return FileResponse(path=person.pfxfile, media_type="application/x-pkcs12", filename=f"{callsign}.pfx")
