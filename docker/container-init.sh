#!/bin/bash -l
set -e
# Make sure product api endpoints point to correct IP, 127.0.01 is this containers localhost...
awk '!/.*localmaeher.*/' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
# FIXME: resolve the product hostnames from manifest
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') fake.localmaeher.dev.pvarki.fi" >>/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') tak.localmaeher.dev.pvarki.fi" >>/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') kc.localmaeher.dev.pvarki.fi" >>/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') bl.localmaeher.dev.pvarki.fi" >>/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') mtx.localmaeher.dev.pvarki.fi" >>/etc/hosts

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
