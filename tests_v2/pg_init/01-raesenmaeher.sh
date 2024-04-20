#!/bin/bash
if [ -z "$RAESENMAEHER_PASSWORD" ]
then
  echo "RAESENMAEHER_PASSWORD not set"
  exit 1
fi
set -e
# FIXME: Can we use mTLS for auth ??
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER raesenmaeher WITH ENCRYPTED PASSWORD '$RAESENMAEHER_PASSWORD';
    CREATE DATABASE raesenmaeher;
    GRANT ALL PRIVILEGES ON DATABASE raesenmaeher TO raesenmaeher;
EOSQL
