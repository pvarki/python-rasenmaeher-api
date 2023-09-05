#!/bin/bash -e
sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$(getent hosts host.docker.internal | awk '{ print $1 }') localmaeher.pvarki.fi mtls.localmaeher.pvarki.fi fake.localmaeher.pvarki.fi" >>/etc/hosts
python3 /app/fpclient.py
