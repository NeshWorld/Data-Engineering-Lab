"""Bounded real SQLite execution and atomic publication of request results."""
import json
import math
import sqlite3
import time
from .storage import database, backup_database

def reject_constant(value):
    raise ValueError('JSON non fini interdit : ' + value)

def finite_float(value):
    result=float(value)
    if not math.isfinite(result):
        raise ValueError('Nombre JSON hors limites : '+value)
    return result

def strict_json_loads(value):
    return json.loads(value,parse_constant=reject_constant,parse_float=finite_float)

def identifier(value):
    return '"' + str(value).replace('"', '""') + '"'

def safe_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, bytes):
        return '[BLOB ' + str(len(value)) + ' octets]'
    if isinstance(value, str) and len(value) > 20000:
        return value[:20000] + ' … [cellule tronquée]'
    return value

def statements(code):
    current = ''
    for ch in code:
        current += ch
        if ch == ';' and sqlite3.complete_statement(current):
            yield current
            current = ''
    if current.strip():
        yield current

def execute_sql(path, code, deadline=5, read_only=False):
    if not isinstance(code, str) or not code.strip() or len(code) > 200000:
        raise ValueError('Requête vide ou supérieure à 200 000 caractères.')
    started = time.monotonic()
    conn = sqlite3.connect(':memory:', isolation_level=None)
    with database(path, timeout=2) as original:
        backup_database(original,conn,timeout=deadline)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA trusted_schema=OFF')
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2_000_000)
        conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 200000)
        conn.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 256)
        allowed_pragmas = {'table_info','table_xinfo','index_list','index_info','index_xinfo',
                          'foreign_key_list','foreign_key_check','foreign_keys','integrity_check','quick_check'}
        def authorize(action, a, b, *_):
            if read_only and action not in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE):
                return sqlite3.SQLITE_DENY
            if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION and (b or a or '').lower() == 'load_extension':
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_PRAGMA and (a or '').lower() not in allowed_pragmas:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        initial_schema = conn.execute('PRAGMA schema_version').fetchone()[0]
        conn.set_authorizer(authorize)
        conn.set_progress_handler(lambda: int(time.monotonic()-started > deadline), 1000)
        chunks = list(statements(code))
        # The private copy makes publication atomic without rewriting SQLite transactions.
        columns, rows, count = [], [], 0
        before = conn.total_changes
        for sql in chunks:
            cur = conn.execute(sql)
            if cur.description:
                columns = [x[0] for x in cur.description]
                rows, count, budget = [], 0, 2_000_000
                for row in cur:
                    count += 1
                    if count <= 1000 and budget > 0:
                        converted=[safe_json(v) for v in row]
                        cost=len(json.dumps(converted,ensure_ascii=False).encode('utf-8'))
                        if cost<=budget:
                            rows.append(converted)
                            budget-=cost
                        else:
                            budget=0
                    if time.monotonic()-started > deadline:
                        raise TimeoutError('Requête interrompue après 5 secondes.')
        if conn.in_transaction:
            conn.commit()
        conn.set_authorizer(None)
        changed_schema = conn.execute('PRAGMA schema_version').fetchone()[0] != initial_schema
        if conn.total_changes or changed_schema:
            with database(path, timeout=2) as destination:
                backup_database(conn,destination)
        return dict(columns=columns, rows=rows, row_count=count, truncated=count > len(rows),
                    changes=conn.total_changes-before, duration_ms=round((time.monotonic()-started)*1000, 2))
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()

