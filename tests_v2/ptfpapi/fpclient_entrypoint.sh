#!/bin/bash -e
if [ "$#" -eq 0 ]; then
  sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
  echo "$(getent hosts fpapi_run | awk '{ print $1 }') fake.localmaeher.pvarki.fi" >>/etc/hosts
  cat /etc/hosts
  python3 /app/fpclient.py
else
  exec "$@"
fi
