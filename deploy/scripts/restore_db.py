#!/usr/bin/env python3
"""Restore a gzip MySQL backup. Destructive: requires explicit --yes.

Usage:
    python3 deploy/scripts/restore_db.py /srv/dyeingtime-backups/dyeingtime-...sql.gz --yes
"""
from __future__ import annotations

import gzip
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ENV_FILE = Path(os.environ.get("DYEINGTIME_ENV_FILE", "/etc/dyeingtime/backend.env"))


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
    if len(sys.argv) < 3 or sys.argv[-1] != "--yes":
        print("Refusing destructive restore without --yes", file=sys.stderr)
        return 2
    backup = Path(sys.argv[1])
    values = load_env(ENV_FILE)
    parsed = urlparse(values["DATABASE_URL"])
    db_name = parsed.path.lstrip("/")
    query = parse_qs(parsed.query)
    socket = (query.get("unix_socket") or [None])[0]
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 3306)
    user = unquote(parsed.username or "root")
    password = unquote(parsed.password or "")
    env = dict(os.environ)
    if password:
        env["MYSQL_PWD"] = password
    # Drop/recreate only the configured database. This is intentionally explicit.
    drop = subprocess.run(
        ["mysql", "-u", user, *(["--socket", socket] if socket else ["-h", host, "-P", port]),
         "-e", f"DROP DATABASE IF EXISTS `{db_name}`; CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"],
        env=env,
    )
    if drop.returncode != 0:
        return drop.returncode
    with gzip.open(backup, "rb") as fh:
        proc = subprocess.run(
            ["mysql", "-u", user, *(["--socket", socket] if socket else ["-h", host, "-P", port]), db_name],
            stdin=fh,
            env=env,
        )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
