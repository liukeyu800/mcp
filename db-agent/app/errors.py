# app/errors.py
RETRYABLE  = {"LOCK_TIMEOUT","DEADLOCK","LOST_CONNECTION","TIMEOUT"}
SCHEMA_ERR = {"UNKNOWN_TABLE","UNKNOWN_COLUMN","SQL_SYNTAX_ERROR"}
TOO_LARGE  = {"RESULT_TOO_LARGE"}

def ok(res):
    return bool(res and res.get("ok", True) and not res.get("error"))

def code(res):
    if not res:
        return "UNKNOWN"
    return (res.get("error") or {}).get("code", "UNKNOWN")
