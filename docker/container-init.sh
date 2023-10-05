#!/bin/bash -l
set -ex
# Make sure fakeproduct api endpoint points to correct IP, 127.0.01 is this containers localhost...
sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$(getent hosts host.docker.internal | awk '{ print $1 }') fake.localmaeher.pvarki.fi" >>/etc/hosts
if [ -d /pvarki/public ]
then
  cp /pvarki/public/*werk.pub ${JWT_PUBKEY_PATH:-/data/persistent/public}/
fi
