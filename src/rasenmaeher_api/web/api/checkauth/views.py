"""Info API views."""
from typing import cast


from fastapi import APIRouter, Depends, Request
from multikeyjwt.middleware import JWTBearer, JWTPayload
from libpvarki.middleware.mtlsheader import MTLSHeader, DNDict

from ..middleware import MTLSorJWT, MTLSorJWTPayload

router = APIRouter()


@router.get("/jwt", dependencies=[Depends(JWTBearer(auto_error=True))])
async def return_jwt_payload(request: Request) -> JWTPayload:
    """Method for testing JWT"""
    return request.state.jwt


@router.get("/mtls", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def return_mtls_payload(request: Request) -> DNDict:
    """Method for testing mTLS"""
    return request.state.mtlsdn


@router.get("/mtls_or_jwt", dependencies=[Depends(MTLSorJWT(auto_error=True))])
async def return_mtlsjwt_payload(request: Request) -> MTLSorJWTPayload:
    """Method for testing mTLS and JWT auth"""
    return request.state.mtls_or_jwt


@router.get("/mtls_or_jwt/permissive", dependencies=[Depends(MTLSorJWT(auto_error=True, disallow_jwt_sub=[]))])
async def return_mtlsjwt_payload_permissive(request: Request) -> MTLSorJWTPayload:
    """Method for testing mTLS and JWT auth, do not disallow any subjects"""
    return request.state.mtls_or_jwt


@router.get("/ldap/connection-string", dependencies=[Depends(JWTBearer())])
async def return_ldap_connectionstring() -> str:
    """
    Method for generating and returning ldap connection string
    """

    return cast(str, "Hello World")
