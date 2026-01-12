
import os
import threading
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Callable

from renforge_logger import get_logger
from renforge_localization import tr
import renforge_config as config
from parser.translate_parser import TranslateParser

# Reuse QA Engine definitions if possible, or define Preflight specific structures
# We'll define a simple Issue structure here to be independent but compatible

class PreflightIssue:
    def __init__(self, severity: str, rule: str, file_path: str, line_num: int, message: str, row_id: int = -1):
        self.severity = severity  # "error", "warning", "info"
        self.rule = rule # e.g. "missing_token"
        self.file_path = file_path
        self.line_num = line_num
        self.message = message
        self.row_id = row_id # Index in file_data items if applicable

class PreflightEngine:
    def __init__(self):
        self.logger = get_logger("core.preflight")
        self._stop_event = threading.Event()
        self.issues: List[PreflightIssue] = []
        self.last_run_time = 0
        self.status = "idle" # idle, running, finished, canceled, error
        
        # Configurable thresholds
        self.check_identical = True
        self.check_length = True
        self.length_threshold = 2.0
        self.block_on_error = True
        
    def cancel(self):
        """Request cancellation of current scan."""
        self._stop_event.set()
        
    def run_scan(self, callback_progress: Callable[[int, int, str], None] = None) -> List[PreflightIssue]:
        """
        Run the full project scan.
        This blocking method is intended to be run in a worker thread.
        callback_progress(current, total, status_msg)
        """
        self.status = "running"
        self.issues = []
        self._stop_event.clear()
        
        try:
            project_path = config.APP_DIR
            if not project_path:
                self.logger.error("No active project to scan.")
                self.status = "error"
                return []
                
            # 1. Gather all .rpy files
            rpy_files = list(Path(project_path).rglob("*.rpy"))
            total_files = len(rpy_files)
            processed_count = 0
            
            self.logger.info(f"Starting preflight scan for {total_files} files.")
            
            # 2. System checks (Packaging readiness)
            self._check_packaging_readiness()
            
            # 3. Content checks
            # Use TranslateParser to inspect translation blocks
            parser = TranslateParser()
            
            for fpath in rpy_files:
                if self._stop_event.is_set():
                    self.status = "canceled"
                    return self.issues
                
                rel_path = fpath.relative_to(project_path)
                msg = f"Scanning {rel_path}..."
                if callback_progress:
                    callback_progress(processed_count, total_files, msg)
                    
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        
                    # parse returns (items, language_code)
                    items, _ = parser.parse(lines)
                    
                    if items:
                         self._scan_file_items(str(fpath), items)
                         
                except Exception as e:
                    self.logger.error(f"Error scanning file {fpath}: {e}")
                    self.issues.append(
                        PreflightIssue("error", "scan_error", str(fpath), 0, f"Failed to parse file: {e}")
                    )
                
                processed_count += 1
                
            self.last_run_time = time.time()
            self.status = "finished" if not self._stop_event.is_set() else "canceled"
            return self.issues
            
        except Exception as e:
            self.logger.error(f"Critical preflight error: {e}")
            self.status = "error"
            self.issues.append(PreflightIssue("error", "critical", "", 0, str(e)))
            return self.issues

    def _check_packaging_readiness(self):
        """Check essential files and system state."""
        # 1. Check for valid locales
        # 2. Check for TM if enabled (we don't know if enabled here, but check if exists)
        # 3. Plugin check
        pass
        
    def _scan_file_items(self, file_path: str, items: List[Any]):
        """Analyze parsed items from a single file."""
        
        # We need to detect "original" and "translation" pairs.
        # This depends on how Parser returns data.
        # Assuming items have 'original', 'translation', 'line_number', 'type'
        
        for idx, item in enumerate(items):
            # Items are ParsedItem dataclass objects
            if not hasattr(item, 'type'):
                continue
                
            item_type = item.type
            # Handle ItemType enum comparison? or string?
            # ItemType is likely an Enum.
            # Using basic string check if str, or value otherwise.
            # Actually preflight checks mainly care about content presence.
            
            # Using attributes from ParsedItem definition
            orig = item.original_text
            trans = item.current_text
            line_num = item.line_index + 1 # Display as 1-indexed
            
            # Filter types
            # ItemType.DIALOGUE for dialogue lines
            # ItemType.TRANSLATE_NEW for string translations
            # We also check SCREEN_TEXT_STATEMENT if applicable?
            from renforge_enums import ItemType
            
            valid_types = [
                ItemType.DIALOGUE, 
                ItemType.TRANSLATE_NEW,
                ItemType.SCREEN_TEXT_STATEMENT,
                ItemType.SCREEN_BUTTON
            ]
            
            if item_type not in valid_types:
                continue
                
            # If no translation, skip validation unless we want to flag untranslated?
            # Issue 3: Untranslated or empty lines (where source is not empty)
            if orig and (trans is None or trans.strip() == ""):
                # Assuming empty translation means "Untranslated" in our model
                # But sometimes validly empty? Usually no.
                # Only flag if not explictly marked as TODO?
                self.issues.append(PreflightIssue("error", "empty_translation", file_path, line_num, tr("pf_empty_trans_msg"), idx))
                continue
                
            if not trans:
                continue

            # 1. Tokens (Interpolation)
            self._check_tokens(file_path, line_num, idx, orig, trans)
            
            # 2. Markup Tags
            self._check_markup(file_path, line_num, idx, orig, trans)
            
            # 4. Identical
            if self.check_identical and orig == trans: 
                # Some short words might be legitimately identical (OK, No, etc.)
                # Simple heuristic: Only warn if length > 3
                if len(orig) > 3:
                     self.issues.append(PreflightIssue("warning", "identical", file_path, line_num, tr("pf_identical_msg"), idx))
                     
            # 5. Length overflow
            if self.check_length and len(orig) > 0:
                ratio = len(trans) / len(orig)
                if ratio > self.length_threshold:
                    self.issues.append(PreflightIssue("warning", "length_overflow", file_path, line_num, tr("pf_length_msg", ratio=f"{ratio:.1f}"), idx))

    def _check_tokens(self, fpath, line, row, orig, trans):
        # Regex for [var], %(var)s, {tag}
        # Simple bracket check reusing regex from QA or similar
        # For now, simplistic [interpolation] check
        
        # Matches [...] but excludes tags usually. RenPy uses [] for variable interpolation mostly.
        # Also %s, %d for old style strings.
        
        # Extract tokens from original
        tokens = re.findall(r'\[.+?\]', orig)
        for token in tokens:
            if token not in trans:
                self.issues.append(PreflightIssue("error", "missing_token", fpath, line, tr("pf_missing_token_msg", token=token), row))

    def _check_markup(self, fpath, line, row, orig, trans):
        # Check for unclosed tags like {b}, {/b}
        # Count {tag} vs {/tag}
        # RenPy tags: {b}, {i}, {s}, {u}, {a=...}, {color=...}, {size=...}, {font=...}
        # We check balanced braces {} generally first? No, content uses {} sometimes.
        # Check standard RenPy tags balance.
        
        tags_to_check = ["b", "i", "u", "s"]
        for t in tags_to_check:
            opener = f"{{{t}}}"
            closer = f"{{/{t}}}"
            
            if trans.count(opener) != trans.count(closer):
                self.issues.append(PreflightIssue("error", "markup_mismatch", fpath, line, tr("pf_markup_msg", tag=t), row))
