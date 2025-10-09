# Database Agent MCP Implementation

基于 Model Context Protocol (MCP) 的数据库智能体实现，提供与原 app 相同的功能，但采用更现代的 MCP 架构。

## 项目结构

```
mcp/
├── src/agent_mcp/
│   ├── core/                # 核心模块
│   │   ├── schemas.py       # 数据模型定义
│   │   └── __init__.py
│   ├── tools/               # 工具模块
│   │   └── database/        # 数据库工具包 (重构后)
│   │       ├── client.py              # 主协调器
│   │       ├── session_manager.py     # 会话管理
│   │       ├── execution_engine.py    # 执行引擎
│   │       ├── action_executor.py     # 动作执行器
│   │       ├── query_strategy.py      # 查询策略
│   │       ├── knowledge_manager.py   # 知识管理
│   │       ├── observation_processor.py # 观察处理器
│   │       └── README.md              # 数据库工具详细文档
│   ├── server.py            # MCP 服务器实现
│   ├── api.py               # FastAPI 接口
│   ├── memory.py            # 记忆管理
│   ├── guard.py             # SQL 安全验证
│   └── __init__.py
├── run_api.py               # 启动 API 服务器
├── run_server.py            # 启动 MCP 服务器
├── pyproject.toml           # 项目配置
└── README.md                # 本文档
```

## 核心特性

### 1. MCP 架构
- **服务器端**: 提供数据库操作工具 (list_tables, describe_table, run_sql, sample_rows)
- **客户端**: 实现 ReAct 规划和工具调用逻辑
- **协议**: 基于标准 MCP 协议进行通信

### 2. 模块化数据库工具包 (重构后)
- **主协调器 (client.py)**: 统一入口
- **会话管理器 (session_manager.py)**: 专门处理用户会话和状态管理
- **执行引擎 (execution_engine.py)**: 任务规划、执行控制和错误处理
- **动作执行器 (action_executor.py)**: 具体数据库操作的执行和验证
- **查询策略 (query_strategy.py)**: 智能查询决策和SQL生成
- **知识管理器 (knowledge_manager.py)**: 数据库结构学习和知识积累
- **观察处理器 (observation_processor.py)**: 结果分析和智能解释

### 3. 与原 app 兼容
- 提供相同的 `/plan` 接口
- 支持会话管理 (thread_id)
- 保持相同的响应格式
- 兼容原有的数据库接口

### 4. 安全机制
- SQL 注入防护
- 只读查询验证
- LIMIT 子句强制添加
- 危险操作黑名单

### 5. 智能特性
- **自然语言理解**: 理解用户的自然语言查询需求
- **自动表发现**: 根据查询内容自动识别相关表
- **智能SQL生成**: 生成优化的SQL查询语句
- **上下文感知**: 基于对话历史提供更准确的查询
- **错误自愈**: 自动检测和修复SQL语法错误

### 6. 记忆管理
- 会话状态持久化
- 知识缓存 (known_tables, known_schemas)
- 步骤历史记录
- 上下文摘要生成

## 安装和运行

### 1. 安装依赖

```bash
cd mcp
pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=sqlite:///path/to/your/database.db

# LLM 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4

# 服务配置
MCP_API_PORT=9623
```

### 3. 启动服务

#### 方式一：启动 FastAPI 接口 (推荐)

```bash
python run_api.py
```

访问 http://localhost:9623/docs 查看 API 文档

#### 方式二：分别启动服务器和客户端

```bash
# 终端1: 启动 MCP 服务器
python run_server.py

# 终端2: 使用客户端
python -c "
import asyncio
from src.db_agent_mcp.client import DatabaseMCPClient

async def test():
    client = DatabaseMCPClient()
    async with client.connect_to_server(['python', 'run_server.py']):
        result = await client.call_tool('list_tables', {})
        print(result)

asyncio.run(test())
"
```

## API 接口

### 主要接口

#### POST /plan
与原 app 兼容的规划接口

```json
{
  "question": "统计 user 表总数",
  "thread_id": "optional_session_id",
  "max_steps": 12
}
```

响应：
```json
{
  "ok": true,
  "answer": {"ok": true, "data": [{"total": 1000}]},
  "steps": [...],
  "known_tables": ["user", "order"],
  "thread_id": "session_id"
}
```

#### 会话管理
- `GET /sessions` - 列出所有会话
- `GET /sessions/{session_id}` - 获取会话详情
- `DELETE /sessions/{session_id}` - 删除会话

#### 数据库接口
- `POST /list_tables` - 列出所有表
- `POST /describe_table` - 描述表结构
- `POST /read_query` - 执行 SQL 查询

## 数据库工具包使用指南

### 快速开始

```python
from src.agent_mcp.tools.database.client import DatabaseMCPClient

# 创建数据库客户端
client = DatabaseMCPClient()

# 执行自然语言查询
result = await client.plan_and_execute(
    question="查找销售额最高的前10个产品",
    max_steps=10
)

print(result)
```

### 详细文档

数据库工具包的详细使用说明请参考：
📖 [数据库工具包详细文档](src/agent_mcp/tools/database/README.md)

该文档包含：
- 🏗️ 完整的架构设计说明
- 🚀 所有核心功能介绍
- 📦 各模块详细说明
- 🔧 使用方法和示例
- 🎯 特色功能展示
- 🧪 测试和配置指南

### 重构成果

经过模块化重构，数据库工具包现在具有：
- ✅ **代码精简**: client.py从382行减少到205行 (减少46%)
- ✅ **模块化设计**: 7个专用模块，各司其职
- ✅ **单一职责**: 每个模块只负责一个核心功能
- ✅ **易于扩展**: 新功能可以独立开发和测试
- ✅ **高可维护性**: 清晰的代码结构和接口设计

## 测试

### 运行测试
```bash
# 使用pytest运行测试套件
python -m pytest tests/ -v

# 或者运行特定的测试模块
python -m pytest tests/test_database_tools.py -v
```

测试内容包括：
1. MCP 客户端直接调用
2. FastAPI 接口测试
3. 与原 app 功能对比
4. 记忆管理器测试
5. 模块化组件测试
6. 重构后功能完整性验证

## MCP vs 原 app 对比

| 特性 | 原 app | MCP 实现 |
|------|--------|----------|
| 架构 | LangGraph + FastAPI | MCP Server + Client |
| 工具调用 | 内置函数 | MCP 协议 |
| 状态管理 | LangGraph MemorySaver | 自定义 MemoryManager |
| 扩展性 | 单体应用 | 分布式架构 |
| 协议标准 | 自定义 | 标准 MCP 协议 |
| 部署方式 | 单进程 | 多进程/分布式 |

## 优势

1. **标准化**: 基于 MCP 标准协议，更好的互操作性
2. **模块化**: 服务器和客户端分离，便于独立部署和扩展
3. **可扩展**: 易于添加新的工具和功能
4. **兼容性**: 保持与原 app 的 API 兼容
5. **安全性**: 继承原有的安全机制

## 开发指南

### 添加新工具

1. 在 `server.py` 中定义新工具
2. 在 `client.py` 中添加调用逻辑
3. 更新 `schemas.py` 中的动作类型

### 扩展记忆功能

1. 修改 `AgentState` 模型
2. 更新 `MemoryManager` 类
3. 调整上下文摘要逻辑

### 自定义安全策略

1. 修改 `guard.py` 中的正则表达式
2. 添加新的验证函数
3. 更新黑名单规则

## 故障排除

### 常见问题

1. **连接失败**: 检查 MCP 服务器是否正常启动
2. **数据库错误**: 验证 DATABASE_URL 配置
3. **LLM 调用失败**: 检查 API 密钥和网络连接
4. **权限错误**: 确保数据库文件可读写

### 调试模式

设置环境变量启用调试：

```bash
export DEBUG=1
python run_api.py
```

## 许可证

与原项目保持一致的许可证。

## 架构设计

- **MCP Server**: 提供数据库操作工具 (list_tables, describe_table, run_sql 等)
- **MCP Client**: 处理 ReAct 规划和工具调用逻辑
- **State Management**: 实现状态管理和记忆机制
- **FastAPI Interface**: 提供与原 app 相同的 `/plan` 端点

## 安装

```bash
cd mcp
pip install -e .
```

## 配置

复制 app 目录的 `.env` 文件到 mcp 目录：
```bash
cp ../app/.env .env
```

## 运行

启动 MCP 服务器：
```bash
db-agent-mcp-server
```

启动 FastAPI 接口：
```bash
uvicorn db_agent_mcp.api:app --host 0.0.0.0 --port 9623
```

## 特性

- ✅ 与原 app 相同的 ReAct 规划逻辑
- ✅ 智能表优先级排序
- ✅ 状态缓存和记忆机制
- ✅ SQL 安全守卫
- ✅ 错误处理和重试机制
- ✅ 中文编码修复
- ✅ 计数问题识别和优化