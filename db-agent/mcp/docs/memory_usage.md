# 记忆功能使用指南

## 概述

记忆功能是数据库智能代理的核心组件，它能够在对话过程中自动积累和管理数据库探索的知识，包括表结构、查询历史和操作轨迹。这使得代理能够在多轮对话中保持上下文，提供更智能的数据库交互体验。

## 核心组件

### 1. MemoryManager (记忆管理器)
负责生成和管理记忆摘要，将复杂的对话历史压缩为简洁的上下文信息。

**主要功能：**
- `summarize_context()`: 生成记忆摘要
- `update_knowledge_cache()`: 更新知识缓存

### 2. ConversationManager (对话管理器)
管理对话状态的持久化，支持跨会话的记忆保存和加载。

**主要功能：**
- `create_conversation()`: 创建新对话
- `save_conversation()`: 保存对话状态
- `load_conversation()`: 加载对话状态

### 3. AgentState (代理状态)
存储对话过程中积累的所有知识和状态信息。

**关键字段：**
- `known_tables`: 已知表列表
- `known_schemas`: 表结构信息
- `sql_history`: SQL执行历史
- `steps`: 操作步骤历史

## 使用方法

### 基本初始化

```python
from src.core.memory import MemoryManager
from src.core.conversation_manager import ConversationManager
from src.core.schemas import AgentState

# 初始化组件
memory_manager = MemoryManager()
conversation_manager = ConversationManager()

# 创建新对话
thread_id = conversation_manager.create_conversation(
    question="探索数据库结构",
    initial_state=AgentState()
)
```

### 知识缓存更新

记忆系统会自动根据执行的步骤更新知识缓存：

```python
from src.core.schemas import Step

# 创建步骤
step = Step(
    action="describe_table",
    args={"table_name": "aircraft_info"},
    observation={
        "ok": True,
        "columns": ["id", "name", "type"],
        "table_name": "aircraft_info"
    }
)

# 自动更新知识缓存
memory_manager.update_knowledge_cache(state, step)
```

### 记忆摘要生成

```python
# 生成记忆摘要
memory_summary = memory_manager.summarize_context(
    known_tables=state.known_tables,
    known_schemas=state.known_schemas,
    recent_steps=state.steps[-5:]  # 最近5个步骤
)

print(f"记忆摘要长度: {len(memory_summary)} 字符")
```

### 对话状态管理

```python
# 保存对话状态
conversation_manager.save_conversation(thread_id, state)

# 加载对话状态
loaded_state = conversation_manager.load_conversation(thread_id)
```

## 支持的操作类型

记忆系统会自动识别并处理以下操作类型：

### 1. 表发现操作
- `list_tables`: 列出所有表
- `search_tables`: 搜索表

**自动更新：** `state.known_tables`

### 2. 表结构探索
- `describe_table`: 获取表结构

**自动更新：** `state.known_schemas`

### 3. 数据采样
- `sample_rows`: 获取表样本数据

**自动更新：** `state.known_samples`

### 4. SQL执行
- `run_sql`: 执行SQL查询

**自动更新：** `state.sql_history`

## 记忆摘要格式

记忆摘要包含以下信息：

```
已知表名: table1, table2, table3 (截断至前10个)

已知表结构:
- table1: column1, column2, column3 (截断至前5列)
- table2: column1, column2 (截断至前5列)

最近操作轨迹:
1. 操作类型: 观察结果摘要
2. 操作类型: 观察结果摘要
```

## 最佳实践

### 1. 定期保存状态
在重要操作后及时保存对话状态：

```python
# 在关键步骤后保存
state.steps.append(step)
memory_manager.update_knowledge_cache(state, step)
conversation_manager.save_conversation(thread_id, state)
```

### 2. 合理使用记忆摘要
在生成系统提示时包含记忆摘要：

```python
if state.steps:
    memory_summary = memory_manager.summarize_context(
        known_tables=state.known_tables,
        known_schemas=state.known_schemas,
        recent_steps=state.steps[-5:]
    )
    system_prompt += f"\n\n## 记忆摘要\n{memory_summary}"
```

### 3. 错误处理
确保只有成功的操作才更新缓存：

```python
if step.observation and step.observation.get('ok'):
    memory_manager.update_knowledge_cache(state, step)
```

## 配置选项

### 记忆摘要长度控制
- 表名截断：前10个表
- 列名截断：每表前5列
- 步骤截断：最近5个步骤

### 数据库配置
记忆数据存储在SQLite数据库中：
- 文件位置：`conversations.db`
- 表结构：`conversations` 表

## 故障排除

### 常见问题

1. **记忆摘要为空**
   - 检查 `state.known_tables` 是否有数据
   - 确认步骤的 `observation.ok` 为 True

2. **表结构未保存**
   - 验证步骤的 `action` 为 "describe_table"
   - 检查 `args` 中是否包含正确的表名参数

3. **对话状态加载失败**
   - 确认 `thread_id` 存在
   - 检查数据库连接状态

### 调试工具

使用提供的调试脚本进行问题诊断：

```bash
# 基础功能测试
python debug_memory.py

# 端到端测试
python test_memory_e2e.py
```

## 性能考虑

- 记忆摘要会自动截断以控制长度
- 建议定期清理过期的对话记录
- 大量表结构信息可能影响摘要生成性能

## 扩展功能

记忆系统支持扩展以下功能：
- 自定义摘要格式
- 智能知识过期机制
- 跨用户记忆共享
- 记忆内容搜索和检索