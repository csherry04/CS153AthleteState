#!/usr/bin/env python3
"""Run the FastAPI coaching backend."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from uvicorn import run


def main():
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not set.")
        print("Set it with: export OPENROUTER_API_KEY=sk-or-...")
        sys.exit(1)

    run("src.coach_api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
