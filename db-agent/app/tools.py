# app/tools.py
import os, re, requests
from typing import Dict, Any, List
MCP = os.getenv("MCP_BASE", "http://127.0.0.1:9621")
TMO = (5, 30)


def mcp_list_tables() -> Dict[str, Any]:
    return requests.post(f"{MCP}/list_tables", json={}, timeout=TMO).json()


def mcp_describe_table(table: str) -> Dict[str, Any]:
    return requests.post(f"{MCP}/describe_table", json={"table": table}, timeout=TMO).json()


def mcp_read_query(sql: str, limit: int = 1000, read_only: bool = True) -> Dict[str, Any]:
    return requests.post(
        f"{MCP}/read_query",
        json={"sql": sql, "limit": limit, "read_only": bool(read_only)},
        timeout=TMO,
    ).json()

# 新增：抽样看行（避免一上来就写 SQL）

def sample_rows(table: str, limit: int = 5) -> Dict[str, Any]:
    sql = f"SELECT * FROM `{table}` LIMIT {int(limit)}"
    return mcp_read_query(sql, limit=limit)
