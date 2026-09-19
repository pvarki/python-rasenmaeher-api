"""Apple configuration profile wrapping the client certificate."""

import plistlib
import uuid

MEDIA_TYPE = "application/x-apple-aspen-config"
# Stable namespace, so reinstalling replaces the profile instead of stacking duplicates
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "pvarki.fi")


def build_mobileconfig(callsign: str, deployment: str, pfxbytes: bytes, password: str) -> bytes:
    """Wrap a PKCS12 container in an Apple configuration profile

    Apple's SecPKCS12Import cannot open an empty-password container at all, on any current iOS or
    macOS, so this embeds the passworded container and carries its password in the optional
    Password key. Both platforms then install the identity without ever prompting for it, which is
    the only way to keep Apple password-free from the user's point of view.
    """
    identifier = f"fi.pvarki.{deployment}.mtls"
    identity = {
        "PayloadType": "com.apple.security.pkcs12",
        "PayloadVersion": 1,
        "PayloadIdentifier": f"{identifier}.identity",
        "PayloadUUID": str(uuid.uuid5(NAMESPACE, f"{identifier}:{callsign}:identity")),
        "PayloadDisplayName": f"{callsign} client certificate",
        "PayloadCertificateFileName": f"{callsign}.pfx",
        "PayloadContent": pfxbytes,
        "Password": password,
    }
    profile = {
        "PayloadType": "Configuration",
        "PayloadVersion": 1,
        "PayloadIdentifier": identifier,
        "PayloadUUID": str(uuid.uuid5(NAMESPACE, f"{identifier}:{callsign}")),
        "PayloadDisplayName": f"{deployment} client certificate ({callsign})",
        "PayloadDescription": f"Installs the {callsign} client certificate for {deployment}.",
        "PayloadOrganization": deployment,
        "PayloadScope": "User",
        "PayloadRemovalDisallowed": False,
        "PayloadContent": [identity],
    }
    return plistlib.dumps(profile)
