#!/bin/sh
echo "Cron: Calling the sync Secret."
curl --no-progress-meter -H "API-Key:$FLASK_API_KEY" http://kubestash-v2.kubestash-v2.svc.cluster.local/syncnow
