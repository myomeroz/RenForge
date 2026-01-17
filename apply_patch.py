#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
from pathlib import Path

EXCLUDE_DIRS = {".git", ".venv", "venv", "dist", "build", "__pycache__", ".mypy_cache", ".pytest_cache"}
MARKER = "# [RF_PERF_FIX_V14]"
ENV_ENABLE = "(__import__('os').getenv('RENFORGE_TABLE_PERF','1').strip().lower() not in {'0','false','no','off'})"

def backup(path: Path, original_text: str):
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        bak.write_text(original_text, encoding="utf-8")

def ensure_imports(txt: str) -> str:
    need = [
        "import os",
        "from PySide6.QtWidgets import QAbstractItemView, QHeaderView",
    ]
    # add os if missing
    lines = txt.splitlines(True)
    if "import os" not in txt:
        # insert at top after shebang/coding
        insert_at = 0
        if lines and lines[0].startswith("#!"):
            insert_at = 1
        if len(lines) > insert_at and "coding" in lines[insert_at]:
            insert_at += 1
        lines.insert(insert_at, "import os\n")
    txt = "".join(lines)

    if "QAbstractItemView" not in txt or "QHeaderView" not in txt:
        # Try to append to existing PySide6.QtWidgets import line if present
        m = re.search(r"(?m)^(from\s+PySide6\.QtWidgets\s+import\s+)(.+)$", txt)
        if m:
            head, rest = m.group(1), m.group(2)
            parts = [p.strip() for p in rest.split(",")]
            for name in ["QAbstractItemView", "QHeaderView"]:
                if name not in parts:
                    parts.append(name)
            new_line = head + ", ".join(parts)
            txt = re.sub(r"(?m)^from\s+PySide6\.QtWidgets\s+import\s+.+$", new_line, txt, count=1)
        else:
            # Insert a new import near top
            lines = txt.splitlines(True)
            insert_at = 0
            if lines and lines[0].startswith("#!"):
                insert_at = 1
            if len(lines) > insert_at and "coding" in lines[insert_at]:
                insert_at += 1
            # after initial imports block
            while insert_at < len(lines) and (lines[insert_at].startswith("import ") or lines[insert_at].startswith("from ")):
                insert_at += 1
            lines.insert(insert_at, "from PySide6.QtWidgets import QAbstractItemView, QHeaderView\n")
            txt = "".join(lines)
    return txt

def patch_file_table_view(path: Path) -> bool:
    txt0 = path.read_text(encoding="utf-8", errors="ignore")
    if MARKER in txt0:
        print(f"[SKIP] {path}: already patched.")
        return False

    txt = ensure_imports(txt0)

    # 1) Inject perf defaults inside FileTableView.__init__ after super().__init__
    # Try to find class FileTableView and its __init__
    m_cls = re.search(r"(?m)^\s*class\s+FileTableView\b.*:\s*$", txt)
    if not m_cls:
        print(f"[SKIP] {path}: class FileTableView not found.")
        return False

    # find __init__ after class
    cls_start = m_cls.start()
    txt_after = txt[cls_start:]
    m_init = re.search(r"(?m)^(\s*)def\s+__init__\s*\(.*\)\s*:\s*$", txt_after)
    if not m_init:
        print(f"[SKIP] {path}: __init__ not found in FileTableView.")
        return False

    init_indent = m_init.group(1)
    init_pos = cls_start + m_init.start()
    # find line with super().__init__
    lines = txt.splitlines(True)
    # compute init line index
    char_count = 0
    init_line_idx = 0
    for i,l in enumerate(lines):
        if char_count <= init_pos < char_count + len(l):
            init_line_idx = i
            break
        char_count += len(l)

    # scan forward in init to find super init call
    super_idx = None
    for j in range(init_line_idx, min(init_line_idx+80, len(lines))):
        if "super().__init__(" in lines[j] or "super().__init__()" in lines[j]:
            super_idx = j
            break
    if super_idx is None:
        # fallback: first non-empty line after def
        super_idx = init_line_idx + 1

    body_indent = init_indent + " " * 4
    inject = [
        f"{body_indent}{MARKER}\n",
        f"{body_indent}if {ENV_ENABLE}:\n",
        f"{body_indent}    try:\n",
        f"{body_indent}        # Large-table defaults\n",
        f"{body_indent}        self.setSortingEnabled(False)\n",
        f"{body_indent}        self.setWordWrap(False)\n",
        f"{body_indent}        self.setUniformRowHeights(True)\n",
        f"{body_indent}        self.setAlternatingRowColors(False)\n",
        f"{body_indent}        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)\n",
        f"{body_indent}        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)\n",
        f"{body_indent}        vh = self.verticalHeader()\n",
        f"{body_indent}        try:\n",
        f"{body_indent}            vh.setSectionResizeMode(QHeaderView.Fixed)\n",
        f"{body_indent}        except Exception:\n",
        f"{body_indent}            pass\n",
        f"{body_indent}        try:\n",
        f"{body_indent}            vh.setDefaultSectionSize(26)\n",
        f"{body_indent}        except Exception:\n",
        f"{body_indent}            pass\n",
        f"{body_indent}        hh = self.horizontalHeader()\n",
        f"{body_indent}        try:\n",
        f"{body_indent}            hh.setSectionResizeMode(QHeaderView.Interactive)\n",
        f"{body_indent}        except Exception:\n",
        f"{body_indent}            pass\n",
        f"{body_indent}        try:\n",
        f"{body_indent}            hh.setStretchLastSection(True)\n",
        f"{body_indent}        except Exception:\n",
        f"{body_indent}            pass\n",
        f"{body_indent}    except Exception:\n",
        f"{body_indent}        pass\n",
    ]

    # Insert right after super init line
    insert_at = super_idx + 1
    lines[insert_at:insert_at] = inject
    txt = "".join(lines)

    # 2) Guard resizeColumnsToContents / resizeRowsToContents to small row counts
    def guard_resize(method_name: str, max_rows: int):
        nonlocal txt
        # Replace "self.resizeColumnsToContents()" -> conditional block
        pat = rf"(?m)^(\s*)self\.{method_name}\(\)\s*$"
        def repl(m):
            ind = m.group(1)
            return (f"{ind}# [RF_PERF_FIX_V14] guarded {method_name}\n"
                    f"{ind}try:\n"
                    f"{ind}    _m = self.model() if hasattr(self, 'model') else None\n"
                    f"{ind}    _rc = _m.rowCount() if _m is not None else 0\n"
                    f"{ind}    if _rc and _rc <= {max_rows}:\n"
                    f"{ind}        self.{method_name}()\n"
                    f"{ind}except Exception:\n"
                    f"{ind}    pass")
        txt = re.sub(pat, repl, txt)

    guard_resize("resizeColumnsToContents", 600)
    guard_resize("resizeRowsToContents", 600)

    if txt == txt0:
        print(f"[SKIP] {path}: no change.")
        return False

    backup(path, txt0)
    path.write_text(txt, encoding="utf-8")
    print(f"[OK] {path}: applied table perf defaults + guarded resizes.")
    return True

def patch_project_model(path: Path) -> bool:
    txt0 = path.read_text(encoding="utf-8", errors="ignore")
    if "File already open" not in txt0:
        print(f"[SKIP] {path}: 'File already open' not found.")
        return False
    txt = re.sub(r'(?m)^(\s*)logger\.warning\((.*File already open.*)\)\s*$', r'\1logger.debug(\2)', txt0)
    if txt == txt0:
        print(f"[SKIP] {path}: no change.")
        return False
    backup(path, txt0)
    path.write_text(txt, encoding="utf-8")
    print(f"[OK] {path}: downgraded 'File already open' WARNING -> DEBUG.")
    return True

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    changed = False

    ftv = root / "gui" / "views" / "file_table_view.py"
    if ftv.exists():
        changed |= patch_file_table_view(ftv)
    else:
        print(f"[NOT FOUND] {ftv}")

    pm = root / "models" / "project_model.py"
    if pm.exists():
        changed |= patch_project_model(pm)
    else:
        print(f"[NOT FOUND] {pm}")

    if changed:
        print("[DONE] v14 applied. Run app and open 11.5k file.")
    else:
        print("[DONE] No changes applied.")

if __name__ == "__main__":
    main()
