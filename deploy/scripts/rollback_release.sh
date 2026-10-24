#!/usr/bin/env bash
# Roll back the current symlink to the previous release.
# Usage: sudo deploy/scripts/rollback_release.sh
set -euo pipefail
CURRENT_LINK="/srv/dyeingtime/current"
PREVIOUS_LINK="/srv/dyeingtime/previous"
[[ -L "$PREVIOUS_LINK" ]] || { echo "no previous release symlink" >&2; exit 2; }
PREV=$(readlink -f "$PREVIOUS_LINK")
[[ -d "$PREV/backend" ]] || { echo "previous release missing: $PREV" >&2; exit 2; }
ln -sfn "$PREV" "$CURRENT_LINK"
systemctl restart dyeingtime-api dyeingtime-celery dyeingtime-celery-image dyeingtime-celery-video dyeingtime-go
systemctl reload nginx
for i in $(seq 1 30); do
  if curl -fsS --max-time 3 http://127.0.0.1:8002/health >/dev/null; then break; fi
  sleep 2
done
curl -fsS http://127.0.0.1:8002/health
curl -fsS https://tim.run.place/health
echo "rolled back to: $PREV"
