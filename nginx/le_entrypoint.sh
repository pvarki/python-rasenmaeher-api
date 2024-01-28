#!/bin/bash
set -ex
/usr/local/bin/crl_watcher.sh &
WATCHER_PID=$!
echo "Calling original entrypoint"
. /docker-entrypoint.sh
EXITCODE=$?
echo "OG entrypint exited, trying to kill the inotify PID "$WATCHER_PID
kill -9 $WATCHER_PID
echo "Exiting with code "$EXITCODE
exit EXITCODE
