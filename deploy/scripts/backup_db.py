#!/usr/bin/env python3
"""Create a consistent MySQL backup before migrations/releases.

Usage (as root on the production host):
    python3 deploy/scripts/backup_db.py
Environment overrides:
    DYEINGTIME_ENV_FILE=/etc/dyeingtime/backend.env
    DYEINGTIME_BACKUP_DIR=/srv/dyeingtime-backups
"""
from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ENV_FILE = Path(os.environ.get("DYEINGTIME_ENV_FILE", "/etc/dyeingtime/backend.env"))
BACKUP_DIR = Path(os.environ.get("DYEINGTIME_BACKUP_DIR", "/srv/dyeingtime-backups"))
RETENTION_DAYS = int(os.environ.get("DYEINGTIME_BACKUP_RETENTION_DAYS", "14"))


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value
    return values


def main() -> int:
    values = load_env(ENV_FILE)
    database_url = values.get("DATABASE_URL", "")
    if not database_url:
        print("DATABASE_URL missing", file=sys.stderr)
        return 1
    parsed = urlparse(database_url)
    if parsed.scheme not in {"mysql+aiomysql", "mysql+pymysql", "mysql"}:
        print(f"unsupported DATABASE_URL scheme: {parsed.scheme}", file=sys.stderr)
        return 1
    db_name = parsed.path.lstrip("/")
    if not db_name:
        print("DATABASE_URL has no database name", file=sys.stderr)
        return 1
    query = parse_qs(parsed.query)
    socket = (query.get("unix_socket") or [None])[0]
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 3306)
    user = unquote(parsed.username or "root")
    password = unquote(parsed.password or "")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    final = BACKUP_DIR / f"dyeingtime-{stamp}.sql.gz"
    tmp = final.with_suffix(".tmp")
    env = dict(os.environ)
    if password:
        env["MYSQL_PWD"] = password
    args = [
        "mysqldump",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--no-tablespaces",
        "--databases",
        db_name,
        "-u",
        user,
    ]
    if socket:
        args += ["--socket", socket]
    else:
        args += ["-h", host, "-P", port]
    with tmp.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6) as gz:
            proc = subprocess.run(args, env=env, stdout=gz, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                print(proc.stderr.decode(errors="replace"), file=sys.stderr)
                tmp.unlink(missing_ok=True)
                return proc.returncode
    tmp.replace(final)
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    (BACKUP_DIR / "SHA256SUMS").open("a").write(f"{digest}  {final.name}\n")
    env_backup = BACKUP_DIR / f"backend-env-{stamp}.env"
    shutil.copyfile(ENV_FILE, env_backup)
    os.chmod(env_backup, 0o600)
    cutoff = datetime.now(UTC).timestamp() - RETENTION_DAYS * 86400
    for old in BACKUP_DIR.glob("dyeingtime-*.sql.gz"):
        if old.stat().st_mtime < cutoff:
            old.unlink(missing_ok=True)
    print(final)
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
