
import re

# Patterns to protect during translation (Ren'Py tags, placeholders, formatting)
RENPY_TOKEN_PATTERNS = [
    r'\{i\}', r'\{/i\}',           # Italic tags
    r'\{b\}', r'\{/b\}',           # Bold tags  
    r'\{u\}', r'\{/u\}',           # Underline tags
    r'\{s\}', r'\{/s\}',           # Strikethrough tags
    r'\{color=[^}]+\}', r'\{/color\}',  # Color tags
    r'\{size=[^}]+\}', r'\{/size\}',    # Size tags
    r'\{font=[^}]+\}', r'\{/font\}',    # Font tags
    r'\{w(?:=[\d.]+)?\}',          # Wait tags {w} {w=0.5}
    r'\{p(?:=[\d.]+)?\}',          # Pause tags {p} {p=1.0}
    r'\{nw\}',                     # No-wait tag
    r'\{fast\}',                   # Fast display
    r'\{cps=\d+\}', r'\{/cps\}',   # Characters per second
    r'\[[^\]]+\]',                 # Variable placeholders [name] [player]
    r'%\([^)]+\)[sd]',             # Python format %(name)s %(count)d
    r'%[sd]',                      # Simple Python format %s %d
    r'\{\d+\}',                    # Positional format {0} {1}
]

# Compiled pattern for efficiency
_TOKEN_REGEX = None

def _get_token_regex():
    """Get compiled regex for all token patterns."""
    global _TOKEN_REGEX
    if _TOKEN_REGEX is None:
        combined = '|'.join(f'({p})' for p in RENPY_TOKEN_PATTERNS)
        _TOKEN_REGEX = re.compile(combined)
    return _TOKEN_REGEX


def mask_renpy_tokens(text: str):
    """
    Replace Ren'Py tokens with masked placeholders ⟦T0⟧, ⟦T1⟧, etc.
    
    Args:
        text: Original text with Ren'Py tokens
        
    Returns:
        Tuple of (masked_text, token_map) where token_map is {placeholder: original}
    """
    if not text:
        return text, {}
    
    token_map = {}
    counter = [0]  # Use list for closure mutability
    
    def replacer(match):
        token = match.group(0)
        placeholder = f"⟦T{counter[0]}⟧"
        token_map[placeholder] = token
        counter[0] += 1
        return placeholder
    
    regex = _get_token_regex()
    masked_text = regex.sub(replacer, text)
    
    return masked_text, token_map


def unmask_renpy_tokens(text: str, token_map: dict) -> str:
    """
    Restore masked placeholders ⟦T0⟧ back to original Ren'Py tokens.
    
    Args:
        text: Text with masked placeholders
        token_map: Map of {placeholder: original_token}
        
    Returns:
        Text with original tokens restored
    """
    if not text or not token_map:
        return text
    
    # Iterate through map and replace placeholders
    # We sort by length descending just in case, though T0, T1 etc shouldn't overlap
    for placeholder, original in token_map.items():
        text = text.replace(placeholder, original)
        
    return text
