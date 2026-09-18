"""Enduser API views."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from libpvarki.schemas.generic import OperationResultResponse

from ....db import Person
from ....rmsettings import RMSettings
from ..enrollment.views import issue_enrollment_jwt
from ..middleware.user import ValidUser
from ..utils.auditcontext import build_audit_extra
from .mobileconfig import MEDIA_TYPE, build_mobileconfig

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
    callsign = callsign.removesuffix(deplosuffix)
    callsign = callsign.removesuffix(".pem")
    LOGGER.debug(f"PEM: Called with callsign={callsign}")
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


@router.post("/session")
async def create_download_session(
    request: Request,
    response: Response,
    person: Person = Depends(ValidUser(auto_error=True)),
) -> OperationResultResponse:
    """Refresh the JWT cookie so the browser can fetch a download by plain navigation

    iOS only hands a .mobileconfig to the profile installer when Safari navigates to it and sees
    the response content type, and a navigation carries no Authorization header. The cookie is the
    only credential that survives one, and the one enrollment sets expires long before the JWT the
    page holds, so anyone downloading again later needs a fresh one.
    """
    issue_enrollment_jwt(response, {"sub": person.callsign})
    LOGGER.audit(  # type: ignore[attr-defined]
        "Download session refreshed",
        extra=build_audit_extra(
            action="download_session",
            outcome="success",
            actor=person.callsign,
            request=request,
        ),
    )
    return OperationResultResponse(success=True)


@router.get(f"/{{callsign}}_{RMSettings.singleton().deployment_name}.mobileconfig")
@router.get("/{callsign}.mobileconfig")
async def get_user_mobileconfig(
    request: Request,
    callsign: str,
    person: Person = Depends(ValidUser(auto_error=True)),
) -> Response:
    """Get the cert and key as an Apple configuration profile, which installs without a prompt"""
    deployment = RMSettings.singleton().deployment_name
    # Strip the extension before the deployment suffix: "/{callsign}.mobileconfig" is registered
    # first, so it is what matches the long form too, leaving "OTTER1_localmaeher" in the param.
    callsign = callsign.removesuffix(".mobileconfig")
    callsign = callsign.removesuffix(f"_{deployment}")
    LOGGER.debug(f"MOBILECONFIG: Called with callsign={callsign}")
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
                certificate_type="mobileconfig",
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
            certificate_type="mobileconfig",
        ),
    )

    filename = f"{callsign}_{deployment}.mobileconfig"
    return Response(
        content=build_mobileconfig(callsign, deployment, person.pfxfile.read_bytes(), person.callsign),
        media_type=MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    callsign = callsign.removesuffix(deplosuffix)
    callsign = callsign.removesuffix(".pfx")
    if callsign.endswith(".pem"):
        LOGGER.debug("PFX: got .pem suffix, delegating")
        return await get_user_pem(request, callsign, person)
    LOGGER.debug(f"PFX: Called with callsign={callsign}")
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

    # Empty password everywhere it works, which is everything except Apple. Apple has the
    # .mobileconfig endpoint instead. create_pfx always writes this one, so never serve the other.
    return FileResponse(
        path=person.nopass_pfxfile,
        media_type="application/x-pkcs12",
        filename=f"{callsign}_{RMSettings.singleton().deployment_name}.pfx",
    )
