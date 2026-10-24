#!/usr/bin/env bash
# Immutable release deployment for the internal production host.
# Usage: sudo deploy/scripts/deploy_release.sh /srv/dyeingtime/releases/v2-internal-beta.1
set -euo pipefail

RELEASE_DIR="${1:?usage: deploy_release.sh <absolute-release-dir>}"
ENV_FILE="${DYEINGTIME_ENV_FILE:-/etc/dyeingtime/backend.env}"
CURRENT_LINK="/srv/dyeingtime/current"
PREVIOUS_LINK="/srv/dyeingtime/previous"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

[[ -d "$RELEASE_DIR/backend" && -d "$RELEASE_DIR/front" ]] || { echo "invalid release dir: $RELEASE_DIR" >&2; exit 2; }
[[ -f "$ENV_FILE" ]] || { echo "missing env file: $ENV_FILE" >&2; exit 2; }

# Refuse to deploy while a real video task is running.
ACTIVE=$(mysql --batch --skip-column-names -e "SELECT COUNT(*) FROM ${DYEINGTIME_DB:-dyeingtime}.generation_tasks WHERE task_kind='video_generation' AND status IN ('pending','running');" 2>/dev/null || true)
if [[ "${ACTIVE:-0}" != "0" ]]; then
  echo "refusing deploy: ${ACTIVE} active video task(s)" >&2
  exit 3
fi

echo "[1/8] backup database"
python3 "$ROOT_DIR/deploy/scripts/backup_db.py"

echo "[2/8] build frontend"
sudo -u ubuntu bash -lc "cd '$RELEASE_DIR/front' && pnpm install --frozen-lockfile && pnpm run build"

echo "[3/8] create backend venv"
sudo -u ubuntu bash -lc "cd '$RELEASE_DIR/backend' && uv sync --frozen --no-dev"

echo "[4/8] apply additive SQL migrations 034-050"
DB_NAME=$(python3 - "$ENV_FILE" <<'PY'
import sys
from urllib.parse import urlparse
for line in open(sys.argv[1]):
    if line.startswith('DATABASE_URL='):
        print(urlparse(line.split('=',1)[1].strip()).path.lstrip('/'))
        break
PY
)
for f in "$RELEASE_DIR"/backend/sql/*.sql; do
  n=$(basename "$f" | sed 's/^\([0-9]\+\).*/\1/')
  n=$((10#$n))
  if (( n >= 34 )); then
    echo "  apply $(basename "$f")"
    mysql "$DB_NAME" < "$f"
  fi
done

echo "[5/8] ensure ORM tables"
python3 "$ROOT_DIR/deploy/scripts/with_env.py" "$ENV_FILE" "$RELEASE_DIR/backend/.venv/bin/python" "$RELEASE_DIR/backend/init_db.py"

echo "[6/8] install units + switch release symlink"
cp "$ROOT_DIR/deploy/systemd/"*.service "$ROOT_DIR/deploy/systemd/"*.timer /etc/systemd/system/
cp "$ROOT_DIR/deploy/scripts/backup_db.py" /usr/local/sbin/dyeingtime-backup-db.py
chmod 700 /usr/local/sbin/dyeingtime-backup-db.py
cp "$ROOT_DIR/deploy/scripts/health-check.sh" /usr/local/sbin/dyeingtime-health-check.sh
chmod 700 /usr/local/sbin/dyeingtime-health-check.sh
systemctl daemon-reload
systemctl enable --now dyeingtime-backup.timer dyeingtime-staging-api.service
if [[ -L "$CURRENT_LINK" ]]; then
  readlink -f "$CURRENT_LINK" > /tmp/dyeingtime-previous-release
  ln -sfn "$(readlink -f "$CURRENT_LINK")" "$PREVIOUS_LINK"
elif [[ -e "$CURRENT_LINK" ]]; then
  echo "$CURRENT_LINK exists but is not a symlink; aborting" >&2
  exit 4
fi
ln -sfn "$RELEASE_DIR" "$CURRENT_LINK"

echo "[7/8] restart services"
systemctl restart dyeingtime-api dyeingtime-celery dyeingtime-celery-image dyeingtime-celery-video dyeingtime-go

echo "[8/8] switch nginx + verify"
cp "$ROOT_DIR/deploy/nginx/sites-enabled/dyeingtime" /etc/nginx/sites-enabled/dyeingtime
cp "$ROOT_DIR/deploy/nginx/snippets/dyeingtime-proxy.conf" /etc/nginx/snippets/dyeingtime-proxy.conf
cp "$ROOT_DIR/deploy/nginx/staging.conf" /etc/nginx/sites-available/dyeingtime-staging
ln -sfn /etc/nginx/sites-available/dyeingtime-staging /etc/nginx/sites-enabled/dyeingtime-staging
nginx -t
systemctl reload nginx
for i in $(seq 1 30); do
  if curl -fsS --max-time 3 http://127.0.0.1:8002/health >/dev/null; then break; fi
  sleep 2
done
curl -fsS http://127.0.0.1:8002/health
curl -fsS https://tim.run.place/health
curl -fsS https://tim.run.place/api/v1/ready
echo
echo "release deployed: $RELEASE_DIR"
