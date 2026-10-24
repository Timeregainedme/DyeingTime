#!/usr/bin/env python3
"""Archive all R2 objects into a local tar.gz for disaster recovery.

R2 is the primary media store; this is a secondary copy of the current bucket.
Objects are streamed into the tar (no second full copy on disk).
"""
from __future__ import annotations

import hashlib
import os
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
from botocore.client import Config

ENV_FILE = Path(os.environ.get("DYEINGTIME_ENV_FILE", "/etc/dyeingtime/backend.env"))
BACKUP_DIR = Path(os.environ.get("DYEINGTIME_BACKUP_DIR", "/srv/dyeingtime-backups"))
RETENTION_DAYS = 28


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
    env = load_env(ENV_FILE)
    client = boto3.client(
        "s3",
        endpoint_url=env.get("S3_ENDPOINT_URL"),
        region_name=env.get("S3_REGION_NAME", "auto"),
        aws_access_key_id=env.get("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=env.get("S3_SECRET_ACCESS_KEY"),
        config=Config(s3={"addressing_style": env.get("S3_ADDRESSING_STYLE", "path")}),
    )
    bucket = env["S3_BUCKET_NAME"]
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    final = BACKUP_DIR / f"media-{stamp}.tar.gz"
    tmp = final.with_suffix(".tmp")
    count = 0
    with tarfile.open(tmp, "w:gz") as tar:
        token = None
        while True:
            kwargs = {"Bucket": bucket, "MaxKeys": 1000}
            if token:
                kwargs["ContinuationToken"] = token
            page = client.list_objects_v2(**kwargs)
            for item in page.get("Contents", []):
                key = item["Key"]
                obj = client.get_object(Bucket=bucket, Key=key)
                info = tarfile.TarInfo(name=key)
                info.size = int(obj["ContentLength"])
                info.mtime = int(item["LastModified"].timestamp())
                tar.addfile(info, obj["Body"])
                count += 1
            if not page.get("IsTruncated"):
                break
            token = page.get("NextContinuationToken")
    tmp.replace(final)
    os.chmod(final, 0o600)
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    (BACKUP_DIR / "MEDIA-SHA256SUMS").open("a").write(f"{digest}  {final.name}\n")
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    for old in BACKUP_DIR.glob("media-*.tar.gz"):
        if datetime.fromtimestamp(old.stat().st_mtime, UTC) < cutoff:
            old.unlink(missing_ok=True)
    print(f"{final} objects={count} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
