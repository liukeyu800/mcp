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
    step_index: int = 0
    thought: str = ""
    action: str = ""
    args: Dict[str, Any] = {}
    observation: Dict[str, Any] = {}
    step_type: str = "action"  # 支持灵活ReAct模式: reasoning, action, finish
    content: str = ""
    timestamp: Optional[str] = None

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
    messages: List[Dict[str, str]] = Field(default_factory=list)  # 对话消息列表 [{"role": "user/assistant", "content": "..."}]
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
    # 压缩消息的缓存（避免每次重新计算）
    compressed_summary: Optional[str] = Field(default=None, description="历史消息的压缩摘要")
    compressed_message_count: int = Field(default=0, description="被压缩的消息数量")
    compressed_config_hash: Optional[str] = Field(default=None, description="压缩配置的哈希值（用于判断是否需要重新压缩）")

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

## ⚠️ 核心规则（必须严格遵守）

**规则1：何时必须查询实际数据？**
如果用户要求"举例"、"举例子"、"展示"、"列出"、"有哪些"、"包含哪些数据"、"具体数据"等，**必须**使用 `sample_rows` 或 `run_sql` 查询实际数据，**不能**仅基于表结构信息回答。

**规则2：finish的禁止条件**
- ❌ **禁止**在用户要求"举例"、"展示数据"时直接finish，必须先查询数据
- ❌ **禁止**仅基于表结构信息回答需要实际数据的问题
- ✅ 只有在**已执行查询工具并获取能够回答问题的实际数据后**才能finish

**规则3：表结构 ≠ 实际数据**
- `describe_table` 只能告诉你**表的结构**（有哪些字段），**不能**告诉你**具体的数据内容**
- 知道表结构 ≠ 知道数据内容，必须查询才能回答

## 可用工具

1. **list_tables**: 列出数据库中的所有表
2. **describe_table**: 获取指定表的结构信息（字段名、类型等）
3. **sample_rows**: 获取表的示例数据（**用于回答"举例"、"展示"等问题**）
4. **run_sql**: 执行SQL查询（**用于回答需要实际数据的问题**）

## ReAct工作模式

按照 **思考 → 行动 → 观察** 循环：
1. **思考**：分析用户问题，决定下一步行动
2. **行动**：调用合适的工具获取信息
3. **观察**：分析工具返回的结果
4. **重复**：直到能够回答用户问题

## 响应格式

请严格按照以下JSON格式回复：

### 推理步骤
```json
{
  "thought": "你的详细思考过程",
  "step_type": "reasoning",
  "analysis": "当前情况分析",
  "plan": ["计划步骤1", "计划步骤2"]
}
```

### 行动步骤
```json
{
  "thought": "为什么要执行这个工具",
  "step_type": "action", 
  "action": "工具名称",
  "args": {"参数名": "参数值"}
}
```

### 完成步骤（finish）
```json
{
  "thought": "为什么现在可以给出答案",
  "step_type": "finish",
  "answer": "简洁、用户友好的最终答案",
  "rationale": "完成的理由"
}
```

**finish的严格要求**：
- ✅ 必须**已执行查询工具**（sample_rows或run_sql）并获取实际数据后才能finish
- ✅ 回答必须简洁、用户友好，提取关键信息
- ❌ **禁止**在用户要求"举例"、"展示"时直接finish
- ❌ **禁止**仅基于表结构信息回答需要实际数据的问题

## 示例

**示例1：用户："aircraft_info表包含哪些字段？"**
- 步骤1：action → describe_table → 获取表结构
- 步骤2：finish → 基于表结构回答

**示例2：用户："里面都有那些卫星的信息，请你举几个例子"**
- 步骤1：action → sample_rows(table="aircraft_info", limit=5) → **必须查询实际数据**
- 步骤2：finish → 基于查询结果给出具体例子

**示例3：用户："有多少颗卫星？"**
- 步骤1：action → run_sql(sql="SELECT COUNT(*) FROM aircraft_info") → **必须查询**
- 步骤2：finish → 基于查询结果回答数量"""