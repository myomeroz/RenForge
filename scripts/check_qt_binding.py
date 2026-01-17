#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qt Binding Consistency Checker for RenForge

CI-style script that scans the repository for forbidden Qt binding strings.
Exit code 0 = pass, exit code 1 = violations found.

Usage:
    python scripts/check_qt_binding.py
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Root of the repository
REPO_ROOT = Path(__file__).parent.parent

# Directories to skip
SKIP_DIRS = {
    '__pycache__',
    '.git',
    '.venv',
    'venv',
    'node_modules',
    '.mypy_cache',
    '.pytest_cache',
}

# Files to skip (relative to repo root)
SKIP_FILES = {
    'scripts/check_qt_binding.py',  # This script itself
}

# Forbidden patterns with descriptions
FORBIDDEN_PATTERNS = [
    (r'\bfrom PyQt6\b', 'PyQt6 import'),
    (r'\bimport PyQt6\b', 'PyQt6 import'),
    (r'\bpyqtSignal\b', 'pyqtSignal (use Signal from PySide6)'),
    (r'\bpyqtSlot\b', 'pyqtSlot (use Slot from PySide6)'),
]

# Allowed patterns (exceptions) - e.g., comments explaining migration
ALLOWED_CONTEXTS = [
    r'#.*PyQt6',  # Comments mentioning PyQt6
    r'""".*PyQt6.*"""',  # Docstrings
    r"'''.*PyQt6.*'''",  # Docstrings
]


def should_skip_path(path: Path) -> bool:
    """Check if a path should be skipped."""
    # Skip directories
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    
    # Skip specific files
    rel_path = path.relative_to(REPO_ROOT)
    if str(rel_path).replace('\\', '/') in SKIP_FILES:
        return True
    
    return False


def is_allowed_context(line: str, pattern: str) -> bool:
    """Check if a match is in an allowed context (like a comment)."""
    stripped = line.strip()
    # Allow if the line is a comment
    if stripped.startswith('#'):
        return True
    # Allow if it's inside a docstring (basic check)
    if '"""' in line or "'''" in line:
        return True
    return False


def scan_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    Scan a single file for forbidden patterns.
    
    Returns:
        List of (line_number, line_content, violation_type)
    """
    violations = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return violations
    
    for line_num, line in enumerate(lines, start=1):
        for pattern, description in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                # Check if it's in an allowed context
                if not is_allowed_context(line, pattern):
                    violations.append((line_num, line.rstrip(), description))
    
    return violations


def scan_repository() -> dict:
    """
    Scan the entire repository for Qt binding violations.
    
    Returns:
        Dict mapping filepath to list of violations
    """
    results = {}
    
    for py_file in REPO_ROOT.rglob('*.py'):
        if should_skip_path(py_file):
            continue
        
        violations = scan_file(py_file)
        if violations:
            rel_path = py_file.relative_to(REPO_ROOT)
            results[str(rel_path)] = violations
    
    return results


def print_report(results: dict) -> None:
    """Print a formatted report of violations."""
    if not results:
        print("✅ No Qt binding violations found!")
        print("\nAll files use PySide6 correctly.")
        return
    
    total_violations = sum(len(v) for v in results.values())
    print(f"❌ Found {total_violations} violation(s) in {len(results)} file(s):\n")
    
    for filepath, violations in sorted(results.items()):
        print(f"  📄 {filepath}")
        for line_num, line_content, violation_type in violations:
            print(f"     Line {line_num}: {violation_type}")
            print(f"       → {line_content[:80]}...")
        print()
    
    print("=" * 60)
    print(f"Summary: {total_violations} violations in {len(results)} files")
    print("=" * 60)
    print("\nFix these by:")
    print("  - Replace 'from PyQt6' with 'from PySide6'")
    print("  - Replace 'pyqtSignal' with 'Signal'")
    print("  - Replace 'pyqtSlot' with 'Slot'")
    print("  - Or use the central module: from gui.qt import ...")


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("RenForge Qt Binding Consistency Check")
    print("=" * 60)
    print(f"Scanning: {REPO_ROOT}")
    print()
    
    results = scan_repository()
    print_report(results)
    
    # Exit with error code if violations found
    if results:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
