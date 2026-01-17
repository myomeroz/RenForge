# -*- coding: utf-8 -*-
"""
RenForge Batch Report Module

Generates structured reports from batch translation results.
Supports Markdown and JSON export formats.
"""

import re
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional

from renforge_logger import get_logger

logger = get_logger("core.batch_report")

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ErrorEntry:
    """Single error entry in the report."""
    table_row: int          # 1-based display row
    row_id: Optional[int]   # 0-based internal ID
    file_line: Optional[int]  # Line number in file (if available)
    code: str               # Error code (e.g., "EMPTY_RESULT", "AUTH_ERROR")
    message: str            # Human-readable message


@dataclass
class QCEntry:
    """Single QC issue entry in the report."""
    table_row: int          # 1-based display row
    file_line: Optional[int]
    codes: List[str]        # QC codes (e.g., ["PLACEHOLDER_MISSING", "LENGTH_LONG"])
    summary: str            # Human-readable summary


@dataclass
class BatchReport:
    """Complete batch report structure."""
    timestamp: str                          # ISO format local time
    file_path: Optional[str] = None         # Opened file path
    file_name: Optional[str] = None         # Just the filename
    
    # Context (sanitized - no API keys)
    provider: Optional[str] = None          # e.g., "gemini", "google"
    model: Optional[str] = None             # e.g., "gemini-2.0-flash"
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    chunk_size: Optional[int] = None
    
    # Summary counts
    total_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    qc_count: int = 0
    
    # Details
    errors: List[ErrorEntry] = field(default_factory=list)
    qc_issues: List[QCEntry] = field(default_factory=list)
    
    # Optional log snippet (masked)
    log_snippet: Optional[str] = None


# =============================================================================
# SENSITIVE DATA MASKING
# =============================================================================

# Patterns that look like sensitive data
SENSITIVE_PATTERNS = [
    # API keys (various formats)
    (r'(["\']?(?:api[_-]?key|apikey|api_key|key|token|secret|password|auth)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})', r'\1[REDACTED]'),
    # Bearer tokens
    (r'(Bearer\s+)([a-zA-Z0-9_\-\.]+)', r'\1[REDACTED]'),
    # Long hex strings (likely keys)
    (r'\b([a-fA-F0-9]{32,})\b', r'[REDACTED_HEX]'),
    # Google API key format
    (r'(AIza[a-zA-Z0-9_\-]{35})', r'[REDACTED_GOOGLE_KEY]'),
    # Generic long alphanumeric (40+ chars, likely tokens)
    (r'\b([a-zA-Z0-9]{40,})\b', r'[REDACTED_TOKEN]'),
]


def mask_sensitive(text: str) -> str:
    """
    Mask sensitive-looking tokens in text.
    
    Args:
        text: Input text that may contain sensitive data
        
    Returns:
        Text with sensitive patterns replaced
    """
    if not text:
        return text
    
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


# =============================================================================
# REPORT BUILDER
# =============================================================================

class BatchReportBuilder:
    """Builds a BatchReport from BatchController and model state."""
    
    @staticmethod
    def build(batch_controller, table_model=None, file_path: str = None) -> BatchReport:
        """
        Build a report from the current batch controller state.
        
        Args:
            batch_controller: The BatchController instance
            table_model: Optional TranslationTableModel to scan for QC issues
            file_path: Optional file path override
            
        Returns:
            BatchReport instance
        """
        report = BatchReport(
            timestamp=datetime.now().isoformat(sep=' ', timespec='seconds')
        )
        
        # File info
        if file_path:
            report.file_path = file_path
            report.file_name = file_path.split('/')[-1].split('\\')[-1]
        elif hasattr(batch_controller, 'main'):
            current_data = batch_controller.main._get_current_file_data()
            if current_data and current_data.file_path:
                report.file_path = current_data.file_path
                report.file_name = current_data.file_path.split('/')[-1].split('\\')[-1]
        
        # Context (from _last_run_context)
        ctx = getattr(batch_controller, '_last_run_context', {}) or {}
        report.provider = ctx.get('engine') or ctx.get('provider')
        report.model = ctx.get('model')
        report.source_lang = ctx.get('source_lang')
        report.target_lang = ctx.get('target_lang')
        report.chunk_size = ctx.get('chunk_size')
        
        # Summary counts
        report.total_processed = getattr(batch_controller, '_total_processed', 0)
        report.success_count = getattr(batch_controller, '_success_count', 0)
        report.error_count = len(getattr(batch_controller, '_structured_errors', []))
        
        # Build error entries
        structured_errors = getattr(batch_controller, '_structured_errors', [])
        for err in structured_errors:
            entry = ErrorEntry(
                table_row=err.get('row_id', 0) + 1,  # 1-based
                row_id=err.get('row_id'),
                file_line=err.get('file_line'),
                code=err.get('code', 'UNKNOWN'),
                message=err.get('message', 'Unknown error')
            )
            report.errors.append(entry)
        
        # Build QC entries from model
        if table_model and hasattr(table_model, '_rows'):
            for idx, row in enumerate(table_model._rows):
                if getattr(row, 'qc_flag', False):
                    entry = QCEntry(
                        table_row=idx + 1,
                        file_line=getattr(row, 'file_line', None),
                        codes=getattr(row, 'qc_codes', []) or [],
                        summary=getattr(row, 'qc_summary', '') or ''
                    )
                    report.qc_issues.append(entry)
        
        report.qc_count = len(report.qc_issues)
        
        return report


# =============================================================================
# FORMATTERS
# =============================================================================

def format_markdown(report: BatchReport, max_errors: int = 50, max_qc: int = 50) -> str:
    """
    Format report as Markdown.
    
    Args:
        report: BatchReport instance
        max_errors: Maximum error entries to include
        max_qc: Maximum QC entries to include
        
    Returns:
        Markdown formatted string
    """
    lines = []
    
    # Header
    lines.append("# Batch Report")
    lines.append("")
    lines.append(f"**Generated:** {report.timestamp}")
    if report.file_name:
        lines.append(f"**File:** {report.file_name}")
    lines.append("")
    
    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Processed | {report.total_processed} |")
    lines.append(f"| Successful | {report.success_count} |")
    lines.append(f"| Errors | {report.error_count} |")
    lines.append(f"| QC Issues | {report.qc_count} |")
    lines.append("")
    
    # Context
    if report.provider or report.model:
        lines.append("## Context")
        lines.append("")
        if report.provider:
            lines.append(f"- **Provider:** {report.provider}")
        if report.model:
            lines.append(f"- **Model:** {report.model}")
        if report.source_lang:
            lines.append(f"- **Source Language:** {report.source_lang}")
        if report.target_lang:
            lines.append(f"- **Target Language:** {report.target_lang}")
        if report.chunk_size:
            lines.append(f"- **Chunk Size:** {report.chunk_size}")
        lines.append("")
    
    # Errors
    if report.errors:
        lines.append("## Errors")
        lines.append("")
        lines.append("| # | Table Row | File Line | Code | Message |")
        lines.append("|---|-----------|-----------|------|---------|")
        
        for i, err in enumerate(report.errors[:max_errors]):
            file_line = str(err.file_line) if err.file_line else "-"
            message = err.message[:80] + "..." if len(err.message) > 80 else err.message
            lines.append(f"| {i+1} | {err.table_row} | {file_line} | {err.code} | {message} |")
        
        if len(report.errors) > max_errors:
            lines.append(f"| ... | *{len(report.errors) - max_errors} more errors* | | | |")
        lines.append("")
    
    # QC Issues
    if report.qc_issues:
        lines.append("## QC Issues")
        lines.append("")
        lines.append("| # | Table Row | File Line | Codes | Summary |")
        lines.append("|---|-----------|-----------|-------|---------|")
        
        for i, qc in enumerate(report.qc_issues[:max_qc]):
            file_line = str(qc.file_line) if qc.file_line else "-"
            codes = ", ".join(qc.codes) if qc.codes else "-"
            summary = qc.summary[:60] + "..." if len(qc.summary) > 60 else qc.summary
            # Escape newlines in summary for table
            summary = summary.replace("\n", " ").replace("|", "\\|")
            lines.append(f"| {i+1} | {qc.table_row} | {file_line} | {codes} | {summary} |")
        
        if len(report.qc_issues) > max_qc:
            lines.append(f"| ... | *{len(report.qc_issues) - max_qc} more issues* | | | |")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("*Generated by RenForge*")
    
    return "\n".join(lines)


def format_json(report: BatchReport) -> str:
    """
    Format report as JSON.
    
    Args:
        report: BatchReport instance
        
    Returns:
        JSON formatted string
    """
    # Convert to dict
    data = {
        'timestamp': report.timestamp,
        'file': {
            'path': report.file_path,
            'name': report.file_name
        },
        'context': {
            'provider': report.provider,
            'model': report.model,
            'source_lang': report.source_lang,
            'target_lang': report.target_lang,
            'chunk_size': report.chunk_size
        },
        'summary': {
            'total_processed': report.total_processed,
            'success_count': report.success_count,
            'error_count': report.error_count,
            'qc_count': report.qc_count
        },
        'errors': [
            {
                'table_row': e.table_row,
                'row_id': e.row_id,
                'file_line': e.file_line,
                'code': e.code,
                'message': e.message
            }
            for e in report.errors
        ],
        'qc_issues': [
            {
                'table_row': q.table_row,
                'file_line': q.file_line,
                'codes': q.codes,
                'summary': q.summary
            }
            for q in report.qc_issues
        ],
        'generator': 'RenForge'
    }
    
    return json.dumps(data, ensure_ascii=False, indent=2)
