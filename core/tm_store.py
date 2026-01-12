
import sqlite3
import os
import re
import html
from dataclasses import dataclass
from typing import List, Optional
from renforge_logger import get_logger

logger = get_logger("core.tm_store")

@dataclass
class TMEntry:
    source_text: str
    target_text: str
    score: float = 0.0
    provenance: str = "manual"
    reviewed: bool = False
    
    @property
    def is_high_confidence(self):
        return self.reviewed or self.provenance == "review_accepted"

class TMManager:
    """
    Manages Translation Memory using SQLite for persistence
    and an in-memory normalized index for fast retrieval.
    """
    def __init__(self, project_path: Optional[str] = None):
        self.db_path = None
        self.conn = None
        self.project_path = project_path
        self._memory_cache = {} # source -> [TMEntry]
        
        # Always init DB since it's global now
        self.init_db(project_path)
            
    def init_db(self, project_path: Optional[str] = None):
        if project_path:
            self.project_path = project_path
        
        # User requested TM in "DB" folder alongside settings.json
        # This makes the TM global for the application instance.
        import renforge_config
        # Ensure we work with string path for sqlite compatibility
        self.db_path = str(renforge_config.DB_DIR / "tm.db") if hasattr(renforge_config.DB_DIR, 'joinpath') else os.path.join(renforge_config.DB_DIR, "tm.db")
        
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._create_tables()
            self._load_cache() # Warm up cache for speed
        except Exception as e:
            logger.error(f"Failed to init TM DB: {e}")
            self.conn = None
            
    def _create_tables(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS tm_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                target_text TEXT NOT NULL,
                normalized_hash TEXT,
                provenance TEXT,
                reviewed INTEGER DEFAULT 0,
                timestamp REAL,
                UNIQUE(source_text, target_text)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_source ON tm_entries(source_text)")
        self.conn.commit()
        
    def _normalize(self, text: str) -> str:
        # Lowercase, strip punctuation and whitespace
        return re.sub(r'[\W_]+', '', text.lower())

    def _load_cache(self):
        """Loads entries into memory map for fast normalization lookup."""
        if not self.conn: return
        c = self.conn.cursor()
        c.execute("SELECT source_text, target_text, provenance, reviewed FROM tm_entries")
        rows = c.fetchall()
        
        self._memory_cache = {}
        count = 0
        for r in rows:
            src, tgt, prov, rev = r
            entry = TMEntry(src, tgt, 100.0, prov, bool(rev))
            
            # Exact key
            if src not in self._memory_cache: self._memory_cache[src] = []
            self._memory_cache[src].append(entry)
            
            # Normalized key (store as separate map later if needed, but for now exact first)
            count += 1
        logger.debug(f"TM Cache loaded {count} entries.")

    def add_entry(self, source: str, target: str, provenance: str = "manual", reviewed: bool = False):
        if not source or not target or not self.conn: return
        if source == target: return # Don't store identicals? Or maybe yes if deliberate.
        
        import time
        ts = time.time()
        c = self.conn.cursor()
        try:
            c.execute("""
                INSERT OR REPLACE INTO tm_entries (source_text, target_text, normalized_hash, provenance, reviewed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (source, target, self._normalize(source), provenance, 1 if reviewed else 0, ts))
            self.conn.commit()
            
            # Update cache
            entry = TMEntry(source, target, 100.0, provenance, reviewed)
            if source not in self._memory_cache: self._memory_cache[source] = []
            # Check duplicates
            exists = False
            for e in self._memory_cache[source]:
                if e.target_text == target:
                    e.provenance = provenance
                    e.reviewed = reviewed
                    exists = True
                    break
            if not exists:
                self._memory_cache[source].append(entry)
                
        except Exception as e:
            logger.error(f"Error adding TM entry: {e}")

    def import_from_db(self, source_db_path: str) -> int:
        """
        Import entries from another TM database.
        Merges new entries, ignores duplicates.
        Returns count of added entries.
        """
        if not self.conn or not os.path.exists(source_db_path):
            return 0
            
        added_count = 0
        try:
            # Attach source DB
            c = self.conn.cursor()
            # Use specific syntax for attaching
            c.execute(f"ATTACH DATABASE ? AS src_db", (source_db_path,))
            
            # Insert or Ignore
            c.execute("""
                INSERT OR IGNORE INTO tm_entries (source_text, target_text, normalized_hash, provenance, reviewed, timestamp)
                SELECT source_text, target_text, normalized_hash, provenance, reviewed, timestamp
                FROM src_db.tm_entries
            """)
            added_count = c.rowcount
            
            self.conn.commit()
            
            # Detach
            c.execute("DETACH DATABASE src_db")
            
            # Refresh cache if items added
            if added_count > 0:
                self._load_cache()
                logger.info(f"Imported {added_count} entries from {source_db_path}")
                
        except Exception as e:
            logger.error(f"Failed to import TM DB: {e}")
            if self.conn:
                self.conn.rollback()
                
        return added_count
        
    def lookup(self, text: str, limit: int = 5) -> List[TMEntry]:
        if not text: return []
        results = []
        
        # 1. Exact Match
        if text in self._memory_cache:
            for e in self._memory_cache[text]:
                e.score = 100.0
                results.append(e)
                
        # 2. Normalized Match (if requested or strict failed)
        # Scan cache? O(N). Expensive if 100k.
        # But iterating 100k strings in Python is ~50ms. Acceptable.
        
        norm_input = self._normalize(text)
        if not norm_input: return results
        
        # Simple fuzzy: normalized equality
        # Since we use cache dict keys, we can iterate keys.
        
        # Optimization: Only fuzzy if exact not found? Or always to find variants?
        # User wants "suggestions". Even if exact mismatch, maybe useful.
        
        # To avoid lag, we only run scan if limit not reached
        if len(results) >= limit: return results[:limit]
        
        # Heuristic: Only scan if text len > some threshold
        candidates = []
        
        for src_key in self._memory_cache.keys():
            if src_key == text: continue # Already handled
            
            # Check normalized
            norm_key = self._normalize(src_key)
            if not norm_key: continue
            
            score = 0
            if norm_key == norm_input:
                score = 90.0
            elif norm_input in norm_key or norm_key in norm_input:
                # Substring match
                score = 70.0
            
            if score > 0:
                for e in self._memory_cache[src_key]:
                    # Clone entry with new score
                    cand = TMEntry(e.source_text, e.target_text, score, e.provenance, e.reviewed)
                    candidates.append(cand)
                    
        # Sort by score desc, then reviewed desc
        candidates.sort(key=lambda x: (x.score, x.reviewed), reverse=True)
        
        # Merge
        seen_targets = set(r.target_text for r in results)
        for c in candidates:
            if c.target_text not in seen_targets:
                results.append(c)
                seen_targets.add(c.target_text)
                if len(results) >= limit: break
                
        return results

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

# Global instance
_instance = None
def get_tm_manager() -> TMManager:
    global _instance
    if _instance is None:
        _instance = TMManager()
    return _instance

def init_tm_manager(project_path: str):
    global _instance
    _instance = TMManager(project_path)
    return _instance
