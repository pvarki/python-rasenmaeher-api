#!/bin/bash
set -ex
mkdir -p /tmp/hapcerts
cat /le_certs/${HAP_CERT_NAME}/fullchain.pem /le_certs/${HAP_CERT_NAME}/privkey.pem >/tmp/hapcerts/merged.pem
/usr/local/bin/crl_watcher.sh &
WATCHER_PID=$!
echo "Calling original entrypoint"
. /usr/local/bin/docker-entrypoint.sh
EXITCODE=$?
echo "OG entrypint exited, trying to kill the inotify PID "$WATCHER_PID
kill -9 $WATCHER_PID
echo "Exiting with code "$EXITCODE
exit EXITCODE
