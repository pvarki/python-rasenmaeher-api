"""Functions that routes that deal with users MUST call after changes"""

import uuid
import logging

LOGGER = logging.getLogger(__name__)

# PONDER: Should we be passing the callsign to these at all ? the UUID should be enough to find everything


def user_created(uid: uuid.UUID, callsign: str) -> None:
    """Called when user enrollment has been approved and cert has een created"""
    _, _ = uid, callsign
    # FIXME: Talk to keycloak
    # FIXME: Talk to products' integration apis (see productsapihelpers)


def user_promoted(uid: uuid.UUID, callsign: str) -> None:
    """Called when user has been promoted to admin"""
    _, _ = uid, callsign
    # FIXME: Talk to keycloak
    # FIXME: Talk to products' integration apis (see productsapihelpers)


def user_demoted(uid: uuid.UUID, callsign: str) -> None:
    """Called when user has admin privileges removed"""
    _, _ = uid, callsign
    # FIXME: Talk to keycloak
    # FIXME: Talk to products' integration apis (see productsapihelpers)


def user_removed(uid: uuid.UUID, callsign: str) -> None:
    """Called when user has been removed, cert needs to be revoked etc"""
    _, _ = uid, callsign
    # FIXME: Talk to keycloak
    # FIXME: Talk to products' integration apis (see productsapihelpers)


def user_updated(uid: uuid.UUID, callsign: str) -> None:
    """Called when user was updated"""
    _, _ = uid, callsign
    # FIXME: Talk to keycloak
    # FIXME: Talk to products' integration apis (see productsapihelpers)
