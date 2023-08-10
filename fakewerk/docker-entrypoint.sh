#!/bin/bash -l
set -e
if [ "$#" -eq 0 ]; then
  python3 /fakewerk.py
else
  exec "$@"
fi
