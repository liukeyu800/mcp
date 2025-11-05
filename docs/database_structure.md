# 数据库结构设计文档

## 概述

使用 SQLite 数据库，默认文件：`conversations.db`

## 数据库表结构

### 1. `conversations` 表（主表）

存储会话元数据和完整状态：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `thread_id` | TEXT PRIMARY KEY | 会话唯一标识符（UUID） | `"ed51f46b-9a38-4b4a-8dad-dd4134b53309"` |
| `user_id` | TEXT NOT NULL | 用户ID（默认'default'） | `"default"` |
| `title` | TEXT | 会话标题（问题前50字符） | `"运载火箭有哪些？"` |
| `created_at` | TIMESTAMP | 创建时间 | `"2024-01-01T10:00:00"` |
| `updated_at` | TIMESTAMP | 最后更新时间 | `"2024-01-01T10:05:00"` |
| `tool_categories` | TEXT | 工具分类列表（JSON字符串） | `'["database"]'` |
| `tags` | TEXT | 标签列表（JSON字符串） | `'[]'` |
| `state_data` | TEXT | **完整的会话状态（JSON字符串）** | 见下方详细说明 |

**索引：**
- `idx_conversations_user_id`：按 `user_id` 查询

### 2. `conversation_steps` 表（步骤历史表 - 可选）

存储每个会话的详细步骤（当前未使用，保留用于未来扩展）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| `thread_id` | TEXT NOT NULL | 外键，关联到 `conversations.thread_id` |
| `step_index` | INTEGER NOT NULL | 步骤索引 |
| `step_data` | TEXT NOT NULL | 步骤数据（JSON字符串） |
| `created_at` | TIMESTAMP | 创建时间（默认当前时间） |

**索引：**
- `idx_conversation_steps_thread_id`：按 `thread_id` 查询

**外键约束：**
- `FOREIGN KEY (thread_id) REFERENCES conversations (thread_id)`

---

## `state_data` 字段详细结构

`state_data` 是一个 JSON 字符串，包含完整的 `AgentState` 对象。这是**核心存储结构**，所有状态信息都保存在这里。

### 保存流程

```
AgentState 对象
    ↓
state.dict()  → 转换为字典
    ↓
json.dumps()  → 序列化为JSON字符串
    ↓
保存到 conversations.state_data (TEXT字段)
```

### 数据结构

```json
{
  "question": "运载火箭有哪些？",
  
  "messages": [
    {"role": "user", "content": "运载火箭有哪些？"},
    {"role": "assistant", "content": "运载火箭包括：长征二号丁..."}
  ],
  
  "steps": [
    {
      "step_index": 0,
      "step_type": "action",
      "thought": "需要列出所有表",
      "action": "list_tables",
      "args": {},
      "observation": {"ok": true, "data": {"tables": [...]}},
      "content": "{...}",
      "timestamp": "2024-01-01T10:00:00"
    }
  ],
  
  "known_tables": ["aircraft_info", "aircraft_hardware", ...],
  
  "known_schemas": {
    "aircraft_info": {
      "columns": [
        {"name": "id", "type": "INTEGER", ...},
        {"name": "aircraft_name", "type": "VARCHAR", ...}
      ],
      "table_name": "aircraft_info"
    }
  },
  
  "candidate_tables": [],
  "known_samples": {},
  "error_history": [],
  
  "sql_history": [
    {
      "sql": "SELECT DISTINCT use_rocket FROM aircraft_info;",
      "result": {...},
      "timestamp": "2024-01-01T10:01:00"
    }
  ],
  
  "last_error": null,
  "done": true,
  "answer": {
    "ok": true,
    "data": "运载火箭包括：长征二号丁..."
  },
  "max_steps": 12,
  
  "compressed_summary": "**之前的用户问题**: 2个问题\n- 运载火箭有哪些？\n...",
  "compressed_message_count": 15,
  "compressed_config_hash": "abc123..."
}
```

### 字段说明

| 字段 | 类型 | 说明 | 保存位置 |
|------|------|------|----------|
| `question` | string | 原始问题 | `state_data` JSON |
| `messages` | array | **完整的对话消息列表**（用于前端展示） | `state_data` JSON |
| `steps` | array | ReAct执行步骤历史 | `state_data` JSON |
| `known_tables` | array | 已探索的表名列表 | `state_data` JSON |
| `known_schemas` | object | 表结构信息 | `state_data` JSON |
| `sql_history` | array | SQL查询历史 | `state_data` JSON |
| `compressed_summary` | string/null | **压缩摘要（缓存）** | `state_data` JSON |
| `compressed_message_count` | integer | 被压缩的消息数量 | `state_data` JSON |
| `compressed_config_hash` | string/null | 压缩配置哈希值 | `state_data` JSON |

---

## 压缩对话记录的保存方式

### 关键设计

**压缩摘要没有单独的数据库表或字段**，而是**嵌入在 `state_data` JSON 中**。

### 保存流程

```
1. 执行对话时：
   ├─ 完整消息 → 保存到 state.messages[]
   └─ 压缩摘要 → 计算并保存到 state.compressed_summary

2. 保存到数据库：
   ├─ state.dict() → 整个AgentState转为字典
   ├─ json.dumps(state.dict()) → 序列化为JSON字符串
   └─ 保存到 conversations.state_data (TEXT字段)

3. 加载时：
   ├─ 从 state_data 读取JSON字符串
   ├─ json.loads() → 反序列化为字典
   ├─ AgentState(**state_data) → 重建AgentState对象
   └─ state.compressed_summary → 直接可用（无需重新计算）
```

### 为什么这样设计？

**优点：**
1. ✅ **简单统一**：所有状态一起保存和加载，原子操作
2. ✅ **数据一致性**：压缩摘要和完整消息始终同步
3. ✅ **无需额外查询**：一次查询获取所有信息
4. ✅ **易于维护**：状态管理集中，逻辑清晰

**缺点：**
1. ❌ **无法单独查询压缩摘要**：必须加载整个state
2. ❌ **state_data 可能很大**：包含完整消息和所有状态
3. ❌ **更新成本高**：每次更新都要替换整个state_data

### 当前实现

```python
# 保存时（conversation_manager.py:147）
json.dumps(state.dict())  # 包含 compressed_summary

# 加载时（conversation_manager.py:159）
state_data = json.loads(row[0])  # 从state_data读取
AgentState(**state_data)  # 重建对象，compressed_summary自动恢复
```

---

## 数据关系图

```
conversations (1) ──< (N) conversation_steps
    │
    └── state_data (JSON TEXT)
        ├── messages[] (完整消息列表 - 用于展示)
        ├── steps[] (步骤历史)
        ├── known_tables[] (已知表)
        ├── known_schemas{} (表结构)
        ├── sql_history[] (SQL历史)
        └── compressed_summary (压缩摘要缓存 - 用于LLM)
            ├── compressed_message_count
            └── compressed_config_hash
```

---

## 查询示例

### 查看所有对话

```sql
SELECT 
    thread_id, 
    title, 
    created_at, 
    updated_at,
    json_array_length(json_extract(state_data, '$.messages')) as message_count
FROM conversations 
ORDER BY updated_at DESC;
```

### 查看特定对话的压缩摘要

```sql
SELECT 
    thread_id,
    json_extract(state_data, '$.compressed_summary') as compressed_summary,
    json_extract(state_data, '$.compressed_message_count') as compressed_count
FROM conversations 
WHERE thread_id = 'ed51f46b-9a38-4b4a-8dad-dd4134b53309';
```

### 查看完整状态

```sql
SELECT state_data 
FROM conversations 
WHERE thread_id = 'ed51f46b-9a38-4b4a-8dad-dd4134b53309';
```

---

## 设计考虑

### 为什么不单独存储压缩消息？

1. **数据一致性**：压缩摘要依赖于完整消息，必须同步更新
2. **查询效率**：压缩摘要通常需要和完整消息一起使用
3. **简化设计**：避免维护两个数据源的一致性

### 如果未来需要优化？

可以考虑：
1. **分离存储**：将压缩消息单独存储到 `compressed_messages` 字段
2. **版本控制**：添加 `state_version` 字段，支持增量更新
3. **归档机制**：将旧消息归档到单独的表中

但对于当前需求，嵌入在 `state_data` 中已经足够。

