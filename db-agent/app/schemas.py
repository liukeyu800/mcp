# app/schemas.py
from pydantic import BaseModel, Field, ValidationError
from typing import Literal, Dict, Any

ActionName = Literal[
    "list_tables","describe_table","sample_rows","run_sql","finish"
]

class DecideOut(BaseModel):
    thought: str = Field(default="")
    action: ActionName
    args: Dict[str, Any] = Field(default_factory=dict)

def validate_decide(obj: dict) -> DecideOut:
    try:
        return DecideOut(**obj)
    except ValidationError as e:
        # 兜底：强制回到安全动作
        return DecideOut(thought=f"模型输出不合规，fallback。detail={str(e)[:120]}",
                         action="list_tables", args={})
