#!/usr/bin/env python3
"""
db.py – Datenbank-Kompatibilitätsschicht (PostgreSQL + SQLite-Fallback)

Versucht PostgreSQL via DATABASE_URL, fällt auf SQLite zurück.
Übersetzt automatisch:
  - ?  →  %s
  - INSERT OR IGNORE INTO  →  INSERT INTO ... ON CONFLICT DO NOTHING
  - INTEGER PRIMARY KEY AUTOINCREMENT  →  BIGSERIAL PRIMARY KEY
  - DEFAULT (datetime('now','localtime'))  →  DEFAULT CURRENT_TIMESTAMP
"""
import os
import re
import sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_PG = bool(DATABASE_URL)

# ─── SQL-Übersetzung ──────────────────────────────────────────────────────────

_RE_INSERT_IGNORE = re.compile(
    r'\bINSERT\s+OR\s+IGNORE\s+INTO\b', re.IGNORECASE
)
_RE_AUTOINCREMENT = re.compile(
    r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b', re.IGNORECASE
)
_RE_DATETIME_DEFAULT = re.compile(
    r"DEFAULT\s+\(?datetime\('now'(?:,\s*'[^']*')?\)\)?", re.IGNORECASE
)


_PLACEHOLDER = '\x00PG_PARAM\x00'

def _adapt_pg(sql):
    """Übersetzt SQLite-SQL-Dialekt zu PostgreSQL."""
    # 1. ? temporär durch Platzhalter ersetzen
    sql = sql.replace('?', _PLACEHOLDER)
    # 2. Alle % im SQL escapen (LIKE-Muster etc.) → %%
    sql = sql.replace('%', '%%')
    # 3. Temporäre Platzhalter → %s (psycopg2 Parameter-Syntax)
    sql = sql.replace(_PLACEHOLDER, '%s')

    if _RE_INSERT_IGNORE.search(sql):
        sql = _RE_INSERT_IGNORE.sub('INSERT INTO', sql)
        sql = sql.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'

    sql = _RE_AUTOINCREMENT.sub('BIGSERIAL PRIMARY KEY', sql)
    sql = _RE_DATETIME_DEFAULT.sub('DEFAULT CURRENT_TIMESTAMP', sql)
    return sql


# ─── Row-Wrapper ──────────────────────────────────────────────────────────────

class _Row(dict):
    """Zeile als dict mit zusätzlichem Integer-Index (wie sqlite3.Row)."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


# ─── Cursor-Wrapper ───────────────────────────────────────────────────────────

class _Cursor:
    def __init__(self, raw_cur, is_pg):
        self._cur = raw_cur
        self._is_pg = is_pg

    def fetchall(self):
        try:
            rows = self._cur.fetchall()
            if not rows:
                return []
            if self._is_pg:
                return [_Row(dict(r)) for r in rows]
            return [_Row(dict(r)) for r in rows]
        except Exception:
            return []

    def fetchone(self):
        try:
            row = self._cur.fetchone()
            if row is None:
                return None
            return _Row(dict(row))
        except Exception:
            return None

    @property
    def rowcount(self):
        return self._cur.rowcount


# ─── Connection-Wrapper ───────────────────────────────────────────────────────

class _Conn:
    def __init__(self, raw_conn, is_pg):
        self._conn = raw_conn
        self._is_pg = is_pg

    def _mk_cursor(self):
        if self._is_pg:
            import psycopg2.extras
            return self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self._conn.cursor()

    def execute(self, sql, params=None):
        if self._is_pg:
            sql = _adapt_pg(sql)
        cur = self._mk_cursor()
        cur.execute(sql, params or [])
        return _Cursor(cur, self._is_pg)

    def execute_safe(self, sql, params=None):
        """Führt Statement aus und ignoriert Fehler (für ALTER TABLE Migrationen)."""
        if self._is_pg:
            sql = _adapt_pg(sql)
            # Nur zurückrollen wenn die Transaktion tatsächlich im Fehlerzustand ist
            try:
                import psycopg2.extensions as _pgext
                if self._conn.get_transaction_status() == _pgext.TRANSACTION_STATUS_INERROR:
                    self._conn.rollback()
            except Exception:
                pass
            try:
                cur = self._conn.cursor()
                cur.execute('SAVEPOINT _sp_safe')
                cur.execute(sql, params or [])
                cur.execute('RELEASE SAVEPOINT _sp_safe')
            except Exception:
                try:
                    c2 = self._conn.cursor()
                    c2.execute('ROLLBACK TO SAVEPOINT _sp_safe')
                except Exception:
                    try:
                        self._conn.rollback()
                    except Exception:
                        pass
        else:
            try:
                self._conn.execute(sql, params or [])
            except Exception:
                pass

    def commit(self):
        self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self._conn.rollback()
            except Exception:
                pass
        else:
            try:
                self._conn.commit()
            except Exception:
                pass
        self.close()
        return False


# ─── Öffentliche Factory ──────────────────────────────────────────────────────

def get_db():
    """Liefert eine DB-Verbindung (PostgreSQL oder SQLite)."""
    if USE_PG:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return _Conn(conn, is_pg=True)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'nursy.db'))
    conn.row_factory = sqlite3.Row
    return _Conn(conn, is_pg=False)
