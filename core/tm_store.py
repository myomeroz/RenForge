# -*- coding: utf-8 -*-
"""
RenForge Translation Memory Store (Stage 16.1)

Hash-based exact-match Translation Memory with SQLite persistence.
Thread-safe for worker usage.
"""

import hashlib
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from renforge_logger import get_logger

logger = get_logger("core.tm_store")


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for TM matching.
    
    - Strip leading/trailing whitespace
    - Collapse multiple spaces to single space
    - Lowercase for case-insensitive matching
    - Preserve Ren'Py placeholders like [name], {i}, etc.
    """
    if not text:
        return ""
    
    # Strip and collapse whitespace
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    
    # Lowercase for matching (but original case is stored separately)
    text = text.lower()
    
    return text


def compute_hash(source_text: str, source_lang: str, target_lang: str) -> str:
    """
    Compute hash for exact-match lookup.
    
    Combines normalized source text with language pair for unique key.
    """
    normalized = normalize_text(source_text)
    combined = f"{source_lang}:{target_lang}:{normalized}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32]


# =============================================================================
# DATA CLASS
# =============================================================================

@dataclass
class TMEntry:
    """A Translation Memory entry."""
    id: int
    source_hash: str
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    created_at: str
    updated_at: str
    use_count: int = 0
    origin: str = ""  # e.g., "gemini", "google", "manual"


# =============================================================================
# TM STORE
# =============================================================================

class TMStore:
    """
    Translation Memory store with SQLite backend.
    
    Thread-safe singleton with connection-per-thread.
    """
    
    _instance: Optional['TMStore'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._db_path = self._get_db_path()
        self._local = threading.local()
        
        # Initialize schema on main thread
        self._ensure_schema()
        
        self._initialized = True
        logger.info(f"[TM] TMStore initialized: {self._db_path}")
    
    @classmethod
    def instance(cls) -> 'TMStore':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = TMStore()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
    
    def _get_db_path(self) -> Path:
        """TM veritabanı yolunu döndür (uygulama içindeki DB klasörü)."""
        from renforge_config import DB_DIR
        return DB_DIR / "translation_memory.db"
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _ensure_schema(self):
        """Create TM table if not exists."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tm_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_hash TEXT NOT NULL UNIQUE,
                source_text TEXT NOT NULL,
                target_text TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                use_count INTEGER DEFAULT 0,
                origin TEXT DEFAULT ''
            )
        """)
        
        # Index for fast hash lookup
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_hash ON tm_entries(source_hash)
        """)
        
        conn.commit()
        logger.debug("[TM] Schema ensured")
    
    # =========================================================================
    # LOOKUP
    # =========================================================================
    
    def lookup(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        touch: bool = True
    ) -> Optional[TMEntry]:
        """
        Look up exact match in TM.
        
        Args:
            source_text: Original text to translate
            source_lang: Source language code
            target_lang: Target language code
            touch: If True, increment use_count and update updated_at (default: True)
                   Set to False for UI listing/search operations.
        
        Returns:
            TMEntry if exact match found, None otherwise
        """
        if not source_text or not source_text.strip():
            return None
        
        source_hash = compute_hash(source_text, source_lang, target_lang)
        
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM tm_entries WHERE source_hash = ?",
            (source_hash,)
        )
        row = cursor.fetchone()
        
        if row:
            logger.debug(f"[TM] Hit: {source_hash[:8]}...")
            
            # Stage 20: touch=True ise use_count ve updated_at güncelle
            if touch:
                self._touch_entry(row['id'], conn)
            
            return TMEntry(
                id=row['id'],
                source_hash=row['source_hash'],
                source_text=row['source_text'],
                target_text=row['target_text'],
                source_lang=row['source_lang'],
                target_lang=row['target_lang'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                use_count=row['use_count'] + (1 if touch else 0),  # Güncel değeri döndür
                origin=row['origin'] or ""
            )
        
        return None
    
    def _touch_entry(self, entry_id: int, conn=None):
        """
        TM entry'nin use_count ve updated_at alanlarını güncelle.
        Thread-safe.
        """
        if conn is None:
            conn = self._get_connection()
        
        now = datetime.now().isoformat()
        conn.execute("""
            UPDATE tm_entries 
            SET use_count = use_count + 1, updated_at = ?
            WHERE id = ?
        """, (now, entry_id))
        conn.commit()
    
    def lookup_batch(
        self,
        source_texts: List[str],
        source_lang: str,
        target_lang: str,
        touch: bool = True
    ) -> Dict[int, TMEntry]:
        """
        Batch lookup for multiple source texts.
        
        Args:
            touch: If True, increment use_count for found entries (default: True)
        
        Returns:
            Dict mapping index -> TMEntry for found matches
        """
        results = {}
        
        for i, text in enumerate(source_texts):
            entry = self.lookup(text, source_lang, target_lang, touch=touch)
            if entry:
                results[i] = entry
        
        return results
    
    # =========================================================================
    # INSERT / UPDATE
    # =========================================================================
    
    def insert(
        self,
        source_text: str,
        target_text: str,
        source_lang: str,
        target_lang: str,
        origin: str = ""
    ) -> bool:
        """
        Insert or update a TM entry.
        
        Args:
            source_text: Original text
            target_text: Translated text
            source_lang: Source language code
            target_lang: Target language code
            origin: Origin of translation (e.g., "gemini", "google")
        
        Returns:
            True if successful
        """
        if not source_text or not target_text:
            return False
        
        source_hash = compute_hash(source_text, source_lang, target_lang)
        now = datetime.now().isoformat()
        
        conn = self._get_connection()
        
        try:
            # Try insert, update on conflict
            conn.execute("""
                INSERT INTO tm_entries 
                    (source_hash, source_text, target_text, source_lang, target_lang, 
                     created_at, updated_at, use_count, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(source_hash) DO UPDATE SET
                    target_text = excluded.target_text,
                    updated_at = excluded.updated_at,
                    use_count = use_count + 1,
                    origin = excluded.origin
            """, (source_hash, source_text.strip(), target_text.strip(), 
                  source_lang, target_lang, now, now, origin))
            
            conn.commit()
            logger.debug(f"[TM] Inserted/updated: {source_hash[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"[TM] Insert failed: {e}")
            return False
    
    def increment_use_count(self, source_hash: str):
        """Increment use count for a TM entry."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE tm_entries SET use_count = use_count + 1 WHERE source_hash = ?",
            (source_hash,)
        )
        conn.commit()
    
    # =========================================================================
    # UPDATE / DELETE (Stage 20)
    # =========================================================================
    
    def update(
        self,
        entry_id: int,
        target_text: str = None,
        origin: str = None
    ) -> bool:
        """
        TM entry'sini güncelle.
        
        Args:
            entry_id: Güncellenecek entry ID
            target_text: Yeni çeviri metni (None ise değişmez)
            origin: Yeni kaynak (None ise değişmez)
        
        Returns:
            True if successful
        """
        if not entry_id:
            return False
        
        conn = self._get_connection()
        now = datetime.now().isoformat()
        
        updates = []
        params = []
        
        if target_text is not None:
            updates.append("target_text = ?")
            params.append(target_text.strip())
        
        if origin is not None:
            updates.append("origin = ?")
            params.append(origin)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(now)
        params.append(entry_id)
        
        try:
            query = f"UPDATE tm_entries SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, tuple(params))
            conn.commit()
            logger.debug(f"[TM] Updated entry {entry_id}")
            return True
        except Exception as e:
            logger.error(f"[TM] Update failed: {e}")
            return False
    
    def delete(self, entry_id: int) -> bool:
        """
        TM entry'sini sil.
        
        Args:
            entry_id: Silinecek entry ID
        
        Returns:
            True if successful
        """
        if not entry_id:
            return False
        
        conn = self._get_connection()
        
        try:
            cursor = conn.execute("DELETE FROM tm_entries WHERE id = ?", (entry_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.debug(f"[TM] Deleted entry {entry_id}")
            return deleted
        except Exception as e:
            logger.error(f"[TM] Delete failed: {e}")
            return False
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get TM statistics."""
        conn = self._get_connection()
        
        cursor = conn.execute("SELECT COUNT(*) as total FROM tm_entries")
        total = cursor.fetchone()['total']
        
        cursor = conn.execute("SELECT SUM(use_count) as uses FROM tm_entries")
        uses = cursor.fetchone()['uses'] or 0
        
        return {
            'total_entries': total,
            'total_uses': uses
        }
    
    def clear(self):
        """Clear all TM entries (for testing)."""
        conn = self._get_connection()
        conn.execute("DELETE FROM tm_entries")
        conn.commit()
        logger.info("[TM] Database cleared")
