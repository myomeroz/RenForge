
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from models.parsed_file import ParsedItem
import locales
from renforge_logger import get_logger

logger = get_logger("core.qa_engine")

class QASeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class QAIssue:
    rule_id: str
    severity: QASeverity
    line_index: int # 1-based display index
    raw_index: int # data index
    message: str
    can_fix: bool = False
    
class QARule:
    id = "base"
    
    def check(self, item: ParsedItem, index: int) -> Optional[QAIssue]:
        raise NotImplementedError
        
    def fix(self, item: ParsedItem) -> bool:
        return False

# =========================================================================
# Rules
# =========================================================================

class TokenRule(QARule):
    id = "token_mismatch"
    
    def check(self, item: ParsedItem, index: int) -> Optional[QAIssue]:
        orig = item.current_text if item.current_text else (item.original_text or "")
        # Actually, we compare Original vs Translation.
        # But item.current_text IS the translation in Translate Mode.
        # Original is item.original_text.
        
        original = item.original_text or ""
        translation = item.current_text or ""
        
        if not translation: return None # Empty checked elsewhere
        
        # Regex for Ren'Py tokens [foo]
        tokens_orig = re.findall(r'\[.*?\]', original)
        tokens_trans = re.findall(r'\[.*?\]', translation)
        
        # Check set equality? Or count?
        # Strict: Count must match exactly?
        # User requirement: "Count and exact token text must match"
        
        # We check if every token in orig exists in trans.
        # And counts match.
        from collections import Counter
        c_orig = Counter(tokens_orig)
        c_trans = Counter(tokens_trans)
        
        missing = []
        for t, count in c_orig.items():
            if c_trans[t] < count:
                missing.append(t)
                
        if missing:
            return QAIssue(self.id, QASeverity.ERROR, 
                           (item.line_index or 0) + 1, index, 
                           f"{locales.tr('qa_rule_token_mismatch')}: {', '.join(missing)}",
                           can_fix=True)
                           
        # Check for malformed tokens? e.g. [player
        if re.search(r'\[[^\]]*$', translation):
             return QAIssue(self.id, QASeverity.WARNING, 
                           (item.line_index or 0) + 1, index, 
                           f"{locales.tr('qa_rule_token_mismatch')} (Unclosed bracket)")
                           
        return None

    def fix(self, item: ParsedItem) -> bool:
        # Safe fix: Append missing tokens?
        # Or try to insert?
        # For now, appendage is safest "Repair".
        original = item.original_text or ""
        translation = item.current_text or ""
        
        tokens_orig = re.findall(r'\[.*?\]', original)
        tokens_trans = re.findall(r'\[.*?\]', translation)
        
        from collections import Counter
        c_orig = Counter(tokens_orig)
        c_trans = Counter(tokens_trans)
        
        to_add = []
        for t, count in c_orig.items():
            diff = count - c_trans[t]
            if diff > 0:
                to_add.extend([t] * diff)
                
        if to_add:
            item.current_text = translation + " " + " ".join(to_add)
            item.is_modified_session = True
            return True
        return False

class MarkupRule(QARule):
    id = "markup_mismatch"
    
    def check(self, item: ParsedItem, index: int) -> Optional[QAIssue]:
        translation = item.current_text or ""
        if not translation: return None
        
        # Check {b} {/b}, {i} {/i}
        # Simple stack-based check for {} tags?
        # Ren'Py tags are {tag} or {tag=val}. Closing is {/tag}.
        
        tags = re.findall(r'\{(/?)(\w+)(?:=.*?)?\}', translation)
        # tags is list of (is_closing, tag_name)
        
        stack = []
        for is_closing, tag_name in tags:
            if tag_name in ['w', 'nw', 'fast', 'p']: continue # Self-closing
            
            if not is_closing:
                stack.append(tag_name)
            else:
                if not stack:
                    return QAIssue(self.id, QASeverity.WARNING,
                                   (item.line_index or 0) + 1, index,
                                   f"{locales.tr('qa_rule_markup_mismatch')}: Unexpected {{/{tag_name}}}")
                last = stack.pop()
                if last != tag_name:
                     return QAIssue(self.id, QASeverity.WARNING,
                                   (item.line_index or 0) + 1, index,
                                   f"{locales.tr('qa_rule_markup_mismatch')}: Expected {{/{last}}}, found {{/{tag_name}}}")
                                   
        if stack:
             return QAIssue(self.id, QASeverity.WARNING,
                            (item.line_index or 0) + 1, index,
                            f"{locales.tr('qa_rule_markup_mismatch')}: Unclosed {{/{stack[-1]}}}")
                            
        return None

class EmptyRule(QARule):
    id = "empty"
    def check(self, item: ParsedItem, index: int) -> Optional[QAIssue]:
        if item.original_text and not item.current_text:
             return QAIssue(self.id, QASeverity.ERROR, (item.line_index or 0)+1, index, locales.tr('qa_rule_empty'))
        return None

class IdenticalRule(QARule):
    id = "identical"
    def check(self, item: ParsedItem, index: int) -> Optional[QAIssue]:
        if item.original_text and item.current_text and item.original_text == item.current_text:
             # Ignore if original is very short (numbers, names)
             if len(item.original_text) > 3:
                 return QAIssue(self.id, QASeverity.INFO, (item.line_index or 0)+1, index, locales.tr('qa_rule_identical'))
        return None

class WhitespaceRule(QARule):
    id = "whitespace"
    def check(self, item: ParsedItem, index: int) -> Optional[QAIssue]:
        t = item.current_text
        if not t: return None
        
        if t.startswith(" ") or t.endswith(" ") or "  " in t:
             return QAIssue(self.id, QASeverity.WARNING, (item.line_index or 0)+1, index, 
                            locales.tr('qa_rule_whitespace'), can_fix=True)
        return None
        
    def fix(self, item: ParsedItem) -> bool:
        t = item.current_text or ""
        new_t = re.sub(r'\s+', ' ', t).strip()
        if new_t != t:
            item.current_text = new_t
            item.is_modified_session = True
            return True
        return False

# =========================================================================
# Engine
# =========================================================================

class QAEngine:
    def __init__(self):
        self.rules: List[QARule] = [
            TokenRule(),
            MarkupRule(),
            EmptyRule(),
            IdenticalRule(),
            WhitespaceRule()
        ]
        
    def scan(self, items: List[ParsedItem], callback=None) -> List[QAIssue]:
        issues = []
        total = len(items)
        if total == 0: return []
        
        for i, item in enumerate(items):
            if i % 500 == 0 and callback:
                if not callback(i, total): break # Cancelled
                
            for rule in self.rules:
                issue = rule.check(item, i)
                if issue:
                    issues.append(issue)
                    
        return issues
        
    def fix_issue(self, item: ParsedItem, issue: QAIssue) -> bool:
        for rule in self.rules:
            if rule.id == issue.rule_id:
                return rule.fix(item)
        return False
