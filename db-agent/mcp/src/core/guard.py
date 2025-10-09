"""智能守卫模块"""

import re
from typing import Dict, Any, Optional, List, Tuple
from .schemas import AgentState
from .memory import (
    infer_candidate_tables, 
    is_count_question, 
    has_recent_sql_evidence
)


# SQL安全守卫 - 从app移植
BLACKLIST_DDL_DML = re.compile(
    r'\b(?:CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|TRUNCATE|REPLACE)\b', 
    re.IGNORECASE
)

BLACKLIST_DANGEROUS = re.compile(
    r'\b(?:LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE|EXEC|EXECUTE|xp_cmdshell)\b', 
    re.IGNORECASE
)

MULTI_STATEMENT = re.compile(r';\s*\w', re.IGNORECASE)
COMMENT_PATTERNS = [
    re.compile(r'--.*$', re.MULTILINE),
    re.compile(r'/\*.*?\*/', re.DOTALL),
    re.compile(r'#.*$', re.MULTILINE)
]

ALLOWED_STARTS = re.compile(
    r'^\s*(?:SELECT|SHOW|DESCRIBE|DESC|EXPLAIN|WITH)\b', 
    re.IGNORECASE
)

LIMIT_PATTERN = re.compile(r'\bLIMIT\s+(\d+)\b', re.IGNORECASE)


def strip_comments(sql: str) -> str:
    """去除SQL注释"""
    for pattern in COMMENT_PATTERNS:
        sql = pattern.sub('', sql)
    return sql.strip()


def single_statement(sql: str) -> str:
    """保留第一条语句"""
    if MULTI_STATEMENT.search(sql):
        return sql.split(';')[0].strip()
    return sql


def cap_limit(sql: str, max_limit: int = 100) -> str:
    """限制LIMIT子句的值"""
    def replace_limit(match):
        limit_val = int(match.group(1))
        return f"LIMIT {min(limit_val, max_limit)}"
    
    result = LIMIT_PATTERN.sub(replace_limit, sql)
    
    # 如果没有LIMIT，添加默认LIMIT
    if not LIMIT_PATTERN.search(sql) and sql.strip().upper().startswith('SELECT'):
        result += f" LIMIT {max_limit}"
    
    return result


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
    sql = strip_comments(sql)
    sql = single_statement(sql)
    sql = cap_limit(sql)
    return sql


def ensure_safe_sql(sql: str) -> str:
    """确保SQL安全（主入口）"""
    sql = sanitize_sql(sql)
    sql = ensure_read_only(sql)
    return sql


class IntelligentGuard:
    """智能守卫，防止无效操作和过早结束"""
    
    def __init__(self):
        self.max_retries = 3
        self.min_evidence_steps = 2
    
    def should_prevent_early_finish(self, state: AgentState) -> bool:
        """检查是否应该防止过早结束"""
        # 如果没有足够的证据，防止过早结束
        if len(state.steps) < self.min_evidence_steps:
            return True
        
        # 检查最近是否有成功的数据库操作
        return not has_recent_sql_evidence(state)
    
    def suggest_alternative_action(self, state: AgentState, intended_action: str) -> Optional[str]:
        """建议替代行动"""
        if intended_action == "finish" and self.should_prevent_early_finish(state):
            # 如果没有表信息，建议列出表
            if not state.known_tables:
                return "list_tables"
            
            # 如果有表但没有结构信息，建议描述表
            if state.known_tables and not state.known_schemas:
                return "describe_table"
            
            # 如果有结构但没有数据，建议采样
            if state.known_schemas:
                return "sample_rows"
        
        return None
    
    def rewrite_action_with_intelligence(self, state: AgentState, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """智能改写动作（从app移植的核心逻辑）"""
        result = {"action": action, "args": args, "modified": False, "reason": ""}
        
        # 1. 防止重复list_tables
        if action == "list_tables" and state.known_tables:
            # 已知表，改为描述最相关的表
            candidates = infer_candidate_tables(state, top_k=1)
            if candidates and candidates[0] not in state.known_schemas:
                result.update({
                    "action": "describe_table",
                    "args": {"table": candidates[0]},
                    "modified": True,
                    "reason": f"已知表列表，改为描述最相关表: {candidates[0]}"
                })
            else:
                # 所有候选表都已知结构，改为采样
                result.update({
                    "action": "sample_rows", 
                    "args": {"table": candidates[0] if candidates else state.known_tables[0]},
                    "modified": True,
                    "reason": "表结构已知，改为采样数据"
                })
        
        # 2. 防止重复describe_table
        elif action == "describe_table":
            table = args.get("table")
            if table and table in state.known_schemas:
                result.update({
                    "action": "sample_rows",
                    "args": {"table": table},
                    "modified": True,
                    "reason": f"表{table}结构已知，改为采样数据"
                })
        
        # 3. 智能finish防护
        elif action == "finish":
            if not has_recent_sql_evidence(state):
                # 没有近期SQL证据，根据情况改写
                if not state.known_tables:
                    result.update({
                        "action": "list_tables",
                        "args": {},
                        "modified": True,
                        "reason": "无SQL证据且无已知表，改为列表操作"
                    })
                elif state.known_tables and not state.known_schemas:
                    candidates = infer_candidate_tables(state, top_k=1)
                    result.update({
                        "action": "describe_table",
                        "args": {"table": candidates[0] if candidates else state.known_tables[0]},
                        "modified": True,
                        "reason": "无SQL证据且无表结构，改为描述表"
                    })
                elif state.known_schemas:
                    # 有结构但无SQL证据，尝试查询
                    candidates = infer_candidate_tables(state, top_k=1)
                    if is_count_question(state.question):
                        # 计数问题，构造COUNT查询
                        table = candidates[0] if candidates else list(state.known_schemas.keys())[0]
                        result.update({
                            "action": "run_sql",
                            "args": {"sql": f"SELECT COUNT(*) FROM {table}"},
                            "modified": True,
                            "reason": f"计数问题无SQL证据，改为COUNT查询: {table}"
                        })
                    else:
                        # 非计数问题，采样数据
                        table = candidates[0] if candidates else list(state.known_schemas.keys())[0]
                        result.update({
                            "action": "sample_rows",
                            "args": {"table": table},
                            "modified": True,
                            "reason": f"无SQL证据，改为采样: {table}"
                        })
        
        # 4. SQL安全检查
        elif action == "run_sql":
            sql = args.get("sql", "")
            try:
                safe_sql = ensure_safe_sql(sql)
                if safe_sql != sql:
                    result.update({
                        "args": {**args, "sql": safe_sql},
                        "modified": True,
                        "reason": "SQL已清理和安全化"
                    })
            except ValueError as e:
                # SQL不安全，改为安全操作
                result.update({
                    "action": "list_tables",
                    "args": {},
                    "modified": True,
                    "reason": f"SQL不安全({e})，改为列表操作"
                })
        
        return result
    
    def validate_action(self, state: AgentState, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """验证并可能修改行动（保持向后兼容）"""
        return self.rewrite_action_with_intelligence(state, action, args)