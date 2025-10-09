# app/guard.py
import re
from typing import Tuple

# —— 黑名单：拒绝 DDL/DML、危险函数/导出 —— #
DDL_DML = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|REPLACE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE)\b", re.I)
DANGEROUS_FUNCS = re.compile(r"\b(SLEEP|BENCHMARK|LOAD_FILE)\s*\(", re.I)
OUTFILE_INFILE = re.compile(r"\b(INTO\s+OUTFILE|INTO\s+DUMPFILE|LOAD\s+DATA\s+INFILE)\b", re.I)

# —— 多语句/注释处理 —— #
SQL_COMMENT = re.compile(r"(--[^\n]*\n)|(/\*.*?\*/)", re.S)
SEMICOLON = re.compile(r";")

# —— 允许的起始关键词（只读） —— #
ALLOWED_START = re.compile(r"^\s*(SELECT|WITH)\b", re.I)

# —— LIMIT 检测 —— #
HAS_LIMIT = re.compile(r"\blimit\s+\d+", re.I)

def strip_comments(sql: str) -> str:
    return SQL_COMMENT.sub("", sql or "")

def single_statement(sql: str) -> str:
    # 拒绝多条语句；只保留第一条
    parts = SEMICOLON.split(sql)
    return parts[0]

def cap_limit(sql: str, max_limit: int) -> Tuple[str, int]:
    """
    若无 LIMIT 补上；若有 LIMIT 但超过上限则压帽
    返回(新SQL, 实际limit)
    """
    s = sql.strip()
    if not HAS_LIMIT.search(s):
        return f"{s} LIMIT {max_limit}", max_limit
    # 压帽
    m = re.search(r"limit\s+(\d+)", s, flags=re.I)
    if not m:
        return s, max_limit
    cur = int(m.group(1))
    if cur > max_limit:
        s = re.sub(r"(limit\s+)\d+", rf"\g<1>{max_limit}", s, flags=re.I)
        return s, max_limit
    return s, cur

def ensure_read_only(sql: str) -> None:
    s = sql.upper()
    if DDL_DML.search(s) or DANGEROUS_FUNCS.search(s) or OUTFILE_INFILE.search(s):
        raise ValueError("Only read-only SELECT/CTE is allowed.")
    if not ALLOWED_START.search(sql):
        raise ValueError("Query must start with SELECT/WITH.")

def sanitize_sql(sql: str) -> str:
    # 1) 去注释 2) 仅取第一条语句
    s = strip_comments(sql)
    s = single_statement(s)
    return s

def ensure_safe_sql(sql: str, default_limit: int = 1000, max_limit: int = 5000) -> str:
    """
    主入口：确保只读 + 单语句 + 自动/压帽 LIMIT
    """
    s = sanitize_sql(sql)
    ensure_read_only(s)
    s, _ = cap_limit(s, max_limit=max_limit)
    # 若没有任何 LIMIT（极少数情况正则没匹配到），再兜底加一个
    if not HAS_LIMIT.search(s):
        s = f"{s} LIMIT {default_limit}"
    return s
