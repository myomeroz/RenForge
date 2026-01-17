# -*- coding: utf-8 -*-
"""
RenForge Quality Check (QC) Engine

This module provides logic to detect quality issues in translations,
such as missing placeholders, empty content, or length anomalies.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from renforge_logger import get_logger

logger = get_logger("core.qc_engine")

@dataclass
class QCIssue:
    code: str
    message: str
    severity: str = "WARN"  # "WARN" or "ERROR"

# --- REGEX PATTERNS ---

# Ren'Py Interpolation variables (Missing = ERROR)
# [variable], {variable}, {0}, %(variable)s, %s, %d
VARIABLE_PATTERNS = [
    r'\{[^}ib/]+\}',        # {variable} or {0} (excluding simple {i}, {b}, {/i})
    r'\[[^\]]+\]',          # [variable]
    r'%[\(\)a-zA-Z0-9]+',   # %s, %d, %(name)s
]

# Ren'Py Formatting Tags (Missing = WARN)
# {i}, {/i}, {b}, {/b}, {a=...}, {/a}, etc.
TAG_PATTERNS = [
    r'\{[ib]\}',            # {i}, {b}
    r'\{/[ib]\}',           # {/i}, {/b}
    r'\{a=[^}]+\}',         # {a=link}
    r'\{/a\}',              # {/a}
    # Add more as needed (color, font, etc.): r'\{color=[^}]+\}', r'\{/color\}'
]

def check_quality(source_text: str, target_text: str) -> List[QCIssue]:
    """
    Run all QC checks on the translation pair.
    
    Args:
        source_text: Original text
        target_text: Translated text
        
    Returns:
        List of QCIssue objects found.
    """
    issues = []
    
    if source_text is None: source_text = ""
    if target_text is None: target_text = ""
    
    # 1. Empty Translation (ERROR)
    if not target_text.strip() and source_text.strip():
        issues.append(QCIssue(
            code="EMPTY_TRANSLATION", 
            message="Çeviri metni boş.",
            severity="ERROR"
        ))
        return issues # Stop other checks if empty
        
    # 2. Unchanged (normalized) (WARN)
    # Logic: " ".join(text.strip().casefold().split())
    if len(source_text) > 3: # Ignore very short texts
        norm_source = " ".join(source_text.strip().casefold().split())
        norm_target = " ".join(target_text.strip().casefold().split())
        
        # Also ensure they are not structurally identical if punctuation differs
        if norm_source == norm_target:
             # Further check: if source was just a symbol or number, maybe OK.
             # But generally warn.
             if not source_text.replace('.','').isdigit():
                issues.append(QCIssue(
                    code="UNCHANGED", 
                    message="Çeviri kaynak metinle aynı.",
                    severity="WARN"
                ))

    # 3. Variable/Placeholder Mismatch (ERROR)
    source_vars = []
    for pattern in VARIABLE_PATTERNS:
        source_vars.extend(re.findall(pattern, source_text))
    
    missing_vars = []
    for token in source_vars:
        if token not in target_text:
            missing_vars.append(token)
            
    if missing_vars:
        unique_missing = sorted(list(set(missing_vars)))
        issues.append(QCIssue(
            code="PLACEHOLDER_MISSING",
            message=f"Eksik değişkenler: {', '.join(unique_missing)}",
            severity="ERROR"
        ))

    # 4. Tag Mismatch (WARN)
    source_tags = []
    for pattern in TAG_PATTERNS:
        source_tags.extend(re.findall(pattern, source_text))
        
    missing_tags = []
    for token in source_tags:
        if token not in target_text:
            missing_tags.append(token)
            
    if missing_tags:
        unique_missing_tags = sorted(list(set(missing_tags)))
        issues.append(QCIssue(
            code="TAG_MISMATCH",
            message=f"Eksik etiketler: {', '.join(unique_missing_tags)}",
            severity="WARN"
        ))

    # 5. Length Anomaly (WARN)
    if len(source_text) > 0:
        ratio = len(target_text) / len(source_text)
        if len(source_text) > 10: # Only check significant length
            if ratio < 0.35:
                issues.append(QCIssue(
                    code="LENGTH_SHORT",
                    message=f"Çeviri çok kısa ({int(ratio*100)}% oran)",
                    severity="WARN"
                ))
            elif ratio > 2.5:
                issues.append(QCIssue(
                    code="LENGTH_LONG",
                    message=f"Çeviri çok uzun ({int(ratio*100)}% oran)",
                    severity="WARN"
                ))

    # 6. Escape/Linebreak Mismatch (WARN)
    # Check both literal newlines and escaped newlines if likely to appear
    # Ren'Py mostly handles \n automatically if in "" strings, but logic:
    # Count literal \n
    s_nl = source_text.count('\n')
    t_nl = target_text.count('\n')
    
    # Also check literal \n sequence if raw text
    s_esc = source_text.count('\\n')
    t_esc = target_text.count('\\n')
    
    total_source = s_nl + s_esc
    total_target = t_nl + t_esc
    
    if total_source > 0 and total_target == 0:
         issues.append(QCIssue(
            code="ESCAPE_MISMATCH",
            message="Satır sonu karakterleri kaybolmuş.",
            severity="WARN"
        ))
    elif abs(total_source - total_target) >= 2:
         # Only warn if difference is significant (>=2 lines off)
         issues.append(QCIssue(
            code="ESCAPE_MISMATCH",
            message=f"Satır sonu sayısı uyumsuz (Kaynak: {total_source}, Hedef: {total_target})",
            severity="WARN"
        ))

    return issues
