"""Copy repo canvases/ into Cursor's managed canvases folder for IDE preview."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURSOR_DIR = Path.home() / ".cursor/projects/Users-callumsherry-athlete-state-model/canvases"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync canvases from repo to Cursor IDE folder.")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "canvases")
    parser.add_argument("--target", type=Path, default=DEFAULT_CURSOR_DIR)
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Source directory not found: {args.source}", file=sys.stderr)
        raise SystemExit(1)

    args.target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sorted(args.source.glob("*.canvas.tsx")):
        shutil.copy2(path, args.target / path.name)
        copied += 1
    print(f"Synced {copied} canvas file(s) to {args.target}")


if __name__ == "__main__":
    main()
