"""Info API views."""

from typing import cast


from fastapi import APIRouter, Depends, Request
from multikeyjwt.middleware import JWTBearer, JWTPayload
from libpvarki.middleware.mtlsheader import MTLSHeader, DNDict

from ..middleware.mtls import MTLSorJWT
from ..middleware.datatypes import MTLSorJWTPayload
from ..middleware.user import ValidUser

router = APIRouter()


@router.get("/jwt", dependencies=[Depends(JWTBearer(auto_error=True))])
async def return_jwt_payload(request: Request) -> JWTPayload:
    """Method for testing JWT"""
    return cast(JWTPayload, request.state.jwt)


@router.get("/mtls", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def return_mtls_payload(request: Request) -> DNDict:
    """Method for testing mTLS"""
    return cast(DNDict, request.state.mtlsdn)


@router.get("/mtls_or_jwt", dependencies=[Depends(MTLSorJWT(auto_error=True))])
async def return_mtlsjwt_payload(request: Request) -> MTLSorJWTPayload:
    """Method for testing mTLS and JWT auth"""
    return cast(MTLSorJWTPayload, request.state.mtls_or_jwt)


@router.get("/mtls_or_jwt/permissive", dependencies=[Depends(MTLSorJWT(auto_error=True, disallow_jwt_sub=[]))])
async def return_mtlsjwt_payload_permissive(request: Request) -> MTLSorJWTPayload:
    """Method for testing mTLS and JWT auth, do not disallow any subjects"""
    return cast(MTLSorJWTPayload, request.state.mtls_or_jwt)


@router.get("/validuser", dependencies=[Depends(ValidUser(auto_error=True))])
async def return_validuser_payload(request: Request) -> MTLSorJWTPayload:
    """Method for the ValidUser middleware"""
    return cast(MTLSorJWTPayload, request.state.mtls_or_jwt)


@router.get("/validuser/admin", dependencies=[Depends(ValidUser(auto_error=True, require_roles=["admin"]))])
async def return_validadmin_payload(request: Request) -> MTLSorJWTPayload:
    """Method for the ValidUser middleware with required_roles"""
    return cast(MTLSorJWTPayload, request.state.mtls_or_jwt)


@router.get("/ldap/connection-string", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def return_ldap_connectionstring() -> str:
    """
    Method for generating and returning ldap connection string
    """
    # TODO: Check that the subject of the cert is one of the product integration APIs in manifest

    return "Hello World"
