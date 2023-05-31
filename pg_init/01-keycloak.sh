#!/bin/bash
if [ -z "$KEYCLOAK_PASSWORD" ]
then
  echo "KEYCLOAK_PASSWORD not set"
  exit 1
fi
set -e
# FIXME: Can we use mTLS for auth ??
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER keycloak WITH ENCRYPTED PASSWORD '$KEYCLOAK_PASSWORD';
    CREATE DATABASE keycloak;
    GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
EOSQL
