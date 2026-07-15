"""Native OCSP responder for the cert-manager backend (RFC 6960 / RFC 5019)"""

from .responder import build_ocsp_response
from .views import router

__all__ = ["build_ocsp_response", "router"]
