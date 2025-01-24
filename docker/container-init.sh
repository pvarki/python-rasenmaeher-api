#!/bin/bash -l
set -e
# Make sure fakeproduct api endpoint points to correct IP, 127.0.01 is this containers localhost...
sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') fake.localmaeher.dev.pvarki.fi" >>/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') tak.localmaeher.dev.pvarki.fi" >>/etc/hosts
echo "$(getent ahostsv4 host.docker.internal | awk '{ print $1 }') kc.localmaeher.dev.pvarki.fi" >>/etc/hosts

# Make sure the persistent directories exist
test -d /data/persistent/private || ( mkdir -p /data/persistent/private && chmod og-rwx /data/persistent/private )
test -d /data/persistent/public || mkdir -p /data/persistent/public

# Copy JWT public keys
if [ -d /pvarki/publickeys ]
then
  cp /pvarki/publickeys/*.pub ${JWT_PUBKEY_PATH:-/data/persistent/public}/
fi
