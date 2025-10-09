# app/planner.py
import os
from dotenv import load_dotenv

# 自动加载app目录下的 .env 文件
APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(APP_DIR, ".env"))

# 现在 os.getenv("MCP_BASE")、os.getenv("OPENAI_API_KEY") 等就能直接用了
MCP_BASE = os.getenv("MCP_BASE")
DEFAULT_LIMIT = int(os.getenv("SQL_DEFAULT_LIMIT", 1000))
MAX_LIMIT = int(os.getenv("SQL_MAX_LIMIT", 5000))

import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
import requests

from .tools import mcp_list_tables, mcp_describe_table, mcp_read_query, sample_rows
from .errors import ok, code, RETRYABLE, SCHEMA_ERR, TOO_LARGE
from .guard import ensure_safe_sql
from .prompts import SYSTEM
from .planner_decide import llm_decide_with_memory
from .schemas import validate_decide

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # 或使用你偏好的模型

class Step(BaseModel):
    thought: str = ""
    action: str = ""
    args: Dict[str, Any] = {}
    observation: Dict[str, Any] = {}

class S(BaseModel):
    question: str
    steps: List[Step] = Field(default_factory=list)
    known_tables: List[str] = Field(default_factory=list)
    known_schemas: Dict[str, Any] = Field(default_factory=dict)  # table -> {columns:[...]}
    last_error: Optional[str] = None
    done: bool = False
    answer: Optional[Dict[str, Any]] = None
    max_steps: int = 20
    

# —— 调 LLM，让它“决定下一步动作” —— #
def llm_decide(state: S) -> Dict[str, Any]:
    msgs = [{"role":"system","content":SYSTEM},
            {"role":"user","content":state.question}]
    # 附上思维链痕迹（观察摘要），帮助 LLM 复用已知表/列
    if state.steps:
        trace = [{"thought":s.thought, "action":s.action, "args":s.args,
                  "observation": {k:v for k,v in s.observation.items() if k in ("ok","error","preview","columns","tables")}}
                 for s in state.steps[-6:]]
        msgs.append({"role":"user","content":"先前步骤（节选）：\n"+json.dumps(trace,ensure_ascii=False)})

    # 简洁调用（可换任意兼容的 Chat/Responses API）
    resp = requests.post("https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model":"gpt-4o-mini",
            "temperature":0.2,
            "messages": msgs,
            "response_format":{"type":"json_object"}
        }
    ).json()
    txt = resp["choices"][0]["message"]["content"]
    return json.loads(txt)  # 期望 {"thought":...,"action":"...","args":{...}}

# —— 执行动作（非固定回退，完全按 LLM 决策） —— #
class TransientError(Exception): pass

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.5, max=4.0),
    retry=retry_if_exception_type(TransientError)
)

def _safe_read(sql: str, limit: int = 1000) -> Dict[str, Any]:
    safe = ensure_safe_sql(sql, default_limit=1000, max_limit=5000)
    res = mcp_read_query(safe, limit=limit, read_only=True)
    if ok(res):
        return res
    c = code(res)
    if c in RETRYABLE:
        raise TransientError(c)
    return res

def run_action(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if action == "list_tables":
        return mcp_list_tables()
    elif action == "describe_table":
        return mcp_describe_table(args.get("table",""))
    elif action == "sample_rows":
        return sample_rows(args.get("table",""), args.get("limit",5))
    elif action == "run_sql":
        return mcp_read_query(args.get("sql",""), limit=args.get("limit",1000))
    else:
        return {"ok": False, "error": f"未知动作: {action}"}

# 从用户问题中粗略提取卫星代号（如 PRSS-1）
_def_code_pattern = re.compile(r"\b([A-Z]{2,}[0-9A-Z-]{0,6}\d)\b")

def _extract_aircraft_code(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"PRSS-\d+", text, flags=re.IGNORECASE)
    if m:
        return m.group(0).upper()
    m2 = _def_code_pattern.search((text or "").upper())
    if m2:
        return m2.group(1).upper()
    return None

# 通用：基于问题与已知信息推测候选表（与业务无关，适用于任意查询）
def _infer_candidate_tables(state, top_k: int = 3) -> List[str]:
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

# 新增：计数类问题识别
def _is_count_question(text: str) -> bool:
    t = (text or "").lower()
    keys = ["多少", "有几个", "数量", "总数", "count", "计数", "几人", "几项", "几条", "几个"]
    return any(k in t for k in keys)

def decide(state: S) -> S:
    
    # 复位：同一线程的新问题开始时，清除上轮的完成标记，避免被短路
    if getattr(state, "done", False):
        state.done = False
        state.answer = None

    # 滑动窗口：为当前轮对话留出预算，避免一上来就 step_budget_exceeded
    if len(state.steps) > state.max_steps - 2:
        keep = max(state.max_steps // 2, 6)
        state.steps = state.steps[-keep:]

    if len(state.steps) >= state.max_steps:
        state.done = True
        state.answer = {"ok": False, "reason": "step_budget_exceeded", "trace": [s.dict() for s in state.steps]}
        return state

    raw = llm_decide_with_memory(state)
    parsed = validate_decide(raw)

    # 防止“无证据的过早结束”：若 LLM 提议 finish，但近期没有任何成功的 run_sql 证据，则改写为更合理的下一步（通用策略）
    if parsed.action == "finish":
        try:
            if not _has_recent_sql_evidence(state):
                # a) 尚未知表 → 先获取全量表
                if not state.known_tables:
                    parsed.action = "list_tables"
                    parsed.args = {}
                    parsed.thought = (parsed.thought or "") + "\n[guard] 改写 finish 为 list_tables 获取全量表名（通用）"
                else:
                    # b) 基于问题与已知信息推候选表
                    cands = _infer_candidate_tables(state, top_k=3)
                    # c) 优先补充 schema 证据
                    ks = getattr(state, "known_schemas", {}) or {}
                    need_describe = None
                    for t in cands:
                        if t not in ks:
                            need_describe = t
                            break
                    if need_describe:
                        parsed.action = "describe_table"
                        parsed.args = {"table": need_describe}
                        parsed.thought = (parsed.thought or "") + f"\n[guard] 改写 finish 为 describe_table({need_describe}) 以获取结构证据（通用）"
                    else:
                        # d) 所有候选表已有 schema → 直接产出可验证证据
                        target = cands[0] if cands else (state.known_tables[0] if state.known_tables else None)
                        if target:
                            if _is_count_question(getattr(state, "question", "")):
                                sql = f"SELECT COUNT(*) AS cnt FROM `{target}`"
                                parsed.thought = (parsed.thought or "") + f"\n[guard] 识别为计数问题，改写 finish 为 run_sql(COUNT `{target}`)（通用）"
                            else:
                                sql = f"SELECT * FROM `{target}` LIMIT 5"
                                parsed.thought = (parsed.thought or "") + f"\n[guard] 改写 finish 为 run_sql(抽样 {target}) 以获取直接证据（通用）"
                            parsed.action = "run_sql"
                            parsed.args = {"sql": sql}
                        else:
                            # e) 极端兜底：直接返回已知表信息
                            parsed.action = "list_tables"
                            parsed.args = {}
                            parsed.thought = (parsed.thought or "") + "\n[guard] 改写 finish 为 list_tables（通用兜底）"
        except Exception:
            # 兜底：不阻断流程
            pass

    state.steps.append(Step(thought=parsed.thought, action=parsed.action, args=parsed.args))
    return state

def act(state: S) -> S:
    step = state.steps[-1]
    obs = run_action(step.action, step.args)
    step.observation = summarize_obs(step.action, obs)
    # 缓存知识
    if step.action in ("list_tables") and ok(obs):
        allnames = obs.get("tables") or obs.get("data",{}).get("all",[])
        state.known_tables = sorted(set(state.known_tables + (allnames or [])))
    if step.action == "describe_table" and ok(obs):
        tbl = step.args.get("table")
        state.known_schemas[tbl] = obs
    # finish?
    if step.action == "finish":
        state.done = True
        state.answer = {"ok": True, "final": obs.get("data")}
        state.done = True
        final = obs.get("data") if isinstance(obs, dict) else None
        # 附加：统一证据出口，供前端直接读取，无需遍历 steps
        evidence = _latest_evidence(state)
        state.answer = {"ok": True, "final": final, "evidence": evidence}
    # 记录错误码
    if not ok(obs):
        state.last_error = code(obs)
    return state

def summarize_obs(action: str, obs: Dict[str, Any]) -> Dict[str, Any]:
    if action in ("list_tables"):
        matches = obs.get("data",{}).get("matches")
        tables  = obs.get("tables") or obs.get("data",{}).get("all")
        return {"ok": ok(obs), "matches": matches, "tables": tables, "error": obs.get("error")}
    if action == "describe_table":
        return {"ok": ok(obs), "columns": (obs.get("columns") or obs.get("data",{}).get("columns")), "error": obs.get("error")}
    if action in ("sample_rows","run_sql"):
        preview = obs.get("data")
        # 建议这里只保留前几行和列名，避免 trace 爆炸
        return {"ok": ok(obs), "preview": preview, "error": obs.get("error")}
    if action == "finish":
        return obs
    return {"ok": ok(obs), "error": obs.get("error")}

# 新增：提取最近一次可视化证据（供前端直接使用，无需遍历 steps）
def _latest_evidence(state: S) -> Dict[str, Any]:
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

# 基于轨迹的“证据”判定：是否已有成功的 SQL 结果
def _has_recent_sql_evidence(state: S, lookback: int = 6) -> bool:
    """满足任一条件即视为有证据：
    - 最近 lookback 步内出现过 action==run_sql，且 observation.ok 为 True；
    - 且 preview 非空（有返回数据或结构）。
    """
    if not state.steps:
        return False
    for s in reversed(state.steps[-lookback:]):
        if s.action == "run_sql":
            obs = s.observation or {}
            if obs.get("ok") and obs.get("preview"):
                return True
    return False

# 可选：一个“满足度评估”节点（让 LLM 判断是否应 finish）
def judge(state: S) -> S:
    if state.done:
        # 若是由 finish 导致的 done，但没有证据，则撤销 done，避免过早结束
        last = state.steps[-1] if state.steps else None
        if last and last.action == "finish" and not _has_recent_sql_evidence(state):
            state.done = False
            state.last_error = "premature_finish"
        return state
    # 简单规则：若最近 2 步都是 run_sql 且 ok，可提示 LLM finish；否则继续 decide
    last2 = state.steps[-2:] if len(state.steps)>=2 else state.steps
    if all(s.action=="run_sql" and s.observation.get("ok") for s in last2) and len(state.steps)>=3:
        # 给下一轮 decide 更多 finish 倾向（你也可直接在此自动 finish）
        pass
    return state

# 编译 LangGraph
builder = StateGraph(S)
builder.add_node("decide", decide)
builder.add_node("act", act)
builder.add_node("judge", judge)
builder.add_edge(START, "decide")
builder.add_edge("decide", "act")
builder.add_edge("act", "judge")
builder.add_conditional_edges("judge", lambda s: s.done, {True: END, False: "decide"})
graph = builder.compile(checkpointer=MemorySaver())
