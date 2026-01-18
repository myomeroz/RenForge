# -*- coding: utf-8 -*-
"""
RenForge Run Analytics (Stage 12)

Provides logic for:
1. Run Comparison (Deltas, Top Changes)
2. Trend Analysis (Last N runs stats)
3. Insight Generation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import Counter
from core.run_history_store import RunRecord

@dataclass
class RunDelta:
    """Differences between two runs (Selected - Baseline)."""
    error_delta: int = 0
    qc_delta: int = 0
    duration_delta_ms: int = 0
    success_delta: int = 0
    
    # Top changed categories (e.g. [('TIMEOUT', +2), ('NETWORK', -1)])
    top_error_increases: List[Tuple[str, int]] = field(default_factory=list)
    top_error_decreases: List[Tuple[str, int]] = field(default_factory=list)
    
    top_qc_increases: List[Tuple[str, int]] = field(default_factory=list)
    top_qc_decreases: List[Tuple[str, int]] = field(default_factory=list)
    
    # Flags
    is_legacy: bool = False  # If either run lacks detailed breakdowns

@dataclass
class TrendStats:
    """Aggregated stats for N runs."""
    count: int = 0
    avg_errors: float = 0.0
    avg_duration_ms: float = 0.0
    error_free_rate: float = 0.0  # Percentage 0-100
    
    # Problematic models: [(model_name, total_errors)]
    problematic_models: List[Tuple[str, int]] = field(default_factory=list)
    
    # Series for charting (chronological)
    error_series: List[int] = field(default_factory=list)
    duration_series: List[int] = field(default_factory=list)

def compute_run_deltas(current: RunRecord, baseline: RunRecord) -> RunDelta:
    """Compute deltas between current and baseline run."""
    delta = RunDelta()
    
    # Basic counts
    delta.error_delta = current.errors_count - baseline.errors_count
    delta.qc_delta = current.qc_count_total - baseline.qc_count_total
    delta.duration_delta_ms = current.duration_ms - baseline.duration_ms
    delta.success_delta = current.success_updated - baseline.success_updated
    
    # Check for breakdown availability
    cur_cats = current.error_category_counts
    base_cats = baseline.error_category_counts
    cur_qc = current.qc_code_counts
    base_qc = baseline.qc_code_counts
    
    if not cur_cats and current.errors_count > 0:
        delta.is_legacy = True
    if not base_cats and baseline.errors_count > 0:
        delta.is_legacy = True
        
    if delta.is_legacy:
        return delta
        
    # Compute category deltas
    all_cats = set(cur_cats.keys()) | set(base_cats.keys())
    cat_changes = []
    for cat in all_cats:
        c = cur_cats.get(cat, 0)
        b = base_cats.get(cat, 0)
        diff = c - b
        if diff != 0:
            cat_changes.append((cat, diff))
    
    # Sort by magnitude
    # Increases: biggest positive first
    delta.top_error_increases = sorted([x for x in cat_changes if x[1] > 0], key=lambda x: x[1], reverse=True)[:3]
    # Decreases: biggest negative first (most improved)
    delta.top_error_decreases = sorted([x for x in cat_changes if x[1] < 0], key=lambda x: x[1])[:3]
    
    # Compute QC deltas
    all_qc = set(cur_qc.keys()) | set(base_qc.keys())
    qc_changes = []
    for code in all_qc:
        c = cur_qc.get(code, 0)
        b = base_qc.get(code, 0)
        diff = c - b
        if diff != 0:
            qc_changes.append((code, diff))
            
    delta.top_qc_increases = sorted([x for x in qc_changes if x[1] > 0], key=lambda x: x[1], reverse=True)[:3]
    delta.top_qc_decreases = sorted([x for x in qc_changes if x[1] < 0], key=lambda x: x[1])[:3]
    
    return delta

def compute_trends(runs: List[RunRecord], last_n: int = 10) -> TrendStats:
    """Compute trends for the last N runs."""
    stats = TrendStats()
    if not runs:
        return stats
        
    # Take last N (assumes runs are sorted chronological or we sort them)
    # Usually history store returns appended list, so last = newest.
    # We want valid runs for analysis.
    
    # Filter valid runs? Or take all? Take all.
    target_runs = runs[-last_n:]
    stats.count = len(target_runs)
    
    total_errors = 0
    total_duration = 0
    error_free_count = 0
    model_errors = Counter()
    
    for r in target_runs:
        total_errors += r.errors_count
        total_duration += r.duration_ms
        if r.errors_count == 0:
            error_free_count += 1
            
        stats.error_series.append(r.errors_count)
        stats.duration_series.append(r.duration_ms)
        
        # Track problematic models
        if r.model and r.errors_count > 0:
            model_errors[r.model] += r.errors_count
            
    if stats.count > 0:
        stats.avg_errors = total_errors / stats.count
        stats.avg_duration_ms = total_duration / stats.count
        stats.error_free_rate = (error_free_count / stats.count) * 100.0
        
    stats.problematic_models = model_errors.most_common(3)
    
    return stats
