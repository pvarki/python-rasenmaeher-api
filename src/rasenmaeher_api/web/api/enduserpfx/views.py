"""Enduser API views."""

import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import FileResponse

from ....db import Person
from ..middleware.user import ValidUser
from ..utils.auditcontext import build_audit_extra
from ....rmsettings import RMSettings

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.get(f"/{{callsign}}_{RMSettings.singleton().deployment_name}.pem")
@router.get("/{callsign}.pem")
async def get_user_pem(
    request: Request,
    callsign: str,
    person: Person = Depends(ValidUser(auto_error=True)),
) -> FileResponse:
    """Get the signed cert in PEM format (no keys)"""
    deplosuffix = f"_{RMSettings.singleton().deployment_name}.pem"
    if callsign.endswith(deplosuffix):
        callsign = callsign[: -len(deplosuffix)]
    if callsign.endswith(".pem"):
        callsign = callsign[:-4]
    LOGGER.debug("PEM: Called with callsign={}".format(callsign))
    if person.callsign != callsign:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Certificate download denied - callsign mismatch",
            extra=build_audit_extra(
                action="certificate_download",
                outcome="failure",
                actor=person.callsign,
                target=callsign,
                request=request,
                error_code="CALLSIGN_MISMATCH",
                certificate_type="pem",
            ),
        )
        raise HTTPException(status_code=403, detail="Callsign must match authenticated user")
    # Make sure the pfx exists, this is no-op if it does
    await person.create_pfx()

    LOGGER.audit(  # type: ignore[attr-defined]
        "Certificate downloaded",
        extra=build_audit_extra(
            action="certificate_download",
            outcome="success",
            actor=person.callsign,
            request=request,
            certificate_type="pem",
        ),
    )

    return FileResponse(
        path=person.certfile,
        media_type="application/x-pem-file",
        filename=f"{callsign}_{RMSettings.singleton().deployment_name}.pem",
    )


@router.get(f"/{{callsign}}_{RMSettings.singleton().deployment_name}.pfx")
@router.get("/{callsign}.pfx")
@router.get("/{callsign}")
async def get_user_pfx(
    request: Request,
    callsign: str,
    person: Person = Depends(ValidUser(auto_error=True)),
) -> FileResponse:
    """
    Method to check if bundle is available
    :param callsign: OTTER1.pfx
    :returns pfx or 403 error
    """
    deplosuffix = f"_{RMSettings.singleton().deployment_name}.pfx"
    if callsign.endswith(deplosuffix):
        callsign = callsign[: -len(deplosuffix)]
    if callsign.endswith(".pfx"):
        callsign = callsign[:-4]
    if callsign.endswith(".pem"):
        LOGGER.debug("PFX: got .pem suffix, delegating")
        return await get_user_pem(request, callsign, person)
    LOGGER.debug("PFX: Called with callsign={}".format(callsign))
    if person.callsign != callsign:
        LOGGER.audit(  # type: ignore[attr-defined]
            "Certificate download denied - callsign mismatch",
            extra=build_audit_extra(
                action="certificate_download",
                outcome="failure",
                actor=person.callsign,
                target=callsign,
                request=request,
                error_code="CALLSIGN_MISMATCH",
                certificate_type="pfx",
            ),
        )
        raise HTTPException(status_code=403, detail="Callsign must match authenticated user")
    # Make sure the pfx exists, this is no-op if it does
    await person.create_pfx()

    LOGGER.audit(  # type: ignore[attr-defined]
        "Certificate downloaded",
        extra=build_audit_extra(
            action="certificate_download",
            outcome="success",
            actor=person.callsign,
            request=request,
            certificate_type="pfx",
        ),
    )

    return FileResponse(
        path=person.pfxfile,
        media_type="application/x-pkcs12",
        filename=f"{callsign}_{RMSettings.singleton().deployment_name}.pfx",
    )
