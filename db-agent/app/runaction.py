# app/planner.py 或 app/your_actions.py 里
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from typing import Dict, Any
from .guard import ensure_safe_sql
from .tools import mcp_read_query, mcp_list_tables, mcp_describe_table, sample_rows
from .errors import ok, code, RETRYABLE

class TransientError(Exception):
    pass

@retry(
    reraise=True,
    stop=stop_after_attempt(3),                          # 最多 3 次
    wait=wait_exponential_jitter(initial=0.5, max=4.0), # 指数退避 + 抖动
    retry=retry_if_exception_type(TransientError)
)
def _safe_read(sql: str, limit: int = 1000) -> Dict[str, Any]:
    safe = ensure_safe_sql(sql, default_limit=1000, max_limit=5000)
    res = mcp_read_query(safe, limit=limit, read_only=True)
    if ok(res):
        return res
    c = code(res)
    if c in RETRYABLE:
        # 抛出以触发 tenacity 重试（指数退避）
        raise TransientError(c)
    # 非重试型错误：直接返回给上层由 ReAct 重新规划（换表/改条件/写 JOIN）
    return res

def run_action(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    统一的动作执行器：只在 run_sql 路径做 SQL 安全与重试；
    其余动作（list/describe/sample/search）无状态、无副作用，直接转发。
    """
    if action == "list_tables":
        return mcp_list_tables()
    elif action == "describe_table":
        return mcp_describe_table(args.get("table"))
    elif action == "sample_rows":
        return sample_rows(args.get("table"), args.get("limit", 10))
    elif action == "run_sql":
        sql = args.get("sql", "")
        if not sql:
            return {"success": False, "error": "SQL query is required"}
        
        # 安全检查
        safe_result = ensure_safe_sql(sql)
        if not safe_result["safe"]:
            return {"success": False, "error": safe_result["reason"]}
        
        return mcp_read_query(sql)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}
