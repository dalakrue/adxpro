from __future__ import annotations
import sqlite3
from core.history_quality_store_20260621 import ensure_quality_schema
from services.canonical_snapshot_store import DB_PATH
conn=sqlite3.connect(str(DB_PATH))
try:
    conn.execute('BEGIN IMMEDIATE'); ensure_quality_schema(conn); conn.commit(); print(f'Migrated: {DB_PATH}')
except Exception:
    conn.rollback(); raise
finally: conn.close()
