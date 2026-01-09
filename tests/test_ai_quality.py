# -*- coding: utf-8 -*-
"""
Unit tests for AI Quality Pack features:
- Token masking/unmasking
- Validation
- Chunking
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from renforge_ai import (
    mask_renpy_tokens,
    unmask_renpy_tokens,
    validate_tokens_preserved,
    _split_into_chunks,
    BATCH_CHUNK_MAX_CHARS,
    BATCH_CHUNK_MAX_ITEMS
)


class TestTokenMasking:
    """Tests for mask/unmask roundtrip functionality."""
    
    def test_mask_unmask_simple_text(self):
        """Plain text without tokens should remain unchanged."""
        text = "Hello, this is a simple text."
        masked, token_map = mask_renpy_tokens(text)
        assert masked == text
        assert token_map == {}
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_italic_tags(self):
        """Italic tags should be masked and restored."""
        text = "This is {i}italic{/i} text."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "{i}" not in masked
        assert "{/i}" not in masked
        assert "⟦T0⟧" in masked
        assert "⟦T1⟧" in masked
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_bold_tags(self):
        """Bold tags should be masked and restored."""
        text = "This is {b}bold{/b} text."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "{b}" not in masked
        assert "{/b}" not in masked
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_color_tags(self):
        """Color tags with values should be masked and restored."""
        text = "This is {color=#FF0000}red{/color} text."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "{color=#FF0000}" not in masked
        assert "{/color}" not in masked
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_variable_placeholders(self):
        """Variable placeholders [name] should be masked and restored."""
        text = "Hello [player], you have [points] points."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "[player]" not in masked
        assert "[points]" not in masked
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_wait_pause_tags(self):
        """Wait and pause tags should be masked and restored."""
        text = "Hello...{w=0.5}there{p}friend."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "{w=0.5}" not in masked
        assert "{p}" not in masked
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_python_format(self):
        """Python format strings should be masked and restored."""
        text = "You have %(count)d items and %(name)s."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "%(count)d" not in masked
        assert "%(name)s" not in masked
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_positional_format(self):
        """Positional format {0} {1} should be masked and restored."""
        text = "Item {0} costs {1} gold."
        masked, token_map = mask_renpy_tokens(text)
        
        assert "{0}" not in masked
        assert "{1}" not in masked
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_unmask_mixed_tokens(self):
        """Multiple different token types in one string."""
        text = "{i}Hello{/i} [player], you earned {color=#00FF00}{b}100{/b}{/color} points{w=1.0}!"
        masked, token_map = mask_renpy_tokens(text)
        
        # All tokens should be masked
        for token in ["{i}", "{/i}", "[player]", "{color=#00FF00}", "{b}", "{/b}", "{/color}", "{w=1.0}"]:
            assert token not in masked
        
        # Should have multiple placeholders
        assert len(token_map) == 8
        
        unmasked = unmask_renpy_tokens(masked, token_map)
        assert unmasked == text
    
    def test_mask_empty_text(self):
        """Empty string handling."""
        text = ""
        masked, token_map = mask_renpy_tokens(text)
        assert masked == ""
        assert token_map == {}
    
    def test_mask_none_text(self):
        """None input handling."""
        masked, token_map = mask_renpy_tokens(None)
        assert masked is None
        assert token_map == {}


class TestTokenValidation:
    """Tests for token validation functionality."""
    
    def test_validation_all_tokens_present(self):
        """Validation passes when all tokens are present."""
        original = "Hello ⟦T0⟧ world ⟦T1⟧!"
        translated = "Merhaba ⟦T0⟧ dünya ⟦T1⟧!"
        token_map = {"⟦T0⟧": "[player]", "⟦T1⟧": "{w}"}
        
        missing = validate_tokens_preserved(original, translated, token_map)
        assert missing == []
    
    def test_validation_missing_one_token(self):
        """Validation fails when a token is missing."""
        original = "Hello ⟦T0⟧ world ⟦T1⟧!"
        translated = "Merhaba ⟦T0⟧ dünya!"  # Missing ⟦T1⟧
        token_map = {"⟦T0⟧": "[player]", "⟦T1⟧": "{w}"}
        
        missing = validate_tokens_preserved(original, translated, token_map)
        assert "⟦T1⟧" in missing
        assert len(missing) == 1
    
    def test_validation_missing_all_tokens(self):
        """Validation fails when all tokens are missing."""
        original = "Hello ⟦T0⟧ world ⟦T1⟧!"
        translated = "Merhaba dünya!"  # All tokens missing
        token_map = {"⟦T0⟧": "[player]", "⟦T1⟧": "{w}"}
        
        missing = validate_tokens_preserved(original, translated, token_map)
        assert "⟦T0⟧" in missing
        assert "⟦T1⟧" in missing
        assert len(missing) == 2
    
    def test_validation_empty_token_map(self):
        """Validation passes with empty token map."""
        original = "Hello world!"
        translated = "Merhaba dünya!"
        token_map = {}
        
        missing = validate_tokens_preserved(original, translated, token_map)
        assert missing == []


class TestChunking:
    """Tests for batch chunking functionality."""
    
    def test_single_chunk_small_batch(self):
        """Small batch fits in one chunk."""
        items = [
            {"i": 0, "original": "a", "masked": "Hello", "token_map": {}},
            {"i": 1, "original": "b", "masked": "World", "token_map": {}},
        ]
        
        chunks = _split_into_chunks(items)
        assert len(chunks) == 1
        assert chunks[0] == items
    
    def test_multiple_chunks_by_char_limit(self):
        """Items split when character limit exceeded."""
        # Create items that exceed char limit
        long_text = "x" * (BATCH_CHUNK_MAX_CHARS // 2 + 100)
        items = [
            {"i": 0, "original": "a", "masked": long_text, "token_map": {}},
            {"i": 1, "original": "b", "masked": long_text, "token_map": {}},
            {"i": 2, "original": "c", "masked": long_text, "token_map": {}},
        ]
        
        chunks = _split_into_chunks(items)
        assert len(chunks) >= 2  # Should be split
    
    def test_multiple_chunks_by_item_limit(self):
        """Items split when item count limit exceeded."""
        items = [
            {"i": i, "original": "a", "masked": "short", "token_map": {}}
            for i in range(BATCH_CHUNK_MAX_ITEMS + 10)
        ]
        
        chunks = _split_into_chunks(items)
        assert len(chunks) >= 2
        assert len(chunks[0]) == BATCH_CHUNK_MAX_ITEMS
    
    def test_chunk_order_preserved(self):
        """Original order is preserved across chunks."""
        items = [
            {"i": i, "original": f"text{i}", "masked": f"text{i}", "token_map": {}}
            for i in range(100)
        ]
        
        chunks = _split_into_chunks(items)
        
        # Flatten and check order
        flattened = [item for chunk in chunks for item in chunk]
        indices = [item["i"] for item in flattened]
        assert indices == list(range(100))
    
    def test_empty_items(self):
        """Empty list returns empty chunks."""
        chunks = _split_into_chunks([])
        assert chunks == []


# Additional integration-style tests (mock Gemini if needed)
class TestBatchTranslationIntegration:
    """Integration tests that may need mocking."""
    
    def test_roundtrip_with_all_token_types(self):
        """Full roundtrip test with various token types."""
        test_texts = [
            "Hello {i}world{/i}!",
            "Player [name] has {b}won{/b}!",
            "{color=#FF0000}Warning{/color}: {w=1.0}",
            "Score: %(count)d points",
            "Item {0} of {1}",
        ]
        
        for text in test_texts:
            masked, token_map = mask_renpy_tokens(text)
            unmasked = unmask_renpy_tokens(masked, token_map)
            assert unmasked == text, f"Roundtrip failed for: {text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
