#!/bin/bash -l
set -e
if [ "$#" -eq 0 ]; then
  # TODO: Put your actual program start here
  uvicorn rasenmaeher_api.web.application:get_app
  exec true
else
  exec "$@"
fi
