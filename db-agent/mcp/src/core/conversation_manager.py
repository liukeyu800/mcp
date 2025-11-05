"""统一对话管理器 - 整合MCP工具调用、ReAct架构、会话历史等所有功能"""

import json
import sqlite3
import threading
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass
from uuid import uuid4

from .schemas import AgentState, Step
from .mcp_tool_registry import MCPToolRegistry
from .conversation_coordinator import ConversationCoordinator


@dataclass
class ConversationMetadata:
    """对话元数据"""
    thread_id: str
    user_id: str = "default"
    title: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    tool_categories: List[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tool_categories is None:
            self.tool_categories = []
        if self.tags is None:
            self.tags = []


class ConversationManager:
    """对话管理器 - 专注于会话数据持久化和管理"""
    
    def __init__(self, tool_registry: MCPToolRegistry, db_path: str = "conversations.db"):
        """
        初始化对话管理器
        
        Args:
            tool_registry: MCP工具注册中心
            db_path: 数据库路径
        """
        self.tool_registry = tool_registry
        self.db_path = db_path
        self._init_database()
        self._lock = threading.Lock()
        
        # 创建对话协调器（传递conversation_manager以便恢复历史状态）
        self.coordinator = ConversationCoordinator(tool_registry, conversation_manager=self)
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    thread_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    title TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    tool_categories TEXT,
                    tags TEXT,
                    state_data TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    step_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES conversations (thread_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                ON conversations (user_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_steps_thread_id 
                ON conversation_steps (thread_id)
            """)
    
    def create_conversation(self, thread_id: str, question: str, 
                          user_id: str = "default", 
                          tool_categories: List[str] = None,
                          max_steps: int = 12) -> AgentState:
        """创建新对话"""
        metadata = ConversationMetadata(
            thread_id=thread_id,
            user_id=user_id,
            title=question[:50] + "..." if len(question) > 50 else question,
            tool_categories=tool_categories or []
        )
        
        # 创建初始状态
        state = AgentState(
            question=question,
            max_steps=max_steps,
            steps=[],
            done=False,
            answer=None,
            known_tables=[],
            known_schemas={},
            candidate_tables=[],
            known_samples={},
            error_history=[],
            sql_history=[],
            last_error=None,
            messages=[],
            compressed_summary=None,
            compressed_message_count=0,
            compressed_config_hash=None
        )
        
        # 保存到数据库
        self.save_conversation(metadata, state)
        return state
    
    def save_conversation(self, metadata: ConversationMetadata, state: AgentState):
        """保存对话到数据库"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversations 
                    (thread_id, user_id, title, created_at, updated_at, tool_categories, tags, state_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.thread_id,
                    metadata.user_id,
                    metadata.title,
                    metadata.created_at.isoformat(),
                    metadata.updated_at.isoformat(),
                    json.dumps(metadata.tool_categories),
                    json.dumps(metadata.tags),
                    json.dumps(state.dict())
                ))
    
    def load_conversation(self, thread_id: str) -> Optional[AgentState]:
        """从数据库加载对话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT state_data FROM conversations WHERE thread_id = ?
            """, (thread_id,))
            
            row = cursor.fetchone()
            if row:
                state_data = json.loads(row[0])
                return AgentState(**state_data)
            return None
    
    def list_conversations(self, user_id: str = "default", 
                          tool_category: Optional[str] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """列出对话历史"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT thread_id, user_id, title, created_at, updated_at, tool_categories, tags
                FROM conversations 
                WHERE user_id = ?
            """
            params = [user_id]
            
            if tool_category:
                query += " AND tool_categories LIKE ?"
                params.append(f'%"{tool_category}"%')
            
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            conversations = []
            
            for row in cursor.fetchall():
                conversations.append({
                    "thread_id": row[0],
                    "user_id": row[1],
                    "title": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                    "tool_categories": json.loads(row[5] or "[]"),
                    "tags": json.loads(row[6] or "[]")
                })
            
            return conversations
    
    def delete_conversation(self, thread_id: str):
        """删除对话"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM conversation_steps WHERE thread_id = ?", (thread_id,))
                conn.execute("DELETE FROM conversations WHERE thread_id = ?", (thread_id,))
    
    def save_step(self, thread_id: str, step: Step):
        """保存对话步骤"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversation_steps (thread_id, step_index, step_data)
                    VALUES (?, ?, ?)
                """, (thread_id, step.step_index, json.dumps(step.dict())))
    
    
    
    async def run_conversation(self, user_input: str, session_id: str, max_steps: int = 12) -> Dict[str, Any]:
        """运行对话（非流式）- 委托给协调器"""
        return await self.coordinator.run_conversation(user_input, session_id, max_steps)
    
    async def run_conversation_stream(self, user_input: str, session_id: str, max_steps: int = 12, 
                                     continue_conversation: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """运行对话（流式输出）- 委托给协调器"""
        async for event in self.coordinator.run_conversation_stream(
            user_input, session_id, max_steps, continue_conversation=continue_conversation
        ):
            yield event


# 全局实例管理
_global_conversation_manager = None


def get_conversation_manager(tool_registry: MCPToolRegistry) -> ConversationManager:
    """获取全局对话管理器"""
    global _global_conversation_manager
    if _global_conversation_manager is None:
        _global_conversation_manager = ConversationManager(tool_registry)
    return _global_conversation_manager
