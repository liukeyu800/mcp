"""SQL安全守卫模块"""

import re
from typing import Dict, Any, Optional, List, Tuple


# SQL安全守卫 - 从app移植
BLACKLIST_DDL_DML = re.compile(
    r'\b(?:CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|TRUNCATE|REPLACE)\b', 
    re.IGNORECASE
)

BLACKLIST_DANGEROUS = re.compile(
    r'\b(?:LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE|EXEC|EXECUTE|xp_cmdshell)\b', 
    re.IGNORECASE
)

ALLOWED_STARTS = re.compile(
    r'^\s*(?:SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b', 
    re.IGNORECASE
)


def single_statement(sql: str) -> str:
    """确保只有一条SQL语句"""
    sql = sql.strip()
    if ';' in sql[:-1]:  # 允许末尾的分号
        sql = sql.split(';')[0]
    return sql


def cap_limit(sql: str, max_limit: int = 100) -> str:
    """限制查询结果数量"""
    sql = sql.strip()
    
    # 如果已经有LIMIT，检查是否超过最大值
    limit_match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
    if limit_match:
        current_limit = int(limit_match.group(1))
        if current_limit > max_limit:
            sql = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {max_limit}', sql, flags=re.IGNORECASE)
    else:
        # 如果没有LIMIT，添加一个
        sql = f"{sql} LIMIT {max_limit}"
    
    return sql


def ensure_read_only(sql: str) -> str:
    """确保SQL是只读的"""
    if BLACKLIST_DDL_DML.search(sql):
        raise ValueError("禁止DDL/DML操作")
    
    if BLACKLIST_DANGEROUS.search(sql):
        raise ValueError("禁止危险函数")
    
    if not ALLOWED_STARTS.match(sql):
        raise ValueError("只允许SELECT/SHOW/DESCRIBE/EXPLAIN语句")
    
    return sql


def sanitize_sql(sql: str) -> str:
    """清理SQL语句"""
    sql = single_statement(sql)
    sql = cap_limit(sql)
    return sql


def ensure_safe_sql(sql: str) -> str:
    """确保SQL安全（主入口）"""
    sql = sanitize_sql(sql)
    sql = ensure_read_only(sql)
    return sql