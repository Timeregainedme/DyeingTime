#!/usr/bin/env python3
"""Run a command with key=value pairs from an EnvironmentFile-like file.

Why: production `.env` intentionally contains values with spaces and shell
metacharacters. Sourcing it from bash is unsafe; this loader passes the exact
values through `os.environ` to the child process.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: with_env.py <env-file> <command> [args...]", file=sys.stderr)
        return 2
    env_file = Path(sys.argv[1])
    env = dict(os.environ)
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value
    return subprocess.call(sys.argv[2:], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
