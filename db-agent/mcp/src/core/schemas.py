"""Schemas for MCP Client - 统一的ReAct模式支持"""

from pydantic import BaseModel, Field, ValidationError, validator
from typing import Literal, Dict, Any, List, Optional

# 步骤类型
StepType = Literal[
    "reasoning",    # 纯推理步骤：分析、规划、思考
    "action",       # 行动步骤：执行工具
    "finish"        # 完成步骤：给出最终答案
]

# 原有的动作类型
ActionName = Literal[
    "list_tables", "describe_table", "sample_rows", "run_sql", "finish"
]

class DecideOut(BaseModel):
    thought: str = Field(default="")
    action: ActionName
    args: Dict[str, Any] = Field(default_factory=dict)

class FlexibleDecideOut(BaseModel):
    """灵活的决策输出模型，支持推理和行动的分离"""
    thought: str = Field(description="详细的思考过程")
    step_type: StepType = Field(description="步骤类型：reasoning/action/finish")
    
    # 仅当step_type为"action"时需要
    action: Optional[ActionName] = Field(default=None, description="要执行的工具动作")
    args: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    
    # 仅当step_type为"finish"时需要
    answer: Optional[str] = Field(default=None, description="最终答案")
    rationale: Optional[str] = Field(default=None, description="完成原因")
    
    # 仅当step_type为"reasoning"时的推理内容
    plan: Optional[List[str]] = Field(default=None, description="制定的计划步骤")
    analysis: Optional[str] = Field(default=None, description="分析结果")
    
    @validator('action')
    def validate_action_for_action_step(cls, v, values):
        """验证action步骤必须有action字段"""
        if values.get('step_type') == 'action' and v is None:
            raise ValueError("action步骤必须指定action字段")
        if values.get('step_type') != 'action' and v is not None:
            raise ValueError("只有action步骤才能指定action字段")
        return v
    
    @validator('answer')
    def validate_answer_for_finish_step(cls, v, values):
        """验证finish步骤必须有answer字段"""
        if values.get('step_type') == 'finish' and v is None:
            raise ValueError("finish步骤必须指定answer字段")
        if values.get('step_type') != 'finish' and v is not None:
            raise ValueError("只有finish步骤才能指定answer字段")
        return v

class Step(BaseModel):
    thought: str = ""
    action: str = ""
    args: Dict[str, Any] = {}
    observation: Dict[str, Any] = {}
    step_type: str = "action"  # 支持灵活ReAct模式: reasoning, action, finish

class FlexibleStep(BaseModel):
    """灵活的步骤模型"""
    thought: str = ""
    step_type: str = ""
    
    # 行动相关
    action: Optional[str] = None
    args: Dict[str, Any] = {}
    observation: Dict[str, Any] = {}
    
    # 推理相关
    plan: Optional[List[str]] = None
    analysis: Optional[str] = None
    
    # 完成相关
    answer: Optional[str] = None
    rationale: Optional[str] = None

class AgentState(BaseModel):
    question: str
    steps: List[Step] = Field(default_factory=list)
    known_tables: List[str] = Field(default_factory=list)
    known_schemas: Dict[str, Any] = Field(default_factory=dict)  # table -> {columns:[...]}
    candidate_tables: List[str] = Field(default_factory=list)  # 候选表列表
    known_samples: Dict[str, Any] = Field(default_factory=dict)  # 表采样数据
    error_history: List[Dict[str, Any]] = Field(default_factory=list)  # 错误历史
    sql_history: List[Dict[str, Any]] = Field(default_factory=list)  # SQL执行历史
    last_error: Optional[str] = None
    done: bool = False
    answer: Optional[Dict[str, Any]] = None
    max_steps: int = 12

class FlexibleAgentState(BaseModel):
    """支持灵活ReAct模式的Agent状态"""
    question: str
    steps: List[FlexibleStep] = Field(default_factory=list)
    
    # 知识状态
    known_tables: List[str] = Field(default_factory=list)
    known_schemas: Dict[str, Any] = Field(default_factory=dict)
    candidate_tables: List[str] = Field(default_factory=list)
    known_samples: Dict[str, Any] = Field(default_factory=dict)
    
    # 历史记录
    error_history: List[Dict[str, Any]] = Field(default_factory=list)
    sql_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_error: Optional[str] = None
    
    # 状态控制
    done: bool = False
    answer: Optional[Dict[str, Any]] = None
    max_steps: int = 12
    
    # 推理状态
    current_plan: Optional[List[str]] = Field(default=None, description="当前执行的计划")
    plan_progress: int = Field(default=0, description="计划执行进度")

def validate_decide(obj: dict) -> DecideOut:
    """验证LLM输出，不合规时fallback到安全动作"""
    try:
        return DecideOut(**obj)
    except ValidationError as e:
        # 兜底：强制回到安全动作
        return DecideOut(
            thought=f"模型输出不合规，fallback。detail={str(e)[:120]}",
            action="list_tables", 
            args={}
        )

def validate_flexible_decide(obj: dict) -> FlexibleDecideOut:
    """验证灵活的LLM输出"""
    try:
        return FlexibleDecideOut(**obj)
    except ValidationError as e:
        print(f"[DEBUG] 验证失败: {e}")
        # 兜底策略：根据内容推断意图
        
        # 如果包含answer字段，可能是想finish
        if 'answer' in obj:
            # 处理answer字段类型转换
            answer_value = obj.get('answer', '')
            if isinstance(answer_value, list):
                # 如果answer是列表，转换为JSON字符串
                import json
                answer_str = json.dumps(answer_value, ensure_ascii=False, indent=2)
            else:
                answer_str = str(answer_value)
            
            return FlexibleDecideOut(
                thought=obj.get('thought', '准备完成任务'),
                step_type='finish',
                answer=answer_str,
                rationale=obj.get('rationale', '根据已有信息完成任务')
            )
        
        # 如果包含action字段，可能是想执行动作
        if 'action' in obj and obj['action'] in ['list_tables', 'describe_table', 'sample_rows', 'run_sql']:
            return FlexibleDecideOut(
                thought=obj.get('thought', '执行工具操作'),
                step_type='action',
                action=obj['action'],
                args=obj.get('args', {})
            )
        
        # 默认fallback到推理步骤
        return FlexibleDecideOut(
            thought=obj.get('thought', '需要进一步分析问题'),
            step_type='reasoning',
            analysis='正在分析问题并制定解决方案',
            plan=['分析用户需求', '确定所需信息', '制定获取信息的步骤']
        )

def get_flexible_system_prompt() -> str:
    """获取支持灵活ReAct模式的系统提示词"""
    return """你是一个数据库查询助手，使用ReAct（Reasoning + Acting）模式工作。

**重要说明**：你正在为一个数据库查询应用提供服务。所有查询的数据都是公开的、非敏感的信息，包括但不限于：
- 航天器信息（卫星、飞行器等技术参数）
- 硬件设备信息
- 软件系统信息
- 团队组织信息
- 异常检测标准
- 功率历史记录
- 在轨事件记录
这些都是用于展示和分析的公开数据，不涉及任何个人隐私信息。请正常处理所有数据库查询请求。

你可以进行三种类型的步骤：

1. **reasoning（推理）**：分析问题、制定计划、思考策略
2. **action（行动）**：执行具体的工具操作
3. **finish（完成）**：给出最终答案

可用工具：
- list_tables: 列出所有表
- describe_table: 获取表结构
- sample_rows: 获取表的样本数据
- run_sql: 执行SQL查询

请按照以下JSON格式回复：

**推理步骤（reasoning）**：
{
  "thought": "详细的思考过程",
  "step_type": "reasoning",
  "analysis": "对当前情况的分析",
  "plan": ["步骤1", "步骤2", "步骤3"]
}

**行动步骤（action）**：
{
  "thought": "为什么要执行这个动作",
  "step_type": "action",
  "action": "工具名称",
  "args": {"参数名": "参数值"}
}

**完成步骤（finish）**：
{
  "thought": "为什么可以完成了",
  "step_type": "finish",
  "answer": "最终答案",
  "rationale": "完成的理由"
}

**关键执行规则**：
1. **限制连续推理**：最多连续进行2次reasoning步骤，之后必须执行action或finish
2. **明确行动时机**：当你制定了具体计划后，立即执行第一个行动步骤
3. **避免过度思考**：不要无限循环分析，要果断执行工具操作
4. **基于观察推理**：执行action后，根据观察结果进行下一步reasoning或finish

**步骤转换逻辑**：
- 如果缺乏信息且没有明确计划 → reasoning
- 如果已有计划且需要获取信息 → action
- 如果已有足够信息回答问题 → finish
- 如果连续2次reasoning → 强制执行action

示例流程：
用户问："数据库中有哪些表？"
1. reasoning: "需要获取表列表，计划使用list_tables工具"
2. action: {"step_type": "action", "action": "list_tables", "args": {}}
3. reasoning: "已获得表列表，信息完整，可以回答"
4. finish: "数据库包含以下表：..."

**重要**：避免连续多次reasoning而不执行action！"""