from __future__ import annotations
from pathlib import Path
import ast
import sqlite3


def test_all_python_files_parse():
    failures=[]
    for p in Path('.').rglob('*.py'):
        if '.git' in p.parts or '__pycache__' in p.parts: continue
        try: ast.parse(p.read_text(errors='ignore'))
        except Exception as exc: failures.append((str(p),str(exc)))
    assert not failures


def test_packaged_databases_integrity():
    for p in Path('data').glob('*.sqlite3'):
        con=sqlite3.connect(p)
        try: assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        finally: con.close()


def test_main_entry_exists_and_targets_app_py():
    assert Path('app.py').is_file()
    assert 'python-3.12' in Path('runtime.txt').read_text()
