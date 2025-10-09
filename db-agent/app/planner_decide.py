# app/planner_decide.py
import os, json, requests
from typing import Dict, Any
from .prompts import SYSTEM, DEVELOPER
from .memory import summarize_context

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _safe_json_loads(txt: str) -> Dict[str, Any]:
    # 尽力从模型输出中提取 JSON（防万一模型输出夹杂解释）
    txt = txt.strip()
    # 最理想：原生 JSON
    try:
        return json.loads(txt)
    except Exception:
        pass
    # 兜底：尝试截取第一个 {...} 区间
    start = txt.find("{")
    end = txt.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(txt[start:end+1])
        except Exception:
            pass
    # 再兜底：返回一个无动作的错误对象
    return {"thought": "解析失败，请求重试", "action": "list_tables", "args": {}}


def _post_noenv(url: str, **kwargs):
    """使用 requests.Session 且禁用系统代理 (trust_env=False)，避免走 127.0.0.1:7890 等代理。"""
    s = requests.Session()
    s.trust_env = False
    return s.post(url, **kwargs)


def _chat_content(messages, temperature: float = 0.2) -> str:
    """根据 LLM_PROVIDER 发送请求，返回模型的 content 字符串。完全禁用系统代理。"""
    if LLM_PROVIDER == "ollama":
        url = f"{OLLAMA_BASE}/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }
        resp = _post_noenv(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # 常见返回：{"message": {"role":"assistant","content":"..."}, ...}
        if isinstance(data, dict):
            if isinstance(data.get("message"), dict) and "content" in data["message"]:
                return data["message"]["content"]
            # 某些实现可能直接返回 content
            if "content" in data:
                return data["content"]
        # 兜底
        return "{}"
    else:
        resp = _post_noenv(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_MODEL,
                "temperature": temperature,
                "messages": messages,
                "response_format": {"type": "json_object"}
            },
            timeout=60
        ).json()
        return resp["choices"][0]["message"]["content"]


def llm_decide_with_memory(state) -> Dict[str, Any]:
    """
    把“知识提示（已知表/列/最近探查与错误）”插入上下文，
    让模型基于累计证据规划下一步动作（真正对标 Cherry 的“记住历史再思考”）。
    """
    memory_snippet = summarize_context(state)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "system", "content": f"知识提示（供你复用，不要逐字输出）：\n{memory_snippet}"},
        {"role": "system", "content": DEVELOPER},
        {"role": "user", "content": state.question}
    ]

    content = _chat_content(messages, temperature=0.2)
    return _safe_json_loads(content)
