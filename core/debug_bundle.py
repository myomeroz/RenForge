# -*- coding: utf-8 -*-
"""
RenForge Debug Bundle Generator (Stage 11)

Generates a comprehensive debug bundle containing:
1. Masked JSON report
2. Masked Markdown report
3. Recent log snippets (masked)
"""

from core.batch_report import build_markdown_from_run, format_json_from_run, mask_sensitive, mask_path
from core.log_store import instance as get_log_buffer

def build_debug_bundle(run_record) -> str:
    """
    Build a single text blob containing detailed debug info for a run.
    Everything is masked/sanitized for safe sharing.
    """
    sections = []
    
    # Header
    sections.append("=== RENFORGE DEBUG BUNDLE ===")
    sections.append(f"Timestamp: {run_record.timestamp}")
    if run_record.file_name:
        sections.append(f"File: {mask_path(run_record.file_name)}")
    sections.append("")
    
    # 1. JSON Report
    try:
        json_report = format_json_from_run(run_record)
        sections.append("=== [1] JSON REPORT ===")
        sections.append(json_report)
        sections.append("")
    except Exception as e:
        sections.append(f"!! JSON Report Generation Failed: {e}")
        sections.append("")
        
    # 2. Markdown Report
    try:
        md_report = build_markdown_from_run(run_record)
        sections.append("=== [2] MARKDOWN REPORT ===")
        sections.append(md_report)
        sections.append("")
    except Exception as e:
        sections.append(f"!! Markdown Report Generation Failed: {e}")
        sections.append("")
        
    # 3. Recent Logs
    try:
        # Get last 200 lines
        logs = get_log_buffer().get_logs(limit=200)
        
        sections.append("=== [3] RECENT LOGS (Last 200 lines) ===")
        sections.append("Note: Logs are filtered to 'renforge.*' and masked.")
        sections.append("")
        
        if logs:
            for line in logs:
                # Apply masking to log line (paths, secrets)
                masked_line = mask_sensitive(line)
                
                # Additional path masking for logs (brute force common paths)
                # mask_path helper is too specific (basename only), we want to mask prefixes
                # but mask_sensitive handles secrets. Let's rely on mask_sensitive and manual path masking.
                
                # Check for absolute paths pattern in logs (roughly)
                # We won't be perfect, but we try common patterns
                import re
                # Windows Users path
                masked_line = re.sub(r'[C-Zc-z]:[\\/]Users[\\/][^\\/]+', 'C:/Users/[REDACTED]', masked_line)
                
                sections.append(masked_line)
        else:
            sections.append("(No logs in buffer)")
            
    except Exception as e:
        sections.append(f"!! Log Retrieval Failed: {e}")
    
    sections.append("")
    sections.append("=== END DEBUG BUNDLE ===")
    
    return "\n".join(sections)
