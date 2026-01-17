# -*- coding: utf-8 -*-
"""
RenForge Row Data Model (v2)

Defines the core data structures for translation rows:
- RowStatus: Enum for translation states
- RowData: Dataclass for holding row information

v2 Changes:
- Added last_saved_text, last_engine_text for undo support
- Added approved_at timestamp
- Added validation fields (placeholders_ok, tags_ok)
- Added revert methods
- APPROVED + edit → MODIFIED transition
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class RowStatus(Enum):
    """Enumeration of possible row translation statuses."""
    UNTRANSLATED = "untranslated"   # editable_text is empty/whitespace
    TRANSLATED = "translated"       # Engine filled, user hasn't edited
    MODIFIED = "modified"           # User edited after engine OR after save
    APPROVED = "approved"           # User explicitly approved
    ERROR = "error"                 # Validation failed OR engine failed


@dataclass
class RowData:
    """
    Data structure representing a single translation row.
    
    This is the single source of truth for a row's state in the UI.
    Uses stable row_id for all actions (never row index).
    """
    # === Identity ===
    id: str                         # Stable UUID (from parser or generated)
    row_type: str                   # 'say', 'menu', 'string', etc.
    original_text: str              # Source text (immutable)
    tag: str = ""                   # Character tag (e.g., "mc")
    
    # === Text Versions for Undo ===
    editable_text: str = ""         # Current live translation
    last_saved_text: str = ""       # Snapshot at last file save
    last_engine_text: str = ""      # Last AI/Google output
    
    # === State ===
    status: RowStatus = RowStatus.UNTRANSLATED
    is_flagged: bool = False        # Independent attention toggle
    error_message: Optional[str] = None
    
    # === Metadata ===
    engine_used: Optional[str] = None      # "gemini-2.0-flash", "google"
    last_modified: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    notes: str = ""                 # User notes for this row
    
    # === Validation Cache ===
    placeholders_ok: bool = True
    # === Validation Cache ===
    placeholders_ok: bool = True
    tags_ok: bool = True
    
    # === QC / Problem Detection (Stage 6) ===
    qc_flag: bool = False
    qc_codes: list = field(default_factory=list)
    qc_summary: Optional[str] = None
    
    # =========================================================================
    # TEXT UPDATE METHODS
    # =========================================================================
    
    def update_text(self, new_text: str) -> None:
        """
        Update text and transition status.
        CRITICAL: Editing APPROVED row revokes approval → MODIFIED.
        """
        if self.editable_text == new_text:
            return
        
        self.editable_text = new_text
        self.last_modified = datetime.now()
        
        # Transition logic
        if not new_text.strip():
            self.status = RowStatus.UNTRANSLATED
            self.approved_at = None
        elif self.status == RowStatus.APPROVED:
            # CRITICAL: Editing approved row revokes approval
            self.status = RowStatus.MODIFIED
            self.approved_at = None
        elif self.status in (RowStatus.TRANSLATED, RowStatus.UNTRANSLATED):
            self.status = RowStatus.MODIFIED
        # If ERROR, stay ERROR until validation passes (handled elsewhere)
    
    def set_engine_translation(self, text: str, engine: str) -> None:
        """Set translation from AI/Google engine."""
        self.editable_text = text
        self.last_engine_text = text
        self.engine_used = engine
        self.last_modified = datetime.now()
        
        if text.strip():
            self.status = RowStatus.TRANSLATED
        else:
            self.status = RowStatus.UNTRANSLATED
    
    # =========================================================================
    # REVERT METHODS (Concrete Undo Semantics)
    # =========================================================================
    
    def revert_to_saved(self) -> None:
        """
        Revert to last saved state. Default Ctrl+Z action.
        """
        self.editable_text = self.last_saved_text
        self.error_message = None
        self._recompute_status()
    
    def revert_to_engine(self) -> None:
        """
        Revert to last engine output.
        """
        if self.last_engine_text:
            self.editable_text = self.last_engine_text
            self.status = RowStatus.TRANSLATED
            self.error_message = None
            self.approved_at = None
    
    def clear_translation(self) -> None:
        """
        Clear translation entirely.
        """
        self.editable_text = ""
        self.status = RowStatus.UNTRANSLATED
        self.error_message = None
        self.approved_at = None
    
    def _recompute_status(self) -> None:
        """Recompute status based on current editable_text."""
        if not self.editable_text.strip():
            self.status = RowStatus.UNTRANSLATED
            self.approved_at = None
        elif self.editable_text == self.last_engine_text and self.last_engine_text:
            self.status = RowStatus.TRANSLATED
        else:
            self.status = RowStatus.MODIFIED
    
    # =========================================================================
    # APPROVAL METHODS
    # =========================================================================
    
    def set_approved(self) -> None:
        """Set status to APPROVED if valid."""
        if self.editable_text.strip() and self.status != RowStatus.ERROR:
            self.status = RowStatus.APPROVED
            self.approved_at = datetime.now()
    
    def revoke_approval(self) -> None:
        """Revoke approval, revert to MODIFIED or appropriate state."""
        if self.status == RowStatus.APPROVED:
            self.approved_at = None
            if self.editable_text.strip():
                self.status = RowStatus.MODIFIED
            else:
                self.status = RowStatus.UNTRANSLATED
    
    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    
    def set_error(self, message: str) -> None:
        """Set row to ERROR state with message. Keeps editable_text."""
        self.status = RowStatus.ERROR
        self.error_message = message
    
    def clear_error(self) -> None:
        """Clear error and recompute status."""
        self.error_message = None
        self._recompute_status()
    
    # =========================================================================
    # SAVE SNAPSHOT
    # =========================================================================
    
    def snapshot_for_save(self) -> None:
        """Called when file is saved. Updates last_saved_text."""
        self.last_saved_text = self.editable_text
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    @property
    def is_dirty(self) -> bool:
        """Check if row has unsaved changes."""
        return self.editable_text != self.last_saved_text
    
    @property
    def is_problem(self) -> bool:
        """Check if row is a 'problem' (for Review filter)."""
        return (
            self.status in (RowStatus.UNTRANSLATED, RowStatus.ERROR, RowStatus.MODIFIED)
            or self.is_flagged
        )
    
    def get_problem_reason(self) -> str:
        """Return reason string for Review 'Reason' column."""
        if self.status == RowStatus.UNTRANSLATED:
            return "Empty"
        if self.status == RowStatus.ERROR:
            if self.error_message:
                return self.error_message[:50] + ("..." if len(self.error_message) > 50 else "")
            return "Validation error"
        if self.is_flagged:
            return "Flagged"
        if self.status == RowStatus.MODIFIED:
            return "Needs review"
        return ""
