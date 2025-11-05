"""对话协调器 - 负责协调ReAct引擎和会话管理"""

import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from uuid import uuid4

from .schemas import AgentState, Step
from .react_engine import ReActEngine
from .mcp_tool_registry import MCPToolRegistry


class ConversationCoordinator:
    """对话协调器 - 协调ReAct推理和会话状态管理"""
    
    def __init__(self, tool_registry: MCPToolRegistry, conversation_manager=None):
        self.tool_registry = tool_registry
        self.react_engine = ReActEngine(tool_registry)
        self.conversation_manager = conversation_manager  # 用于加载历史状态
        
        # 消息压缩配置（可通过环境变量调整）
        import os
        self.message_compress_recent_window = int(os.getenv("MESSAGE_COMPRESS_RECENT_WINDOW", "10"))  # 保留最近N条完整消息
        self.message_compress_max_length = int(os.getenv("MESSAGE_COMPRESS_MAX_LENGTH", "5000"))  # 压缩后最大字符数
    
    async def run_conversation_stream(self, user_input: str, session_id: str, max_steps: int = 12, 
                                     continue_conversation: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """运行流式对话 - 使用ReAct架构
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            max_steps: 最大步数
            continue_conversation: 是否继续已有对话（从历史状态恢复）
        """
        
        print(f"[Conversation Coordinator] 开始运行对话流，用户输入: {user_input}, 会话ID: {session_id}, 继续对话: {continue_conversation}")
        
        # 尝试从历史状态恢复
        state = None
        messages = None
        
        if continue_conversation and self.conversation_manager:
            # 加载历史状态
            loaded_state = self.conversation_manager.load_conversation(session_id)
            if loaded_state:
                print(f"[Conversation Coordinator] 从历史状态恢复，已有 {len(loaded_state.steps)} 步")
                print(f"[Conversation Coordinator] 加载完整消息: {len(loaded_state.messages)} 条（压缩消息将在调用LLM时动态生成）")
                state = loaded_state
                state.max_steps = max_steps  # 更新最大步数
                # 重要：重置done状态，允许处理新问题
                state.done = False
                state.answer = None  # 清空之前的答案
                print(f"[Conversation Coordinator] 重置状态: done=False, 准备处理新问题")
                
                # 从历史消息恢复对话上下文
                # 构建包含已知表信息的系统消息
                messages = [self.react_engine.build_system_message(state=loaded_state)]
                if loaded_state.messages:
                    # 使用历史消息（跳过系统消息，因为我们已经添加了）
                    messages.extend(loaded_state.messages[1:] if loaded_state.messages[0].get("role") == "system" else loaded_state.messages)
                else:
                    # 如果没有保存的消息，从步骤中重建
                    messages.append({"role": "user", "content": loaded_state.question})
                    for step in loaded_state.steps:
                        if step.step_type == "reasoning":
                            messages.append({"role": "assistant", "content": f"思考: {step.thought}"})
                        elif step.step_type == "action":
                            messages.append({"role": "assistant", "content": f"行动: {step.thought}"})
                            if step.observation:
                                messages.append(self.react_engine.build_observation_message(
                                    step.action, step.observation
                                ))
                
                # 添加新的用户输入
                messages.append({"role": "user", "content": user_input})
        
        # 如果没有恢复状态，创建新状态
        if state is None:
            state = AgentState(
                question=user_input,
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
                messages=[],  # 初始化消息列表
                compressed_summary=None,  # 压缩摘要缓存
                compressed_message_count=0,  # 被压缩的消息数量
                compressed_config_hash=None  # 压缩配置哈希
            )
            
            # 构建初始消息
            messages = [
                self.react_engine.build_system_message(state=state),
                {"role": "user", "content": user_input}
            ]
        
        # 计算已执行步数
        # 重要：区分"继续之前的任务"和"在同一会话中问新问题"
        # 只有当用户明确说"继续"时，才使用历史步数；否则重置为0
        is_continue_request = any(keyword in user_input.lower() for keyword in 
                                  ["继续", "continue", "继续执行", "继续任务", "继续之前"])
        
        if continue_conversation and is_continue_request:
            # 继续之前的任务：使用历史步数
            initial_step_count = len(state.steps)
            print(f"[Conversation Coordinator] 继续之前的任务，保留历史步数: {initial_step_count}")
        else:
            # 新问题：重置步数，但保留历史上下文（已知表、消息等）
            initial_step_count = 0
            if continue_conversation:
                print(f"[Conversation Coordinator] 新问题，重置步数为0（但保留历史上下文）")
        
        step_count = initial_step_count
        print(f"[Conversation Coordinator] 进入主循环，最大步数: {max_steps}, 当前已执行步数: {step_count}")
        print(f"[Conversation Coordinator] 状态检查: done={state.done}, step_count={step_count}, max_steps={max_steps}")
        
        while not state.done and step_count < max_steps:
            step_count += 1
            print(f"[Conversation Coordinator] 执行第 {step_count} 步（总限制: {max_steps}）")
            
            # 发送思考信号
            yield {"type": "thinking", "data": {"step": step_count, "message": "正在思考..."}}
            
            try:
                # 执行ReAct步骤
                print(f"[Conversation Coordinator] 调用ReAct引擎...")
                # 压缩消息以避免上下文超限
                # 注意：messages列表保持完整用于保存，只压缩发送给LLM的版本
                compressed_messages = self._compress_messages_for_llm(
                    messages, state, 
                    recent_window=self.message_compress_recent_window,
                    max_compressed_length=self.message_compress_max_length
                )
                if len(messages) != len(compressed_messages):
                    print(f"[Conversation Coordinator] 消息压缩: {len(messages)} -> {len(compressed_messages)} 条（完整消息已保存用于展示）")
                react_result = await self.react_engine.execute_react_step(compressed_messages)
                print(f"[Conversation Coordinator] ReAct引擎返回结果类型: {react_result.get('type', 'unknown')}")
                
                # 处理不同类型的步骤结果
                if react_result["type"] == "reasoning":
                    step = self._create_step(len(state.steps), "reasoning", react_result["data"])
                    state.steps.append(step)
                    
                    yield {"type": "step", "data": {
                        "step_index": step.step_index,
                        "step_type": "reasoning",
                        "content": react_result["data"]["thought"]
                    }}
                    
                    # 添加助手消息到对话历史
                    messages.append({"role": "assistant", "content": f"思考: {react_result['data']['thought']}"})
                    # 更新状态的消息列表
                    state.messages = messages.copy()
                
                elif react_result["type"] == "action":
                    # 记录行动步骤
                    action_step = self._create_step(len(state.steps), "action", react_result["data"])
                    state.steps.append(action_step)
                    
                    yield {"type": "step", "data": {
                        "step_index": action_step.step_index,
                        "step_type": "action",
                        "content": f"调用工具: {react_result['data']['tool_name']}",
                        "tool_name": react_result["data"]["tool_name"],
                        "parameters": react_result["data"]["parameters"]
                    }}
                    
                    # 记录观察步骤
                    observation_step = self._create_step(len(state.steps), "observation", {
                        "tool_name": react_result["data"]["tool_name"],
                        "result": react_result["data"]["result"]
                    })
                    state.steps.append(observation_step)
                    
                    yield {"type": "step", "data": {
                        "step_index": observation_step.step_index,
                        "step_type": "observation",
                        "content": react_result["data"]["result"],
                        "tool_name": react_result["data"]["tool_name"]
                    }}
                    
                    # 添加消息到对话历史
                    messages.append({"role": "assistant", "content": f"行动: {react_result['data']['thought']}"})
                    messages.append(self.react_engine.build_observation_message(
                        react_result["data"]["tool_name"], 
                        react_result["data"]["result"]
                    ))
                    # 更新状态的消息列表
                    state.messages = messages.copy()
                
                elif react_result["type"] == "error":
                    error_step = self._create_step(len(state.steps), "error", react_result["data"])
                    state.steps.append(error_step)
                    
                    yield {"type": "step", "data": {
                        "step_index": error_step.step_index,
                        "step_type": "error",
                        "content": f"错误: {react_result['data']['error']}"
                    }}
                    
                    # 根据错误类型决定处理方式
                    error_type = react_result["data"].get("error_type", "unknown")
                    
                    if error_type == "json_parse_error":
                        # JSON解析错误：将错误信息和原始响应添加到对话历史，让LLM重新生成
                        # 检查是否连续多次JSON解析错误，避免无限重试
                        json_error_count = sum(1 for step in state.steps if step.step_type == "error" and "JSON解析" in str(step.observation))
                        if json_error_count >= 3:
                            # 连续3次JSON解析错误，直接结束对话并返回错误
                            state.done = True
                            error_msg = "抱歉，系统在处理您的请求时遇到了格式问题。请稍后重试或尝试重新表述您的问题。"
                            state.answer = {"ok": False, "data": error_msg}
                            messages.append({"role": "assistant", "content": error_msg})
                            state.messages = messages.copy()
                            yield {"type": "finish", "data": {
                                "answer": error_msg,
                                "total_steps": len(state.steps),
                                "state": state.dict()
                            }}
                            print(f"[Conversation Coordinator] 连续3次JSON解析错误，结束对话")
                            break
                        
                        raw_response = react_result["data"].get("raw_response", "")
                        error_message = f"""格式错误：你的响应不是有效的JSON格式。系统无法解析你的响应。

请严格按照系统提示词要求的JSON格式回复。你的响应必须是纯JSON对象，不能包含其他文本。

错误详情: {react_result['data']['error']}

你刚才的响应（前500字符）:
{raw_response[:500]}

请重新生成符合以下格式的JSON响应（注意：answer字段要简洁，不要复制工具原始数据）：
- 推理步骤: {{"thought": "...", "step_type": "reasoning", "analysis": "...", "plan": [...]}}
- 行动步骤: {{"thought": "...", "step_type": "action", "action": "...", "args": {{...}}}}
- 完成步骤: {{"thought": "...", "step_type": "finish", "answer": "简洁的用户友好回答", "rationale": "..."}}"""
                        
                        messages.append({"role": "user", "content": error_message})
                        print(f"[Conversation Coordinator] JSON解析错误（第{json_error_count + 1}次），已添加错误信息到对话历史，将在下一轮重试")
                    else:
                        # 工具执行错误等其他错误：正常处理
                        messages.append({"role": "user", "content": f"错误: {react_result['data']['error']}"})
                
                elif react_result["type"] == "finish":
                    # 完成对话
                    state.done = True
                    state.answer = {"ok": True, "data": react_result["data"]["answer"]}
                    # 添加最终答案到消息历史
                    messages.append({"role": "assistant", "content": react_result["data"]["answer"]})
                    state.messages = messages.copy()
                    
                    # 更新状态信息：从工具执行结果中提取表信息
                    self._update_state_from_steps(state)
                    
                    yield {"type": "finish", "data": {
                        "answer": react_result["data"]["answer"],
                        "total_steps": len(state.steps),
                        "state": state.dict()  # 返回完整状态
                    }}
                    break
                
            except Exception as e:
                print(f"[Conversation Coordinator] 异常发生: {type(e).__name__}: {e}")
                import traceback
                print(f"[Conversation Coordinator] 异常堆栈: {traceback.format_exc()}")
                
                yield {"type": "error", "data": {
                    "error": str(e),
                    "step": step_count
                }}
                break
        
        # 如果达到最大步数仍未完成，生成总结并询问是否继续
        if not state.done:
            print(f"[Conversation Coordinator] 达到最大步数限制，生成总结...")
            
            # 生成当前进度总结
            summary = await self._generate_progress_summary(state, messages)
            
            # 添加总结到消息历史
            pause_message = summary + "\n\n已达到最大步数限制。当前进度总结如上，您可以回复'继续'来继续执行，或提供新的指令。"
            messages.append({"role": "assistant", "content": pause_message})
            state.messages = messages.copy()
            
            # 返回暂停状态，询问用户是否继续（包含完整状态）
            yield {"type": "pause", "data": {
                "summary": summary,
                "total_steps": len(state.steps),
                "max_steps_reached": True,
                "thread_id": session_id,
                "message": "已达到最大步数限制。当前进度总结如上，您可以回复'继续'来继续执行，或提供新的指令。",
                "state": state.dict()  # 返回完整状态
            }}
        
        # 最后返回完整状态，确保所有信息都被保存
        yield {"type": "state_snapshot", "data": {
            "state": state.dict()
        }}
    
    async def run_conversation(self, user_input: str, session_id: str, max_steps: int = 12) -> Dict[str, Any]:
        """运行对话（非流式）"""
        print(f"[Conversation Coordinator] run_conversation 开始，用户输入: {user_input}")
        
        result = {
            "success": False,
            "final_answer": "",
            "steps": []
        }
        
        event_count = 0
        async for event in self.run_conversation_stream(user_input, session_id, max_steps):
            event_count += 1
            print(f"[Conversation Coordinator] 收到事件 {event_count}: {event['type']}")
            
            if event["type"] == "step":
                result["steps"].append(event["data"])
            elif event["type"] == "finish":
                result["success"] = True
                result["final_answer"] = event["data"].get("answer", "")
                break
            elif event["type"] == "error":
                result["error"] = event["data"]
                break
            elif event["type"] == "thinking":
                print(f"[Conversation Coordinator] 思考事件: {event['data']}")
        
        print(f"[Conversation Coordinator] run_conversation 完成，总事件数: {event_count}, 结果: {result}")
        return result
    
    async def _generate_progress_summary(self, state: AgentState, messages: List[Dict[str, str]]) -> str:
        """生成当前进度总结"""
        try:
            # 构建总结请求消息
            summary_messages = messages.copy()
            summary_messages.append({
                "role": "user",
                "content": """请总结当前任务的执行进度。包括：
1. 原始问题是什么
2. 已经完成了哪些步骤
3. 发现了哪些信息（表、字段、数据等）
4. 遇到了哪些问题或错误
5. 还需要完成什么才能回答原始问题

请用清晰的中文总结，帮助用户了解当前状态。"""
            })
            
            # 调用LLM生成总结
            llm_response = await self.react_engine._call_llm(summary_messages)
            
            # 提取总结内容（可能是纯文本或JSON）
            if isinstance(llm_response, str):
                # 尝试提取JSON格式的总结
                try:
                    import re
                    json_match = re.search(r'\{[^{}]*"summary"[^{}]*\}', llm_response, re.DOTALL)
                    if json_match:
                        summary_data = json.loads(json_match.group())
                        return summary_data.get("summary", llm_response)
                except:
                    pass
                return llm_response
            else:
                return str(llm_response)
        except Exception as e:
            print(f"[Conversation Coordinator] 生成总结失败: {e}")
            # 返回基本总结
            return f"""当前任务进度：

**原始问题**: {state.question}

**已执行步骤**: {len(state.steps)} 步

**已知信息**:
- 已知表: {', '.join(state.known_tables) if state.known_tables else '无'}
- 候选表: {', '.join(state.candidate_tables) if state.candidate_tables else '无'}
- 错误历史: {len(state.error_history)} 次错误
- SQL历史: {len(state.sql_history)} 次SQL查询

**状态**: 任务尚未完成，需要继续执行。"""
    
    def _update_state_from_steps(self, state: AgentState):
        """从执行步骤中更新状态信息（known_tables, known_schemas等）"""
        # 从步骤中提取表信息
        for step in state.steps:
            if step.step_type == "action":
                tool_name = step.action
                # 处理observation可能是字符串的情况
                if isinstance(step.observation, str):
                    try:
                        observation = json.loads(step.observation)
                    except:
                        observation = {}
                else:
                    observation = step.observation if isinstance(step.observation, dict) else {}
                
                # 处理list_tables结果
                if tool_name == "list_tables":
                    # 尝试多种格式
                    tables = None
                    if isinstance(observation, dict):
                        if "ok" in observation and "data" in observation:
                            tables = observation.get("data", {}).get("tables", [])
                        elif "tables" in observation:
                            tables = observation.get("tables", [])
                        elif "data" in observation and isinstance(observation["data"], list):
                            tables = observation["data"]
                    
                    if isinstance(tables, list):
                        for table_info in tables:
                            if isinstance(table_info, dict):
                                table_name = table_info.get("name") or table_info.get("table_name")
                            elif isinstance(table_info, str):
                                table_name = table_info
                            else:
                                continue
                            
                            if table_name and table_name not in state.known_tables:
                                state.known_tables.append(table_name)
                
                # 处理describe_table结果
                elif tool_name == "describe_table":
                    if isinstance(observation, dict):
                        # 尝试从不同格式中提取表名和结构
                        table_name = (observation.get("table_name") or 
                                     observation.get("data", {}).get("table_name") or
                                     step.args.get("table"))
                        if table_name:
                            if table_name not in state.known_tables:
                                state.known_tables.append(table_name)
                            
                            # 提取表结构
                            columns = (observation.get("columns") or 
                                      observation.get("data", {}).get("columns") or
                                      observation.get("data", {}).get("fields"))
                            if columns:
                                state.known_schemas[table_name] = {
                                    "columns": columns,
                                    "table_name": table_name
                                }
                
                # 处理sample_rows结果
                elif tool_name == "sample_rows":
                    table_name = step.args.get("table") or step.args.get("table_name")
                    if table_name:
                        if table_name not in state.known_tables:
                            state.known_tables.append(table_name)
                        # 保存样本数据
                        if observation and isinstance(observation, dict):
                            state.known_samples[table_name] = observation.get("data", observation)
                
                # 处理run_sql结果 - 记录SQL历史
                elif tool_name == "run_sql":
                    sql = step.args.get("sql") or ""
                    if sql:
                        state.sql_history.append({
                            "sql": sql,
                            "result": observation,
                            "timestamp": step.timestamp
                        })
            
            # 处理错误
            elif step.step_type == "error":
                error_info = step.content if isinstance(step.content, dict) else {"error": str(step.content)}
                state.error_history.append(error_info)
                state.last_error = error_info.get("error", str(error_info))
        
        print(f"[Conversation Coordinator] 状态更新完成: 已知表 {len(state.known_tables)} 个, 已知结构 {len(state.known_schemas)} 个")
    
    def _compress_messages_for_llm(self, full_messages: List[Dict[str, str]], state: AgentState, 
                                    recent_window: int = 10, max_compressed_length: int = 5000) -> List[Dict[str, str]]:
        """压缩消息列表以避免上下文超限（带缓存优化）
        
        Args:
            full_messages: 完整的消息列表
            state: 当前状态（用于提取关键信息）
            recent_window: 保留最近N条完整消息
            max_compressed_length: 压缩消息的最大字符长度
        
        Returns:
            压缩后的消息列表
        """
        if len(full_messages) <= recent_window:
            # 消息数量不多，直接返回
            return full_messages
        
        # 分离系统消息和用户/助手消息
        system_msg = full_messages[0] if full_messages and full_messages[0].get("role") == "system" else None
        conversation_messages = full_messages[1:] if system_msg else full_messages
        
        # 如果消息太多，压缩较早的消息
        if len(conversation_messages) > recent_window:
            # 保留最近的消息
            recent_messages = conversation_messages[-recent_window:]
            older_messages = conversation_messages[:-recent_window]
            
            # 检查是否可以使用缓存的压缩摘要
            config_hash = self._get_compress_config_hash(recent_window, max_compressed_length)
            can_use_cache = (
                state.compressed_summary is not None and
                state.compressed_message_count == len(older_messages) and
                state.compressed_config_hash == config_hash
            )
            
            if can_use_cache:
                # 使用缓存的压缩摘要
                compressed_summary = state.compressed_summary
                print(f"[Conversation Coordinator] 使用缓存的压缩摘要（{len(older_messages)}条消息）")
            else:
                # 重新计算压缩摘要
                compressed_summary = self._summarize_older_messages(older_messages, state)
                # 更新缓存
                state.compressed_summary = compressed_summary
                state.compressed_message_count = len(older_messages)
                state.compressed_config_hash = config_hash
                print(f"[Conversation Coordinator] 重新计算压缩摘要（{len(older_messages)}条消息）并缓存")
            
            # 构建压缩后的消息列表
            compressed = []
            if system_msg:
                compressed.append(system_msg)
            
            # 如果有摘要，添加摘要消息
            if compressed_summary:
                compressed.append({
                    "role": "system",
                    "content": f"## 历史对话摘要（已压缩{len(older_messages)}条消息）\n\n{compressed_summary}"
                })
            
            # 添加最近的消息
            compressed.extend(recent_messages)
            
            # 检查总长度，如果还是太长，进一步压缩observation消息
            total_length = sum(len(str(msg.get("content", ""))) for msg in compressed)
            if total_length > max_compressed_length:
                compressed = self._compress_observation_messages(compressed, max_compressed_length)
            
            return compressed
        
        # 如果消息不多，但总长度超限，压缩observation消息
        total_length = sum(len(str(msg.get("content", ""))) for msg in full_messages)
        if total_length > max_compressed_length:
            return self._compress_observation_messages(full_messages, max_compressed_length)
        
        return full_messages
    
    def _get_compress_config_hash(self, recent_window: int, max_compressed_length: int) -> str:
        """生成压缩配置的哈希值，用于判断是否需要重新压缩"""
        import hashlib
        config_str = f"{recent_window}_{max_compressed_length}"
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _summarize_older_messages(self, messages: List[Dict[str, str]], state: AgentState) -> str:
        """总结较早的消息
        
        Args:
            messages: 需要总结的消息列表
            state: 当前状态（用于提取关键信息）
        
        Returns:
            摘要文本
        """
        summary_parts = []
        
        # 提取关键信息
        user_questions = []
        key_actions = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user" and content:
                # 提取用户问题（非观察消息）
                if not content.startswith("观察:"):
                    user_questions.append(content[:100])  # 截断到100字符
            
            elif role == "assistant":
                # 提取助手的关键行动
                if "行动:" in content or "思考:" in content:
                    key_actions.append(content[:150])  # 截断到150字符
        
        # 构建摘要
        if user_questions:
            summary_parts.append(f"**之前的用户问题**: {len(user_questions)}个问题")
            if len(user_questions) <= 3:
                summary_parts.append("\n".join(f"- {q}" for q in user_questions))
            else:
                summary_parts.append(f"- {user_questions[0]}")
                summary_parts.append(f"- ... 还有{len(user_questions)-1}个问题")
        
        # 添加已知信息摘要
        if state.known_tables:
            summary_parts.append(f"\n**已知表**: {', '.join(state.known_tables[:10])}")
            if len(state.known_tables) > 10:
                summary_parts.append(f"(还有{len(state.known_tables)-10}个表)")
        
        if state.known_schemas:
            summary_parts.append(f"\n**已知表结构**: {len(state.known_schemas)}个表的结构已探索")
            for table_name in list(state.known_schemas.keys())[:3]:
                schema = state.known_schemas[table_name]
                columns = schema.get("columns", [])
                if columns:
                    col_names = [col.get("name", str(col)) if isinstance(col, dict) else str(col) for col in columns[:3]]
                    summary_parts.append(f"  - {table_name}: {', '.join(col_names)}...")
        
        if key_actions:
            summary_parts.append(f"\n**执行的操作**: {len(key_actions)}个关键步骤")
        
        return "\n".join(summary_parts) if summary_parts else "无重要历史信息"
    
    def _compress_observation_messages(self, messages: List[Dict[str, str]], max_length: int) -> List[Dict[str, str]]:
        """压缩observation消息（通常很长）
        
        Args:
            messages: 消息列表
            max_length: 目标最大总长度
        
        Returns:
            压缩后的消息列表
        """
        compressed = []
        current_length = 0
        
        for msg in messages:
            content = str(msg.get("content", ""))
            
            # 如果是observation消息且很长，压缩它
            if content.startswith("观察:") and len(content) > 500:
                try:
                    import json
                    # 尝试解析JSON
                    obs_json = json.loads(content.replace("观察:", "").strip())
                    if isinstance(obs_json, dict):
                        # 压缩观察结果
                        compressed_content = self._compress_observation(obs_json)
                        compressed.append({
                            "role": msg.get("role", "user"),
                            "content": f"观察: {compressed_content}"
                        })
                        current_length += len(compressed_content)
                    else:
                        # 如果不是JSON，直接截断
                        compressed.append({
                            "role": msg.get("role", "user"),
                            "content": content[:500] + "... (已截断)"
                        })
                        current_length += 500
                except:
                    # 解析失败，直接截断
                    compressed.append({
                        "role": msg.get("role", "user"),
                        "content": content[:500] + "... (已截断)"
                    })
                    current_length += 500
            else:
                # 非observation消息或已经很短，保留
                compressed.append(msg)
                current_length += len(content)
            
            # 如果已经超过限制，停止添加
            if current_length > max_length:
                break
        
        return compressed
    
    def _compress_observation(self, observation: Dict[str, Any], max_items: int = 10) -> str:
        """压缩单个观察结果
        
        Args:
            observation: 观察结果字典
            max_items: 最大保留项目数
        
        Returns:
            压缩后的JSON字符串
        """
        import json
        
        if not isinstance(observation, dict):
            return json.dumps(observation, ensure_ascii=False)
        
        compressed = {}
        
        # 保留关键字段
        if "ok" in observation:
            compressed["ok"] = observation["ok"]
        
        if "error" in observation:
            compressed["error"] = observation["error"]
        
        # 处理data字段
        if "data" in observation:
            data = observation["data"]
            if isinstance(data, list):
                # 列表：只保留前N项
                compressed["data"] = data[:max_items]
                if len(data) > max_items:
                    compressed["data_count"] = len(data)
                    compressed["data_truncated"] = True
            elif isinstance(data, dict):
                # 字典：保留关键字段
                compressed["data"] = {}
                for key in list(data.keys())[:max_items]:
                    value = data[key]
                    if isinstance(value, list) and len(value) > max_items:
                        compressed["data"][key] = value[:max_items]
                        compressed["data"][f"{key}_count"] = len(value)
                        compressed["data"][f"{key}_truncated"] = True
                    else:
                        compressed["data"][key] = value
            else:
                compressed["data"] = data
        
        return json.dumps(compressed, ensure_ascii=False)
    
    def _create_step(self, step_index: int, step_type: str, data: Dict[str, Any]) -> Step:
        """创建步骤对象"""
        # 处理observation字段 - 如果是字符串则解析为字典
        observation = data.get("result", {})
        if isinstance(observation, str):
            try:
                observation = json.loads(observation)
            except json.JSONDecodeError:
                # 如果无法解析，创建一个包含原始字符串的字典
                observation = {"raw": observation}
        
        return Step(
            step_index=step_index,
            step_type=step_type,
            content=json.dumps(data, ensure_ascii=False),
            timestamp=datetime.now().isoformat(),
            thought=data.get("thought", ""),
            action=data.get("tool_name", ""),
            args=data.get("parameters", {}),
            observation=observation
        )
