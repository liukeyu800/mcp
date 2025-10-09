"""统一对话历史管理器 - 支持跨工具类型的会话管理"""

import json
import sqlite3
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from .schemas import AgentState, Step


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
    """统一对话历史管理器"""
    
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_database()
    
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
                    tool_categories TEXT,  -- JSON array
                    tags TEXT,            -- JSON array
                    state_data TEXT       -- JSON serialized AgentState
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    step_data TEXT NOT NULL,  -- JSON serialized Step
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
        with self._lock:
            # 创建AgentState
            state = AgentState(
                question=question,
                max_steps=max_steps,
                steps=[],
                done=False
            )
            
            # 创建元数据
            metadata = ConversationMetadata(
                thread_id=thread_id,
                user_id=user_id,
                title=question[:50] + "..." if len(question) > 50 else question,
                tool_categories=tool_categories or []
            )
            
            # 保存到数据库
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversations 
                    (thread_id, user_id, title, created_at, updated_at, tool_categories, tags, state_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.thread_id,
                    metadata.user_id,
                    metadata.title,
                    metadata.created_at,
                    metadata.updated_at,
                    json.dumps(metadata.tool_categories),
                    json.dumps(metadata.tags),
                    json.dumps(state.dict())
                ))
            
            return state
    
    def load_conversation(self, thread_id: str) -> Optional[AgentState]:
        """加载对话状态"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT state_data FROM conversations WHERE thread_id = ?
                """, (thread_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                try:
                    state_dict = json.loads(row[0])
                    return AgentState(**state_dict)
                except Exception as e:
                    print(f"Error loading conversation {thread_id}: {e}")
                    return None
    
    def save_conversation(self, thread_id: str, state: AgentState, 
                         tool_categories: List[str] = None):
        """保存对话状态"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 更新主记录
                conn.execute("""
                    UPDATE conversations 
                    SET updated_at = ?, state_data = ?, tool_categories = ?
                    WHERE thread_id = ?
                """, (
                    datetime.now(),
                    json.dumps(state.dict()),
                    json.dumps(tool_categories or []),
                    thread_id
                ))
                
                # 保存新增的步骤
                existing_steps = conn.execute("""
                    SELECT COUNT(*) FROM conversation_steps WHERE thread_id = ?
                """, (thread_id,)).fetchone()[0]
                
                # 只保存新增的步骤
                new_steps = state.steps[existing_steps:]
                for i, step in enumerate(new_steps):
                    conn.execute("""
                        INSERT INTO conversation_steps 
                        (thread_id, step_index, step_data)
                        VALUES (?, ?, ?)
                    """, (
                        thread_id,
                        existing_steps + i,
                        json.dumps(step.dict())
                    ))
    
    def get_conversation_metadata(self, thread_id: str) -> Optional[ConversationMetadata]:
        """获取对话元数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT thread_id, user_id, title, created_at, updated_at, tool_categories, tags
                FROM conversations WHERE thread_id = ?
            """, (thread_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return ConversationMetadata(
                thread_id=row[0],
                user_id=row[1],
                title=row[2],
                created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                updated_at=datetime.fromisoformat(row[4]) if row[4] else None,
                tool_categories=json.loads(row[5]) if row[5] else [],
                tags=json.loads(row[6]) if row[6] else []
            )
    
    def list_conversations(self, user_id: str = "default", 
                          tool_category: str = None,
                          limit: int = 50) -> List[ConversationMetadata]:
        """列出对话"""
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
                conversations.append(ConversationMetadata(
                    thread_id=row[0],
                    user_id=row[1],
                    title=row[2],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    updated_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    tool_categories=json.loads(row[5]) if row[5] else [],
                    tags=json.loads(row[6]) if row[6] else []
                ))
            
            return conversations
    
    def delete_conversation(self, thread_id: str) -> bool:
        """删除对话"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 删除步骤
                conn.execute("DELETE FROM conversation_steps WHERE thread_id = ?", (thread_id,))
                
                # 删除主记录
                cursor = conn.execute("DELETE FROM conversations WHERE thread_id = ?", (thread_id,))
                
                return cursor.rowcount > 0
    
    def add_tags(self, thread_id: str, tags: List[str]):
        """添加标签"""
        metadata = self.get_conversation_metadata(thread_id)
        if metadata:
            existing_tags = set(metadata.tags)
            existing_tags.update(tags)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE conversations SET tags = ?, updated_at = ?
                    WHERE thread_id = ?
                """, (
                    json.dumps(list(existing_tags)),
                    datetime.now(),
                    thread_id
                ))
    
    def update_conversation_title(self, thread_id: str, title: str):
        """更新对话标题"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE conversations SET title = ?, updated_at = ?
                    WHERE thread_id = ?
                """, (title, datetime.now(), thread_id))
                
                return cursor.rowcount > 0
    
    def search_conversations(self, query: str, user_id: str = "default") -> List[ConversationMetadata]:
        """搜索对话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT thread_id, user_id, title, created_at, updated_at, tool_categories, tags
                FROM conversations 
                WHERE user_id = ? AND (title LIKE ? OR state_data LIKE ?)
                ORDER BY updated_at DESC
            """, (user_id, f"%{query}%", f"%{query}%"))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append(ConversationMetadata(
                    thread_id=row[0],
                    user_id=row[1],
                    title=row[2],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    updated_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    tool_categories=json.loads(row[5]) if row[5] else [],
                    tags=json.loads(row[6]) if row[6] else []
                ))
            
            return conversations
    
    def get_conversation_summary(self, thread_id: str) -> Dict[str, Any]:
        """获取对话摘要"""
        metadata = self.get_conversation_metadata(thread_id)
        state = self.load_conversation(thread_id)
        
        if not metadata or not state:
            return {}
        
        return {
            "thread_id": thread_id,
            "title": metadata.title,
            "question": state.question,
            "step_count": len(state.steps),
            "done": state.done,
            "tool_categories": metadata.tool_categories,
            "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
            "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
            "final_answer": state.answer.get("final") if state.answer else None
        }
    
    async def run_conversation(self, user_input: str, session_id: str, max_steps: int = 12) -> Dict[str, Any]:
        """运行对话（非流式）"""
        result = {"steps": [], "final_answer": "", "success": False}
        
        async for step_data in self.run_conversation_stream(user_input, session_id, max_steps):
            if step_data["type"] == "step":
                result["steps"].append(step_data["data"])
            elif step_data["type"] == "final":
                result["final_answer"] = step_data["data"]["answer"]
                result["success"] = step_data["data"]["success"]
        
        return result
    
    async def run_conversation_stream(self, user_input: str, session_id: str, max_steps: int = 12):
        """运行对话（流式输出）"""
        from .schemas import validate_flexible_decide, get_flexible_system_prompt
        import json
        import os
        import requests
        
        # 加载或创建对话状态
        state = self.load_conversation(session_id)
        if state is None:
            state = self.create_conversation(session_id, user_input, max_steps=max_steps)

        
        # 获取工具注册表
        tool_registry = getattr(self, 'tool_registry', None)
        if not tool_registry:
            yield {
                "type": "error",
                "data": {"error": "工具注册表未初始化"}
            }
            return
        
        # 获取可用工具
        available_tools = []
        for category in tool_registry.get_categories():
            provider = tool_registry.get_provider(category)
            if provider:
                for tool in provider.get_tools():
                    available_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    })
        
        step_count = 0
        while not state.done and step_count < max_steps:
            step_count += 1

            
            # 构建系统提示词
            system_prompt = get_flexible_system_prompt()
            
            # 构建对话历史
            messages = [{"role": "system", "content": system_prompt}]
            messages.append({"role": "user", "content": user_input})
            
            # 添加历史步骤（确保消息格式正确）
            for step in state.steps:
                if hasattr(step, 'thought') and step.thought:
                    # 添加assistant消息
                    assistant_content = {
                        "step_type": getattr(step, 'step_type', 'reasoning'),
                        "thought": step.thought,
                        "action": getattr(step, 'action', None),
                        "args": getattr(step, 'args', {})
                    }
                    messages.append({"role": "assistant", "content": json.dumps(assistant_content, ensure_ascii=False)})
                    
                    # 如果有observation，添加对应的user消息
                    if hasattr(step, 'observation') and step.observation:
                        messages.append({"role": "user", "content": f"观察结果: {json.dumps(step.observation, ensure_ascii=False)}"})
            
            # 如果最后一条消息是assistant消息且没有observation，添加一个继续的user消息
            if len(messages) > 2 and messages[-1]["role"] == "assistant":
                last_step = state.steps[-1] if state.steps else None
                if last_step and (not hasattr(last_step, 'observation') or not last_step.observation):
                    if getattr(last_step, 'step_type', '') == 'reasoning':
                        messages.append({"role": "user", "content": "请根据你的推理结果，执行下一步行动。"})
            
            try:
                # 调用LLM
                llm_response = await self._call_llm(messages)
                
                # 解析JSON响应
                if isinstance(llm_response, str):
                    # 提取第一个完整的JSON对象
                    content = llm_response.strip()
                    if '{' in content:
                        start_idx = content.find('{')
                        brace_count = 0
                        end_idx = start_idx
                        
                        # 找到第一个完整的JSON对象
                        for i in range(start_idx, len(content)):
                            if content[i] == '{':
                                brace_count += 1
                            elif content[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        json_content = content[start_idx:end_idx]
                        print(f"🔍 提取的JSON内容: {json_content}")
                        
                        try:
                            llm_response = json.loads(json_content)
                        except json.JSONDecodeError as e:
                            print(f"🔍 JSON解析失败: {e}")
                            # 如果解析失败，尝试修复常见问题
                            # 检查是否有多个JSON对象连在一起
                            if json_content.count('}{') > 0:
                                # 分割多个JSON对象，只取第一个
                                first_json = json_content.split('}{')[0] + '}'
                                print(f"🔍 修复后的JSON: {first_json}")
                                llm_response = json.loads(first_json)
                            else:
                                raise e
                    else:
                        llm_response = json.loads(llm_response)
                
                # 解析响应
                parsed = validate_flexible_decide(llm_response)
                
                # 创建步骤
                from .schemas import Step
                action = getattr(parsed, 'action', None)
                if action is None:
                    action = 'reasoning'  # 默认动作
                
                step = Step(
                    thought=parsed.thought,
                    action=action,
                    args=getattr(parsed, 'args', {}),
                    step_type=parsed.step_type
                )
                
                # 输出步骤信息
                step_data = {
                    "step_index": step_count,
                    "step_type": step.step_type,
                    "thought": step.thought,
                    "action": step.action,
                    "args": step.args
                }
                
                # 如果是finish步骤，添加answer和rationale
                if step.step_type == "finish":
                    step_data["answer"] = getattr(parsed, 'answer', None)
                    step_data["rationale"] = getattr(parsed, 'rationale', None)
                
                yield {
                    "type": "step",
                    "data": step_data
                }
                
                # 执行动作
                if step.action and step.action != "reasoning" and step.action != "finish":
                    try:
                        # 执行工具
                        observation = await tool_registry.execute_tool(step.action, **step.args)
                        step.observation = observation
                        
                        # 输出观察结果
                        yield {
                            "type": "observation",
                            "data": {
                                "step_index": step_count,
                                "action": step.action,
                                "observation": observation
                            }
                        }
                        
                    except Exception as e:
                        step.observation = {"ok": False, "error": str(e)}
                        yield {
                            "type": "observation",
                            "data": {
                                "step_index": step_count,
                                "action": step.action,
                                "observation": step.observation
                            }
                        }
                
                # 添加步骤到状态
                state.steps.append(step)
                
                # 检查是否完成
                if step.action == "finish" or step.step_type == "finish":
                    state.done = True
                    # 从finish步骤中提取answer，确保格式正确
                    if hasattr(parsed, 'answer') and parsed.answer:
                        state.answer = {"answer": parsed.answer, "rationale": getattr(parsed, 'rationale', '')}
                    else:
                        state.answer = {"answer": step.args.get("answer", "任务完成"), "rationale": step.args.get("rationale", "")}
                    
                    # 保存状态
                    self.save_conversation(session_id, state)
                    
                    # 输出最终结果
                    yield {
                        "type": "final",
                        "data": {
                            "answer": state.answer,
                            "success": True,
                            "total_steps": len(state.steps)
                        }
                    }
                    return
                
                # 如果是reasoning步骤，继续循环等待下一步action
                elif step.action == "reasoning" or step.step_type == "reasoning":
                    # 计算连续reasoning步骤数
                    reasoning_count = 0
                    for s in reversed(state.steps):
                        if s.action == "reasoning" or s.step_type == "reasoning":
                            reasoning_count += 1
                        else:
                            break
                    
                    # 如果连续reasoning超过3次，给出警告但继续
                    if reasoning_count >= 3:
                        yield {
                            "type": "warning",
                            "data": {
                                "message": "连续推理步骤较多，建议执行具体操作",
                                "reasoning_count": reasoning_count
                            }
                        }
                    
                    # 保存状态并继续循环
                    self.save_conversation(session_id, state)
                    continue
                
                # 保存中间状态
                self.save_conversation(session_id, state)
                
            except Exception as e:
                yield {
                    "type": "error",
                    "data": {
                        "step_index": step_count,
                        "error": str(e)
                    }
                }
                break
        
        # 如果达到最大步数
        if step_count >= max_steps:
            state.done = True
            state.answer = "达到最大步数限制"
            self.save_conversation(session_id, state)
            
            yield {
                "type": "final",
                "data": {
                    "answer": state.answer,
                    "success": False,
                    "total_steps": len(state.steps),
                    "reason": "max_steps_reached"
                }
            }
    
    async def _call_llm(self, messages):
        """调用LLM"""
        import os
        import requests
        
        # 获取LLM配置
        llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        
        if llm_provider == "ollama":
            url = f"{os.getenv('OLLAMA_BASE', 'http://localhost:11434')}/api/chat"
            payload = {
                "model": os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.2}
            }
            
            # 禁用代理
            session = requests.Session()
            session.trust_env = False
            
            print(f"🔍 调用LLM - URL: {url}")
            print(f"🔍 调用LLM - Payload: {payload}")
            
            response = session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            print(f"🔍 LLM响应: {data}")
            
            if isinstance(data, dict) and "message" in data:
                content = data["message"]["content"]
                print(f"🔍 提取的内容: {content}")
                return content
            print("🔍 未找到message字段，返回空JSON")
            return "{}"
        else:
            # OpenAI API
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                    "temperature": 0.2,
                    "messages": messages,
                    "response_format": {"type": "json_object"}
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


# 全局对话管理器实例
_global_conversation_manager = None


def get_conversation_manager() -> ConversationManager:
    """获取全局对话管理器"""
    global _global_conversation_manager
    if _global_conversation_manager is None:
        _global_conversation_manager = ConversationManager()
    return _global_conversation_manager