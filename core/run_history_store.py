# -*- coding: utf-8 -*-
"""
RenForge Run History Store

Stores batch run history for the Health Panel dashboard.
Persistence: project-first (if project open) + global fallback.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from renforge_logger import get_logger

logger = get_logger("core.run_history_store")

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RunRecord:
    """Single batch run record."""
    timestamp: str                          # ISO format local time
    
    # File info
    file_name: Optional[str] = None         # Filename (basename)
    file_path: Optional[str] = None         # Full path (for reference)
    
    # Context (sanitized - no API keys)
    provider: Optional[str] = None          # e.g., "gemini", "google"
    model: Optional[str] = None             # e.g., "gemini-2.0-flash"
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    chunk_size: Optional[int] = None
    
    # Summary counts
    processed: int = 0
    success_updated: int = 0
    errors_count: int = 0
    qc_count_updated: int = 0               # QC issues in updated rows only
    qc_count_total: int = 0                 # Total QC issues in file
    duration_ms: int = 0
    
    # Breakdowns
    error_category_counts: Dict[str, int] = field(default_factory=dict)
    qc_code_counts: Dict[str, int] = field(default_factory=dict)
    
    # Row IDs for navigation (Stage 8.2)
    error_row_ids: List[int] = field(default_factory=list)  # Source row indices with errors
    qc_row_ids: List[int] = field(default_factory=list)     # Source row indices with QC issues
    
    # Report paths (optional)
    last_report_md_path: Optional[str] = None
    last_report_json_path: Optional[str] = None


# =============================================================================
# PERSISTENCE PATHS
# =============================================================================

def get_global_history_path() -> Path:
    """Get global run history file path (~/.renforge/run_history.json)."""
    home = Path.home()
    renforge_dir = home / ".renforge"
    renforge_dir.mkdir(exist_ok=True)
    return renforge_dir / "run_history.json"


def get_project_history_path(project_path: str) -> Optional[Path]:
    """Get project-specific run history file path."""
    if not project_path:
        return None
    project_dir = Path(project_path)
    if project_dir.is_file():
        project_dir = project_dir.parent
    renforge_dir = project_dir / ".renforge"
    renforge_dir.mkdir(exist_ok=True)
    return renforge_dir / "run_history.json"


# =============================================================================
# STORE CLASS
# =============================================================================

class RunHistoryStore:
    """
    Manages run history with project-first + global fallback persistence.
    
    - If project is open: store in project/.renforge/run_history.json
    - Always also update global ~/.renforge/run_history.json as fallback
    - Limit to MAX_RECORDS per store
    """
    
    MAX_RECORDS = 50  # Keep last 50 runs
    
    _instance = None  # Singleton
    
    def __init__(self):
        self._runs: List[RunRecord] = []
        self._project_path: Optional[str] = None
        self._loaded = False
    
    @classmethod
    def instance(cls) -> 'RunHistoryStore':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = RunHistoryStore()
        return cls._instance
    
    def set_project_path(self, project_path: Optional[str]):
        """Set current project path for persistence."""
        self._project_path = project_path
        # Reload from project if changed
        if project_path:
            self._load_from_project()
        else:
            self._load_from_global()
    
    def add_run(self, record: RunRecord):
        """Add a run record and persist."""
        self._runs.insert(0, record)  # Most recent first
        
        # Trim to max
        if len(self._runs) > self.MAX_RECORDS:
            self._runs = self._runs[:self.MAX_RECORDS]
        
        # Persist
        self._save()
        
        logger.info(f"Run recorded: {record.processed} processed, {record.errors_count} errors, {record.qc_count_updated} QC")
    
    def get_last_run(self) -> Optional[RunRecord]:
        """Get the most recent run."""
        return self._runs[0] if self._runs else None
    
    def get_runs(self, n: int = 10) -> List[RunRecord]:
        """Get last N runs (most recent first, deterministic order by timestamp desc)."""
        # Sort by timestamp descending to ensure deterministic order
        sorted_runs = sorted(self._runs, key=lambda r: r.timestamp, reverse=True)
        return sorted_runs[:n]
    
    def get_aggregated_stats(self, n: int = 10) -> Dict[str, Any]:
        """
        Get aggregated statistics from last N runs.
        
        Returns:
            Dict with:
                - total_runs
                - total_processed
                - total_errors
                - total_qc
                - error_category_totals (sorted by count desc)
                - qc_code_totals (sorted by count desc)
        """
        runs = self.get_runs(n)
        
        error_cats: Dict[str, int] = {}
        qc_codes: Dict[str, int] = {}
        total_processed = 0
        total_errors = 0
        total_qc = 0
        
        for run in runs:
            total_processed += run.processed
            total_errors += run.errors_count
            total_qc += run.qc_count_updated
            
            for cat, count in run.error_category_counts.items():
                error_cats[cat] = error_cats.get(cat, 0) + count
            
            for code, count in run.qc_code_counts.items():
                qc_codes[code] = qc_codes.get(code, 0) + count
        
        # Sort by count descending, then by name for determinism
        sorted_error_cats = sorted(error_cats.items(), key=lambda x: (-x[1], x[0]))
        sorted_qc_codes = sorted(qc_codes.items(), key=lambda x: (-x[1], x[0]))
        
        return {
            'total_runs': len(runs),
            'total_processed': total_processed,
            'total_errors': total_errors,
            'total_qc': total_qc,
            'error_category_totals': sorted_error_cats[:5],  # Top 5
            'qc_code_totals': sorted_qc_codes[:5]  # Top 5
        }
    
    def get_first_error_row_id(self, model) -> Optional[int]:
        """
        Get min(row_id) of rows with errors.
        
        Args:
            model: TranslationTableModel with _rows
            
        Returns:
            Minimum row_id with error, or None
        """
        if not model or not hasattr(model, '_rows'):
            return None
        
        error_rows = []
        for idx, row in enumerate(model._rows):
            if getattr(row, 'status', None) and row.status.value == 'error':
                error_rows.append(idx)
        
        return min(error_rows) if error_rows else None
    
    def get_first_qc_row_id(self, model) -> Optional[int]:
        """
        Get min(row_id) of rows with QC issues.
        
        Args:
            model: TranslationTableModel with _rows
            
        Returns:
            Minimum row_id with QC issue, or None
        """
        if not model or not hasattr(model, '_rows'):
            return None
        
        qc_rows = []
        for idx, row in enumerate(model._rows):
            if getattr(row, 'qc_flag', False):
                qc_rows.append(idx)
        
        return min(qc_rows) if qc_rows else None
    
    def clear(self):
        """Clear all run history."""
        self._runs = []
        self._save()
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def _save(self):
        """Save to both project (if available) and global."""
        data = [asdict(r) for r in self._runs]
        
        # Save to project if available
        if self._project_path:
            project_path = get_project_history_path(self._project_path)
            if project_path:
                try:
                    with open(project_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    logger.debug(f"Run history saved to project: {project_path}")
                except Exception as e:
                    logger.warning(f"Failed to save project run history: {e}")
        
        # Always save to global
        global_path = get_global_history_path()
        try:
            with open(global_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Run history saved to global: {global_path}")
        except Exception as e:
            logger.warning(f"Failed to save global run history: {e}")
    
    def _load_from_project(self):
        """Load from project path."""
        if not self._project_path:
            return
        
        project_path = get_project_history_path(self._project_path)
        if project_path and project_path.exists():
            self._load_from_file(project_path)
        else:
            # Fallback to global
            self._load_from_global()
    
    def _load_from_global(self):
        """Load from global path."""
        global_path = get_global_history_path()
        if global_path.exists():
            self._load_from_file(global_path)
        else:
            self._runs = []
    
    def _load_from_file(self, path: Path):
        """Load run history from a JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._runs = []
            for item in data:
                # Convert dict to RunRecord
                record = RunRecord(
                    timestamp=item.get('timestamp', ''),
                    file_name=item.get('file_name'),
                    file_path=item.get('file_path'),
                    provider=item.get('provider'),
                    model=item.get('model'),
                    source_lang=item.get('source_lang'),
                    target_lang=item.get('target_lang'),
                    chunk_size=item.get('chunk_size'),
                    processed=item.get('processed', 0),
                    success_updated=item.get('success_updated', 0),
                    errors_count=item.get('errors_count', 0),
                    qc_count_updated=item.get('qc_count_updated', 0),
                    qc_count_total=item.get('qc_count_total', 0),
                    duration_ms=item.get('duration_ms', 0),
                    error_category_counts=item.get('error_category_counts', {}),
                    qc_code_counts=item.get('qc_code_counts', {}),
                    error_row_ids=item.get('error_row_ids', []),  # Backward compat
                    qc_row_ids=item.get('qc_row_ids', [])  # Backward compat
                )
                self._runs.append(record)
            
            logger.info(f"Loaded {len(self._runs)} run records from {path}")
            self._loaded = True
            
        except Exception as e:
            logger.warning(f"Failed to load run history from {path}: {e}")
            self._runs = []
    
    def ensure_loaded(self):
        """Ensure history is loaded (call on app start)."""
        if not self._loaded:
            self._load_from_global()
