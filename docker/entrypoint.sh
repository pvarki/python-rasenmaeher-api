#!/bin/bash -l
set -e
# Make sure fakeproduct api endpoint points to correct IP, 127.0.01 is this containers localhost...
sed 's/.*localmaeher.*//g' /etc/hosts >/etc/hosts.new && cat /etc/hosts.new >/etc/hosts
echo "$(getent hosts host.docker.internal | awk '{ print $1 }') fake.localmaeher.pvarki.fi" >>/etc/hosts
if [ "$#" -eq 0 ]; then
  # FIXME: can we know the traefik/nginx internal docker ip easily ?
  exec gunicorn "rasenmaeher_api.web.application:get_app()" --bind 0.0.0.0:8000 --forwarded-allow-ips='*' -w 4 -k uvicorn.workers.UvicornWorker
else
  exec "$@"
fi
