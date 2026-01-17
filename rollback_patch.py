#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

EXCLUDE_DIRS = {".git", ".venv", "venv", "dist", "build", "__pycache__", ".mypy_cache", ".pytest_cache"}

def iter_baks(root: Path):
    for p in root.rglob("*.py.bak"):
        if set(p.parts) & EXCLUDE_DIRS:
            continue
        yield p

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    restored = 0
    for bak in iter_baks(root):
        original = bak.with_suffix("")
        try:
            original.write_bytes(bak.read_bytes())
            restored += 1
            print(f"[RESTORE] {original} <= {bak.name}")
        except Exception as e:
            print(f"[WARN] Failed restore {original}: {e}")

    if restored == 0:
        print("[INFO] Restore edilecek *.py.bak bulunamadı.")
    else:
        print(f"[DONE] Restored {restored} file(s).")

if __name__ == "__main__":
    main()
