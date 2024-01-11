#!/bin/sh
until nc -vz kubestash-v2.kubestash-v2.svc.cluster.local 80 
do
  sleep 100
done

WAIT_SECONDS=$((CRON_HOURS * 60 * 60))

# Sync at startup
while true;
do 
  sh /app/syncSecret.sh
  sleep $WAIT_SECONDS
done
