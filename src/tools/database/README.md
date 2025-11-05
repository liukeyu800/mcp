# 数据库工具包 (Database Tools)

## 📋 概述

数据库工具包是一个智能的数据库查询助手，能够理解自然语言查询并自动生成和执行SQL语句。该工具包采用模块化设计，提供了完整的数据库交互解决方案。

## 🏗️ 架构设计

```
database/
├── client.py              # 主协调器 - 统一入口
├── session_manager.py     # 会话管理 - 处理用户会话
├── execution_engine.py    # 执行引擎 - 任务规划与执行
├── action_executor.py     # 动作执行器 - 具体操作实现
├── query_strategy.py      # 查询策略 - 智能查询决策
├── knowledge_manager.py   # 知识管理 - 数据库结构学习
├── observation_processor.py # 观察处理器 - 结果分析处理
└── README.md              # 本文档
```

## 🚀 核心功能

### 1. 智能查询理解
- **自然语言处理**: 理解用户的自然语言查询需求
- **意图识别**: 自动识别查询类型（搜索、统计、分析等）
- **上下文理解**: 基于对话历史提供更准确的查询

### 2. 自动SQL生成
- **智能表选择**: 根据查询内容自动选择相关表
- **SQL优化**: 生成高效的SQL查询语句
- **错误处理**: 自动检测和修复SQL语法错误

### 3. 数据库结构学习
- **表结构发现**: 自动探索数据库表结构
- **关系识别**: 识别表之间的关联关系
- **知识积累**: 学习并记住数据库模式

### 4. 结果智能分析
- **数据解释**: 对查询结果进行智能解释
- **趋势分析**: 识别数据中的模式和趋势
- **可视化建议**: 提供数据可视化建议

## 📦 模块详解

### DatabaseMCPClient (主协调器)
**文件**: `client.py`
**职责**: 作为整个工具包的统一入口，协调各个模块的工作

**主要方法**:
```python
# 执行查询任务
async def plan_and_execute(question: str, max_steps: int = 10) -> dict

# 会话管理
def load_or_create_session(thread_id: str, question: str) -> AgentState
def save_session(state: AgentState) -> None
def delete_session(thread_id: str) -> None
```

### SessionManager (会话管理器)
**文件**: `session_manager.py`
**职责**: 管理用户会话，保持对话上下文

**核心功能**:
- 会话创建和加载
- 会话状态保存
- 会话历史管理
- 会话摘要生成

### ExecutionEngine (执行引擎)
**文件**: `execution_engine.py`
**职责**: 任务规划和执行控制

**核心功能**:
- 任务分解和规划
- 执行步骤控制
- 错误处理和重试
- 结果汇总和分析

### ActionExecutor (动作执行器)
**文件**: `action_executor.py`
**职责**: 执行具体的数据库操作

**支持的动作**:
- `list_tables`: 列出数据库中的所有表
- `search_tables`: 根据关键词搜索相关表
- `describe_table`: 获取表的详细结构信息
- `sample_rows`: 获取表的示例数据
- `run_sql`: 执行SQL查询
- `finish`: 完成任务并返回结果

### QueryStrategy (查询策略)
**文件**: `query_strategy.py`
**职责**: 智能查询决策和SQL生成

**核心功能**:
- 查询意图分析
- 表选择策略
- SQL语句生成
- 查询优化建议

### KnowledgeManager (知识管理器)
**文件**: `knowledge_manager.py`
**职责**: 管理数据库结构知识

**核心功能**:
- 表结构存储
- 关系映射管理
- 知识更新和维护
- 智能推荐

### ObservationProcessor (观察处理器)
**文件**: `observation_processor.py`
**职责**: 处理和分析查询结果

**核心功能**:
- 结果格式化
- 数据分析
- 错误诊断
- 建议生成

## 🔧 使用方法

### 基本使用

```python
from src.agent_mcp.tools.database.client import DatabaseMCPClient

# 创建客户端实例
client = DatabaseMCPClient()

# 执行查询
result = await client.plan_and_execute(
    question="查找销售额最高的前10个产品",
    max_steps=10
)

print(result)
```

### 会话管理

```python
# 创建或加载会话
state = client.load_or_create_session(
    thread_id="user_123",
    question="分析用户行为数据"
)

# 执行查询
result = await client.plan_and_execute(
    question="显示最活跃的用户",
    max_steps=10
)

# 保存会话
client.save_session(state)
```

### 高级配置

```python
# 自定义配置
client = DatabaseMCPClient()

# 设置最大执行步数
result = await client.plan_and_execute(
    question="复杂的数据分析任务",
    max_steps=20  # 允许更多步骤
)
```

## 📊 工作流程

1. **接收查询**: 用户提供自然语言查询
2. **会话管理**: 加载或创建用户会话
3. **任务规划**: 分析查询并制定执行计划
4. **表发现**: 自动发现相关数据库表
5. **SQL生成**: 根据需求生成SQL查询
6. **执行查询**: 执行SQL并获取结果
7. **结果分析**: 分析和解释查询结果
8. **知识更新**: 更新数据库结构知识
9. **返回结果**: 提供格式化的最终答案

## 🎯 特色功能

### 智能表发现
- 根据查询内容自动识别相关表
- 支持模糊匹配和语义搜索
- 学习用户查询模式

### 自适应查询
- 根据数据库结构调整查询策略
- 自动处理表关联和连接
- 优化查询性能

### 错误恢复
- 自动检测SQL错误
- 提供修复建议
- 支持查询重试

### 上下文感知
- 记住之前的查询历史
- 理解对话上下文
- 提供相关建议

## 🔍 示例场景

### 场景1: 销售数据分析
```
用户: "查看上个月销售额最高的产品"
系统: 
1. 发现sales表和products表
2. 生成关联查询SQL
3. 执行查询并分析结果
4. 返回格式化的销售报告
```

### 场景2: 用户行为分析
```
用户: "分析用户的购买行为模式"
系统:
1. 识别users、orders、products表
2. 生成复杂的分析查询
3. 计算统计指标
4. 提供行为洞察报告
```

### 场景3: 数据质量检查
```
用户: "检查数据中是否有异常值"
系统:
1. 扫描相关表结构
2. 生成数据质量检查SQL
3. 识别异常数据
4. 提供数据清理建议
```

## 🛠️ 配置选项

### 环境变量
```bash
# 数据库连接配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password

# 工具配置
MAX_EXECUTION_STEPS=10
ENABLE_QUERY_CACHE=true
LOG_LEVEL=INFO
```

### 配置文件
```python
# config.py
DATABASE_CONFIG = {
    "max_steps": 10,
    "enable_cache": True,
    "timeout": 30,
    "retry_count": 3
}
```

## 🧪 测试

运行测试套件:
```bash
# 完整集成测试
python -m pytest tests/ -v

# 运行数据库工具相关测试
python -m pytest tests/test_database_tools.py -v

# 运行特定测试类
python -m pytest tests/test_database_tools.py::TestDatabaseMCPClient -v
```

## 📈 性能优化

### 查询优化
- 智能索引建议
- 查询计划分析
- 缓存机制

### 内存管理
- 结果集分页
- 连接池管理
- 资源自动释放

### 并发处理
- 异步查询执行
- 连接复用
- 负载均衡

## 🔒 安全特性

### SQL注入防护
- 参数化查询
- 输入验证
- 权限检查

### 访问控制
- 用户认证
- 操作授权
- 审计日志

## 🚀 扩展开发

### 添加新动作
```python
# 在action_executor.py中添加新动作
async def execute_custom_action(self, args: dict) -> dict:
    # 实现自定义逻辑
    pass
```

### 自定义策略
```python
# 在query_strategy.py中扩展策略
def custom_query_strategy(self, context: dict) -> str:
    # 实现自定义查询策略
    pass
```

## 📞 支持与反馈

如有问题或建议，请联系开发团队或提交Issue。

---

**版本**: 2.0.0  
**最后更新**: 2024年1月  
**维护者**: 数据库工具开发团队