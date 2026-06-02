#!/usr/bin/env python3
"""Run the FastAPI coaching backend."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from uvicorn import run


def load_local_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    load_local_env()
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set.")
        print("Set it with: export OPENAI_API_KEY=your_key_here")
        sys.exit(1)

    run("src.coach_api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
