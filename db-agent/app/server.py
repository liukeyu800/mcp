# app/server.py
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from .planner import graph, S
# 新增：加载 .env
import os
from dotenv import load_dotenv
# 加载app目录下的.env文件
APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(APP_DIR, ".env"))
# 新增：导入数据库模块
from . import db
# 新增：用于生成会话ID（thread_id）
from uuid import uuid4
# 新增：简单 NL→SQL 解析
import re


app = FastAPI()

# 健康检查
@app.get("/health")
def health():
    return {"ok": True}

# 根路径：给出简单说明和入口
@app.get("/", response_class=HTMLResponse)
def index():
    return (
        "<html><body>"
        "<h2>DB-Agent 服务已启动</h2>"
        "<p>Swagger 文档：<a href='/docs'>/docs</a></p>"
        "<p>调用接口：POST /plan，Body 示例：{\"question\": \"统计 user 表总数\"}</p>"
        "<p>数据库接口：POST /list_tables、/describe_table、/read_query</p>"
        "</body></html>"
    )

class In(BaseModel):
    question: str
    # 可选：用于对话线程的ID；不传则自动生成，实现多轮/可复用上下文
    thread_id: str | None = None

# 简单规则 NL→SQL（兜底，不依赖外部 LLM）
SAT_PAT = re.compile(r"[A-Za-z]{2,}[A-Za-z0-9\-]*\d+|")
CN_SAT_PAT = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9\-]{2,}?卫星[\u4e00-\u9fa5A-Za-z0-9\-（）()一二三四五六七八九十〇零0-9号型]*")

# 纠偏：latin1 → utf8 的网页乱码修复

def _fix_mojibake(val):
    if not isinstance(val, str):
        return val
    try:
        repaired = val.encode('latin1').decode('utf-8')
        # 若修复后出现更多汉字字符，则采用修复值
        if any('\u4e00' <= ch <= '\u9fff' for ch in repaired):
            return repaired
    except Exception:
        pass
    return val

def _extract_sat_tokens(q: str):
    q = q or ""
    # 代号（如 PRSS-1）
    code = None
    m_code = re.search(r"[A-Za-z]{2,}[A-Za-z0-9\-]*\d+", q)
    if m_code:
        code = m_code.group(0)
    # 中文名（包含“卫星”字样的片段）
    name = None
    m_name = CN_SAT_PAT.search(q)
    if m_name:
        name = m_name.group(0)
    # 兜底：括号内容
    if not code:
        m_paren = re.search(r"[（(]([A-Za-z0-9\-]+)[)）]", q)
        if m_paren:
            code = m_paren.group(1)
    return code, name


def _escape_like(s: str) -> str:
    return (s or "").replace("'", "''")


def simple_plan(question: str):
    code, name = _extract_sat_tokens(question)
    # 识别是否在问“负责人/联系人/电话”
    need_owner = any(k in question for k in ["负责人", "联系人", "电话", "联系方式"]) or True
    if need_owner and (code or name):
        conds = []
        if code:
            conds.append(f"ai.aircraft_code = '{_escape_like(code)}'")
        if name:
            esc = _escape_like(name)
            conds.append(f"ai.publicity_name LIKE '%{esc}%' OR ai.aircraft_name LIKE '%{esc}%'")
        where = " OR ".join(conds) or "1=1"
        sql = f"""
        SELECT DISTINCT ai.aircraft_code, ai.publicity_name,
               at.manage_leader, at.manage_leader_phone,
               at.overall_contact, at.overall_contact_phone,
               at.center_contact, at.center_contact_phone
        FROM aircraft_info ai
        LEFT JOIN aircraft_team at ON at.aircraft_id = ai.id
        WHERE {where}
        LIMIT 1000
        """
        res = db.db_read_query(sql, limit=1000, read_only=True)
        data = res.get("data", [])
        # 对关键中文字段做编码纠偏
        for row in data:
            if isinstance(row, dict):
                for k in ("publicity_name", "manage_leader", "overall_contact", "center_contact"):
                    if k in row:
                        row[k] = _fix_mojibake(row[k])
        # 统一返回结构
        return {
            "ok": bool(res.get("ok")),
            "answer": {"ok": bool(res.get("ok")), "data": data},
            "steps": [
                {"thought": "规则引擎：解析问题并生成 SQL", "action": "run_sql", "args": {"sql": sql}, "observation": {"ok": bool(res.get("ok")), "preview": data}}
            ],
            "known_tables": ["aircraft_info", "aircraft_team"],
        }
    # 默认回退：仅罗列表
    lt = db.db_list_tables()
    return {
        "ok": bool(lt.get("ok")),
        "answer": {"ok": bool(lt.get("ok")), "data": lt.get("tables", [])},
        "steps": [{"thought": "规则引擎：无法解析明确意图，返回所有表", "action": "list_tables", "args": {}, "observation": lt}],
        "known_tables": lt.get("tables", []),
    }

@app.post("/plan")
def plan(inp: In):
    # 若 DECIDER=simple，则走本地规则，不依赖外部 LLM
    if os.getenv("DECIDER", "simple").lower() == "simple":
        ret = simple_plan(inp.question)
        # 附带 thread_id 以便客户端复用会话语义
        ret["thread_id"] = inp.thread_id or str(uuid4())
        return ret

    # 为使用 LangGraph 的 MemorySaver（checkpointer）补充必需的 configurable.thread_id
    tid = inp.thread_id or str(uuid4())
    try:
        # 使用 invoke 直接获取最终状态，避免 stream 下事件聚合不完整导致的空 steps
        final = graph.invoke(
            {"question": inp.question, "done": False, "answer": None, "max_steps": 20},
            config={
                "configurable": {"thread_id": tid},
                "recursion_limit": 30
            }
        )
    except Exception as e:
        return {
            "ok": False,
            "error": f"planner_invoke_failed: {e}",
            "steps": [],
            "known_tables": [],
            "thread_id": tid,
        }

    # 兼容 Pydantic BaseModel（S）与 dict 两种返回
    try:
        if isinstance(final, S):
            final_obj = final.model_dump()
        elif isinstance(final, dict):
            final_obj = final
        else:
            final_obj = {}
    except Exception:
        final_obj = {}

    steps = final_obj.get("steps") or []
    answer = final_obj.get("answer")
    known_tables = final_obj.get("known_tables") or []

    ok_val = False
    if isinstance(answer, dict):
        ok_val = bool(answer.get("ok", False))
    elif steps:
        # 若无 answer，则尽量从最后一个步骤的 observation.ok 推断
        last_step = steps[-1]
        if isinstance(last_step, dict):
            last_obs = last_step.get("observation", {})
        else:
            # 处理 Step 对象（Pydantic BaseModel）
            last_obs = getattr(last_step, "observation", {})
        ok_val = bool(last_obs.get("ok", False) if isinstance(last_obs, dict) else False)

    return {
        "ok": ok_val,
        "answer": answer,
        "steps": steps,
        "known_tables": known_tables,
        "thread_id": tid,
    }

# ===== 数据库相关路由 =====
class DescribeIn(BaseModel):
    table: str

class ReadIn(BaseModel):
    sql: str
    limit: int | None = 1000
    read_only: bool | None = True

@app.post("/list_tables")
def list_tables():
    return db.db_list_tables()

@app.post("/describe_table")
def describe_table(inp: DescribeIn):
    return db.db_describe_table(inp.table)

@app.post("/read_query")
def read_query(inp: ReadIn):
    return db.db_read_query(inp.sql, limit=inp.limit or 1000, read_only=bool(inp.read_only))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 9621))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
