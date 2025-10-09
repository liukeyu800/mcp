from typing import Dict, Any, List
import json

def truncate_list(xs: List[str], n: int) -> List[str]:
    return xs[:n] if xs else []

def truncate_text(s: str, max_chars: int) -> str:
    if not s: return ""
    s = str(s)
    return s[:max_chars] + ("…" if len(s) > max_chars else "")

def summarize_context(state, *, 
                      max_tables:int=40, 
                      max_cols_per_table:int=12, 
                      max_preview_chars:int=400, 
                      max_steps:int=6) -> str:
    tables = truncate_list(sorted(set(getattr(state, "known_tables", []) or [])), max_tables)

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

    trail = []
    for s in (getattr(state, "steps", []) or [])[-max_steps:]:
        # 确保 s 是 Step 对象而不是字符串
        if isinstance(s, str):
            continue
        
        obs = getattr(s, "observation", {}) or {}
        trail.append({
            "thought": truncate_text(getattr(s, "thought", ""), 240),
            "action": getattr(s, "action", ""),
            "args": {k: truncate_text(v, 160) if isinstance(v, str) else v 
                     for k, v in (getattr(s, "args", {}) or {}).items()},
            "ok": bool(obs.get("ok") if isinstance(obs, dict) else False),
            "err": (obs.get("error") or {}).get("code") if isinstance(obs, dict) and obs.get("error") else None,
            "tables": obs.get("tables") if isinstance(obs, dict) else None,
            "matches": obs.get("matches") if isinstance(obs, dict) else None,
            "columns": obs.get("columns") if isinstance(obs, dict) else None,
            "preview": truncate_text(obs.get("preview"), max_preview_chars) if isinstance(obs, dict) and obs.get("preview") else None
        })

    last_err = getattr(state, "last_error", None)

    payload = {
        "known_tables": tables,
        "known_schemas": schemas,
        "recent_steps": trail,
        "last_error_code": last_err
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
