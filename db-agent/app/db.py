# app/db.py
import os
from typing import List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError, OperationalError, NoSuchTableError
from .guard import ensure_safe_sql

_engine = None
_db_url = None


def _result_ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, **data}


def _result_err(code: str, message: str) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _get_engine():
    global _engine, _db_url
    if _engine is not None:
        return _engine
    _db_url = os.getenv("DB_URL")
    if not _db_url:
        return None
    _engine = create_engine(_db_url, pool_pre_ping=True, future=True)
    return _engine


def db_list_tables() -> Dict[str, Any]:
    eng = _get_engine()
    if eng is None:
        return _result_err("NO_DB_URL", "请在 .env 设置 DB_URL，例如 mysql+pymysql://user:pass@host:3306/dbname")
    try:
        insp = inspect(eng)
        tables = sorted(list(set(insp.get_table_names())))
        return _result_ok({"tables": tables})
    except OperationalError as e:
        return _result_err("LOST_CONNECTION", str(e))
    except Exception as e:
        return _result_err("UNKNOWN", str(e))


def db_describe_table(table: str) -> Dict[str, Any]:
    eng = _get_engine()
    if eng is None:
        return _result_err("NO_DB_URL", "请在 .env 设置 DB_URL，例如 mysql+pymysql://user:pass@host:3306/dbname")
    try:
        insp = inspect(eng)
        cols = insp.get_columns(table)
        columns = [{"name": c.get("name"), "type": str(c.get("type"))} for c in cols]
        return _result_ok({"columns": columns})
    except NoSuchTableError:
        return _result_err("UNKNOWN_TABLE", f"No such table: {table}")
    except ProgrammingError as e:
        msg = str(e)
        code = "SQL_SYNTAX_ERROR"
        if "Unknown column" in msg or "doesn't exist" in msg:
            code = "UNKNOWN_COLUMN"
        return _result_err(code, msg)
    except Exception as e:
        return _result_err("UNKNOWN", str(e))


def db_read_query(sql: str, limit: int = 1000, read_only: bool = True) -> Dict[str, Any]:
    eng = _get_engine()
    if eng is None:
        return _result_err("NO_DB_URL", "请在 .env 设置 DB_URL，例如 mysql+pymysql://user:pass@host:3306/dbname")
    try:
        safe = ensure_safe_sql(sql, default_limit=limit or 1000, max_limit=max(limit or 1000, 1000))
        with eng.connect() as conn:
            rs = conn.execute(text(safe))
            rows = rs.mappings().fetchmany(size=limit or 1000)
            data = [dict(r) for r in rows]
        return _result_ok({"data": data})
    except ProgrammingError as e:
        msg = str(e)
        code = "SQL_SYNTAX_ERROR"
        if "Unknown table" in msg or "doesn't exist" in msg:
            code = "UNKNOWN_TABLE"
        elif "Unknown column" in msg:
            code = "UNKNOWN_COLUMN"
        return _result_err(code, msg)
    except OperationalError as e:
        return _result_err("LOST_CONNECTION", str(e))
    except Exception as e:
        return _result_err("UNKNOWN", str(e))