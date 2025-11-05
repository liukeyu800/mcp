# API模块说明

## 概述

这个目录包含了Database Agent的所有API模块，采用模块化设计，便于维护和扩展。

## 模块结构

```
api/
├── __init__.py          # 模块初始化，统一导出所有路由
├── database_api.py      # 数据库相关API
├── conversation_api.py  # 对话相关API
├── session_api.py       # 会话管理API
├── tool_api.py          # 工具相关API
├── demo_api.py          # 演示页面API
└── README.md           # 本文档
```

## 各模块功能

### 1. database_api.py
- **前缀**: `/database`
- **功能**: 数据库操作相关接口
- **主要端点**:
  - `GET /database/tables` - 列出所有表
  - `GET /database/tables/{table_name}/schema` - 获取表结构
  - `GET /database/tables/{table_name}/sample` - 获取示例数据
  - `POST /database/query` - 执行SQL查询
  - `GET /database/stats` - 获取数据库统计

### 2. conversation_api.py
- **前缀**: `/conversation`
- **功能**: 智能对话相关接口
- **主要端点**:
  - `POST /conversation/plan` - 规划并执行任务
  - `POST /conversation/plan/stream` - 流式执行计划

### 3. session_api.py
- **前缀**: `/sessions`
- **功能**: 会话管理相关接口
- **主要端点**:
  - `GET /sessions/` - 列出所有会话
  - `GET /sessions/{session_id}` - 获取会话详情
  - `DELETE /sessions/{session_id}` - 删除会话
  - `GET /sessions/{thread_id}/memory` - 获取线程记忆

### 4. tool_api.py
- **前缀**: `/tools`
- **功能**: 工具管理相关接口
- **主要端点**:
  - `GET /tools/` - 获取可用工具列表
  - `POST /tools/call` - 直接调用工具
  - `GET /tools/categories` - 获取工具分类

### 5. demo_api.py
- **前缀**: `/demo`
- **功能**: 演示页面
- **主要端点**:
  - `GET /demo/` - 演示页面HTML

## 使用方式

### 1. 统一启动
使用 `main.py` 启动所有模块：
```bash
python src/main.py
```

### 2. 单独导入
在其他项目中单独使用某个模块：
```python
from api.database_api import router as database_router
app.include_router(database_router)
```

### 3. 自定义配置
通过环境变量配置：
```bash
export API_HOST=0.0.0.0
export API_PORT=9623
```

## 设计原则

1. **模块化**: 每个功能模块独立，便于维护
2. **统一性**: 所有模块遵循相同的设计模式
3. **可扩展**: 新功能可以轻松添加新模块
4. **向后兼容**: 保持与原有API的兼容性
5. **文档化**: 每个模块都有清晰的文档说明

## 添加新模块

1. 在 `api/` 目录下创建新的模块文件
2. 定义 FastAPI 路由器
3. 在 `__init__.py` 中导出路由器
4. 在 `main.py` 中注册路由器
5. 更新本文档

## 注意事项

- 每个模块都应该有独立的依赖管理
- 避免模块间的循环依赖
- 保持API接口的一致性
- 添加适当的错误处理和日志记录