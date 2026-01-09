# -*- coding: utf-8 -*-
"""
RenForge Batch Status View

Provides formatting functions for batch translation status and summary messages.
"""

from locales import tr


def format_batch_summary(results: dict) -> str:
    """
    Format batch translation results into a summary message.
    
    Args:
        results: Dict with keys: processed, total, success, errors, warnings, canceled
        
    Returns:
        Formatted summary string for display in MessageBox
    """
    # Robust retrieval with fallbacks
    processed = results.get('processed', results.get('total', 0))
    total = results.get('total', processed)
    success = results.get('success', results.get('success_count', 0))
    canceled = results.get('canceled', False)
    
    # Handle errors (list or count)
    result_errors = results.get('errors', [])
    if not isinstance(result_errors, list):
        result_errors = []
    
    # Handle warnings (list or count)
    warnings_list = results.get('warnings', [])
    if not isinstance(warnings_list, list):
        warnings_list = []
    
    total_error_count = len(result_errors)
    total_warning_count = len(warnings_list)
    
    # Build summary message
    summary = "Batch translation finished.\n\n"
    
    if canceled:
        summary += "TASK CANCELED BY USER\n\n"
    
    summary += f"Lines processed: {processed}/{total}\n"
    summary += f"Successful (text updated): {success}\n"
    
    if total_error_count > 0:
        summary += f"\nErrors: {total_error_count}\n"
        summary += "\nError Details (max 10):\n" + "\n".join(str(e) for e in result_errors[:10])
        if total_error_count > 10:
            summary += "\n..."
    
    if total_warning_count > 0:
        summary += f"\nWarnings (variables '[...]'): {total_warning_count}\n"
        summary += "\nDetails (max 10):\n" + "\n".join(str(w) for w in warnings_list[:10])
        if total_warning_count > 10:
            summary += "\n..."
    
    return summary


def get_status_message(results: dict) -> str:
    """
    Get status bar message for batch completion.
    
    Args:
        results: Dict with keys: errors, warnings, canceled
        
    Returns:
        Status bar message string
    """
    canceled = results.get('canceled', False)
    
    result_errors = results.get('errors', [])
    if not isinstance(result_errors, list):
        result_errors = []
    
    warnings_list = results.get('warnings', [])
    if not isinstance(warnings_list, list):
        warnings_list = []
    
    total_error_count = len(result_errors)
    total_warning_count = len(warnings_list)
    
    if canceled:
        return "Batch translation canceled."
    elif total_error_count > 0 or total_warning_count > 0:
        return "Batch translation finished. Completed with errors/warnings."
    else:
        return "Batch translation finished."
