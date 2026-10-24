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
from typing import Any
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


def _upload_offsite(path: Path, values: dict[str, str]) -> str | None:
    """把备份上传到对象存储，避免备份只存在同一台 EC2。

    为什么必须做：数据库备份若与本机在同一块 EBS 上，磁盘损坏/误删实例时
    备份会一起丢失。复用现有 R2 桶的成本可忽略，因此作为默认行为；
    未配置 S3 时静默跳过，不阻断本地备份。
    """
    bucket = (values.get("S3_BUCKET_NAME") or "").strip()
    if not bucket:
        return None
    import boto3
    from botocore.client import Config as BotoConfig

    client = boto3.client(
        "s3",
        endpoint_url=values.get("S3_ENDPOINT_URL") or None,
        region_name=values.get("S3_REGION_NAME") or "auto",
        aws_access_key_id=values.get("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=values.get("S3_SECRET_ACCESS_KEY"),
        config=BotoConfig(
            s3={"addressing_style": values.get("S3_ADDRESSING_STYLE", "path")}
        ),
    )
    key = f"backups/db/{path.name}"
    client.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": "application/gzip"})
    return f"s3://{bucket}/{key}"


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
    with gzip.open(tmp, "wb", compresslevel=6) as gz:
        proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.read(1024 * 1024)
            if not chunk:
                break
            gz.write(chunk)
        stderr = proc.stderr.read() if proc.stderr is not None else b""
        if proc.wait() != 0:
            print(stderr.decode(errors="replace"), file=sys.stderr)
            tmp.unlink(missing_ok=True)
            return proc.returncode
    tmp.replace(final)
    os.chmod(final, 0o600)
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    (BACKUP_DIR / "SHA256SUMS").open("a").write(f"{digest}  {final.name}\n")
    offsite = _upload_offsite(final, values)
    if offsite:
        print(f"offsite={offsite}")
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
