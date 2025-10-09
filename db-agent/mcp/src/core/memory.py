"""记忆管理模块"""

import json
import sqlite3
import threading
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .schemas import AgentState, Step


def truncate_list(xs: List[str], n: int) -> List[str]:
    """截断列表到指定长度"""
    return xs[:n] if xs else []


def truncate_text(s: str, max_chars: int) -> str:
    """截断文本到指定字符数"""
    if not s: 
        return ""
    s = str(s)
    return s[:max_chars] + ("…" if len(s) > max_chars else "")


def summarize_context(state: AgentState, *, 
                      max_tables: int = 40, 
                      max_cols_per_table: int = 12, 
                      max_preview_chars: int = 400, 
                      max_steps: int = 6) -> str:
    """
    压缩上下文为精炼的知识提示，包含：
    1. 已知表名列表
    2. 表结构信息
    3. 最近几步的操作轨迹
    4. 遇到的错误
    """
    # 1. 已知表名（排序去重，限制数量）
    tables = truncate_list(
        sorted(set(getattr(state, "known_tables", []) or [])), 
        max_tables
    )

    # 2. 表结构信息（压缩列名）
    schemas = {}
    for t, sch in (getattr(state, "known_schemas", {}) or {}).items():
        cols = sch.get("columns") or sch.get("data", {}).get("columns") or []
        names = []
        for c in cols:
            if isinstance(c, dict) and "name" in c:
                names.append(c["name"])
            elif isinstance(c, str):
                names.append(c)
        if names:
            schemas[t] = truncate_list(names, max_cols_per_table)

    # 3. 最近操作轨迹（压缩内容）
    trail = []
    for s in (getattr(state, "steps", []) or [])[-max_steps:]:
        obs = s.observation or {}
        trail.append({
            "thought": truncate_text(getattr(s, "thought", ""), 240),
            "action": getattr(s, "action", ""),
            "args": {k: truncate_text(v, 160) if isinstance(v, str) else v 
                     for k, v in (getattr(s, "args", {}) or {}).items()},
            "ok": bool(obs.get("ok")),
            "err": (obs.get("error") or {}).get("code"),
            "tables": obs.get("tables"),
            "matches": obs.get("matches"),
            "columns": obs.get("columns"),
            "preview": truncate_text(obs.get("preview"), max_preview_chars)
        })

    # 4. 最近错误
    last_err = getattr(state, "last_error", None)

    # 5. 组装知识提示
    payload = {
        "known_tables": tables,
        "known_schemas": schemas,
        "recent_steps": trail,
        "last_error_code": last_err
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def infer_candidate_tables(state: AgentState, top_k: int = 3) -> List[str]:
    """
    智能表优先级排序：
    1. 问题中直接提到的表名
    2. 已经获取过结构信息的表（说明更相关）
    3. 其他未探索的表
    """
    q = (getattr(state, "question", "") or "").lower()
    known = list(getattr(state, "known_tables", []) or [])
    pri: List[str] = []
    
    # 1) 问题中直接出现的表名优先
    for t in known:
        tl = t.lower()
        if tl and (tl in q or re.search(rf"\b{re.escape(tl)}\b", q)):
            pri.append(t)
    
    # 2) 已经拿到 schema 的表次之（说明更相关）
    schemas = getattr(state, "known_schemas", {}) or {}
    for t in schemas.keys():
        if t not in pri and t in known:
            pri.append(t)
    
    # 3) 其余表保持原顺序补齐
    for t in known:
        if t not in pri:
            pri.append(t)
    
    return pri[:top_k]


def is_count_question(text: str) -> bool:
    """识别计数类问题"""
    t = (text or "").lower()
    keys = ["多少", "有几个", "数量", "总数", "count", "计数", "几人", "几项", "几条", "几个"]
    return any(k in t for k in keys)


def has_recent_sql_evidence(state: AgentState, lookback: int = 6) -> bool:
    """检查是否有最近的SQL执行证据"""
    recent_steps = state.steps[-lookback:] if len(state.steps) > lookback else state.steps
    for step in recent_steps:
        if step.action == "run_sql" and step.observation.get("ok"):
            return True
    return False


def extract_latest_evidence(state: AgentState) -> Dict[str, Any]:
    """提取最近一次可视化证据（供前端直接使用）"""
    for s in reversed(state.steps):
        try:
            if s.action in ("run_sql", "sample_rows"):
                ev = {
                    "preview": (s.observation or {}).get("preview"),
                    "sql": s.args.get("sql") if s.action == "run_sql" else None,
                    "table": s.args.get("table") if s.action == "sample_rows" else None,
                }
                # 过滤空证据
                if ev.get("preview") is not None:
                    return ev
        except Exception:
            continue
    return {}


class MemoryManager:
    """记忆管理器，负责状态的持久化和检索"""
    
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self):
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_states (
                thread_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    
    def save_state(self, thread_id: str, state: AgentState) -> None:
        """保存状态到数据库"""
        conn = self._get_connection()
        state_json = json.dumps(state.dict(), ensure_ascii=False)
        
        conn.execute("""
            INSERT OR REPLACE INTO agent_states (thread_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (thread_id, state_json))
        conn.commit()
    
    def load_state(self, thread_id: str) -> Optional[AgentState]:
        """从数据库加载状态"""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT state_data FROM agent_states WHERE thread_id = ?",
            (thread_id,)
        ).fetchone()
        
        if row:
            state_data = json.loads(row['state_data'])
            return AgentState(**state_data)
        return None
    
    def delete_state(self, thread_id: str) -> bool:
        """删除指定的状态"""
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM agent_states WHERE thread_id = ?",
            (thread_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    def cleanup_old_states(self, days: int = 30) -> int:
        """清理超过指定天数的旧状态"""
        conn = self._get_connection()
        cutoff_date = datetime.now() - timedelta(days=days)
        cursor = conn.execute(
            "DELETE FROM agent_states WHERE updated_at < ?",
            (cutoff_date.isoformat(),)
        )
        conn.commit()
        return cursor.rowcount
    
    def list_sessions(self):
        """列出所有会话"""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT thread_id, created_at, updated_at 
            FROM agent_states 
            ORDER BY updated_at DESC
        """)
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "thread_id": row[0],
                "created_at": row[1],
                "updated_at": row[2]
            })
        return sessions


# 全局记忆管理器实例
memory_manager = MemoryManager()