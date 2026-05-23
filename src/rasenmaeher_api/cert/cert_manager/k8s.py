"""Official kubernetes-client factory for the cert-manager backend.

The official `kubernetes` package is synchronous; callers wrap operations in
``asyncio.to_thread`` to stay non-blocking on the FastAPI event loop.
"""

from typing import Optional
import logging

from kubernetes import client, config


LOGGER = logging.getLogger(__name__)

# cert-manager CRD coordinates — used with CustomObjectsApi.
CERT_MANAGER_GROUP = "cert-manager.io"
CERT_MANAGER_VERSION = "v1"
CERTIFICATEREQUESTS_PLURAL = "certificaterequests"

_loaded = False
_custom_api: Optional[client.CustomObjectsApi] = None


def _ensure_loaded() -> None:
    """Load in-cluster config if available, otherwise fall back to kubeconfig."""
    global _loaded  # pylint: disable=global-statement
    if _loaded:
        return
    try:
        config.load_incluster_config()
        LOGGER.info("Loaded in-cluster k8s config")
    except config.ConfigException:
        config.load_kube_config()
        LOGGER.info("Loaded kubeconfig from env")
    _loaded = True


def get_custom_objects_api() -> client.CustomObjectsApi:
    """Return a cached CustomObjectsApi for cert-manager CRD operations."""
    global _custom_api  # pylint: disable=global-statement
    _ensure_loaded()
    if _custom_api is None:
        _custom_api = client.CustomObjectsApi()
    return _custom_api
