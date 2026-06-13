#!/bin/bash -l
set -e
# Make sure product api endpoints point to correct IP, 127.0.01 is this containers localhost...
test -x /pvarki/hosts_script.sh && . /pvarki/hosts_script.sh

# Make sure the persistent directories exist
test -d /data/persistent/private || ( mkdir -p /data/persistent/private && chmod og-rwx /data/persistent/private )
test -d /data/persistent/public || mkdir -p /data/persistent/public

# Handle external JWT public key if provided
if [ -n "$EXTERNAL_JWT_PUBKEY_B64" ]; then
    echo "$EXTERNAL_JWT_PUBKEY_B64" | base64 -d > ${JWT_PUBKEY_PATH:-/data/persistent/public}/external.pub
fi

# Copy JWT public keys
if [ -d /pvarki/publickeys ]
then
  cp /pvarki/publickeys/*.pub ${JWT_PUBKEY_PATH:-/data/persistent/public}/
fi
