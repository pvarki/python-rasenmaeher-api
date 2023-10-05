#!/bin/bash -l
set -e
source /container-init.sh
if [ "$#" -eq 0 ]; then
  # FIXME: can we know the traefik/nginx internal docker ip easily ?
  exec gunicorn "rasenmaeher_api.web.application:get_app()" --bind 0.0.0.0:8000 --forwarded-allow-ips='*' -w 4 -k uvicorn.workers.UvicornWorker
else
  exec "$@"
fi
