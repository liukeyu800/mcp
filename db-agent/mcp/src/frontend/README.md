# 前端对话界面API模块

## 概述

这个模块提供了专门用于前端对话界面的API接口，包括对话历史管理、对话ID获取、对话统计等功能。

## API接口列表

### 1. 对话管理接口

#### 获取对话列表
- **路径**: `GET /frontend/conversations`
- **参数**: 
  - `user_id` (可选): 用户ID，默认为 "default"
  - `limit` (可选): 返回数量限制，默认为 20
  - `offset` (可选): 偏移量，默认为 0
  - `search` (可选): 搜索关键词
- **响应**: 对话列表和总数

#### 获取对话详情
- **路径**: `GET /frontend/conversations/{thread_id}`
- **响应**: 包含对话元数据、消息列表和步骤详情

#### 创建新对话
- **路径**: `POST /frontend/conversations`
- **请求体**: 
  ```json
  {
    "question": "用户问题",
    "user_id": "用户ID（可选）",
    "title": "对话标题（可选）"
  }
  ```
- **响应**: 新创建的对话ID

#### 删除对话
- **路径**: `DELETE /frontend/conversations/{thread_id}`
- **响应**: 删除结果

#### 更新对话标题
- **路径**: `PUT /frontend/conversations/{thread_id}/title`
- **参数**: `title` - 新标题
- **响应**: 更新结果

### 2. 对话导出接口

#### 导出对话
- **路径**: `GET /frontend/conversations/{thread_id}/export`
- **参数**: 
  - `format` (可选): 导出格式，支持 "json" 和 "markdown"，默认为 "json"
- **响应**: 导出的对话数据

### 3. 统计信息接口

#### 获取对话统计
- **路径**: `GET /frontend/stats`
- **参数**: 
  - `user_id` (可选): 用户ID，默认为 "default"
- **响应**: 包含总对话数、工具使用统计、每日对话统计等信息

## 使用示例

### 获取对话列表
```bash
curl -X GET "http://localhost:9623/frontend/conversations?limit=10&offset=0"
```

### 创建新对话
```bash
curl -X POST "http://localhost:9623/frontend/conversations" \
  -H "Content-Type: application/json" \
  -d '{"question":"我的数据库中有哪些表？","user_id":"test_user"}'
```

### 获取对话详情
```bash
curl -X GET "http://localhost:9623/frontend/conversations/{thread_id}"
```

### 导出对话为Markdown
```bash
curl -X GET "http://localhost:9623/frontend/conversations/{thread_id}/export?format=markdown"
```

## 数据模型

### ConversationListResponse
```json
{
  "conversations": [
    {
      "thread_id": "对话ID",
      "title": "对话标题",
      "created_at": "创建时间",
      "updated_at": "更新时间",
      "tool_categories": ["工具类别"],
      "tags": ["标签"],
      "user_id": "用户ID"
    }
  ],
  "total": 总数
}
```

### ConversationDetailResponse
```json
{
  "thread_id": "对话ID",
  "metadata": {
    "title": "对话标题",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "tool_categories": ["工具类别"],
    "tags": ["标签"],
    "user_id": "用户ID",
    "question": "初始问题",
    "done": false,
    "max_steps": 12
  },
  "messages": [
    {
      "role": "user|assistant|system",
      "content": "消息内容",
      "timestamp": "时间戳",
      "type": "消息类型",
      "step_index": "步骤索引（可选）"
    }
  ],
  "steps": [
    {
      "index": 步骤索引,
      "thought": "思考过程",
      "action": "执行动作",
      "args": {},
      "observation": "观察结果",
      "step_type": "步骤类型"
    }
  ]
}
```

## 集成说明

这个模块已经集成到主API服务器中，所有接口都以 `/frontend` 为前缀。前端应用可以直接调用这些接口来实现对话界面的功能。

## 注意事项

1. 所有接口都支持CORS，可以从前端直接调用
2. 对话ID使用UUID格式，确保唯一性
3. 时间戳使用ISO 8601格式
4. 支持分页查询，避免一次性加载过多数据
5. 提供搜索功能，方便用户查找历史对话