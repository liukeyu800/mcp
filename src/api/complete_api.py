"""统一完整API - 整合所有功能：工具调用、对话管理、会话历史等"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import uuid4
import asyncio
import json

from ..core.mcp_tool_registry import MCPToolRegistry
from ..core.conversation_manager import ConversationManager, get_conversation_manager as core_get_conversation_manager
from ..tools.database.mcp_provider import register_database_mcp_tools


# 创建路由器
router = APIRouter(tags=["api"])

# 全局实例
_tool_registry = None
_conversation_manager = None


def get_tool_registry():
    """获取工具注册中心实例"""
    global _tool_registry
    if _tool_registry is None:
        # 这里需要一个MCP服务器实例，但在API中我们不实际运行服务器
        # 所以创建一个虚拟的服务器用于工具注册
        from mcp.server.fastmcp import FastMCP
        mcp_server = FastMCP("API Tool Registry")
        _tool_registry = MCPToolRegistry(mcp_server)
        
        # 注册数据库工具
        register_database_mcp_tools(_tool_registry)
        
        print(f"API工具注册系统已初始化，共 {len(_tool_registry.get_all_tools())} 个工具")
    
    return _tool_registry


def get_conversation_manager():
    """获取对话管理器实例"""
    global _conversation_manager
    if _conversation_manager is None:
        tool_registry = get_tool_registry()
        _conversation_manager = core_get_conversation_manager(tool_registry)
    return _conversation_manager


# ==================== 请求/响应模型 ====================

class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    tool_name: str
    parameters: Dict[str, Any] = {}


class ConversationRequest(BaseModel):
    """对话请求"""
    question: str
    thread_id: Optional[str] = None
    max_steps: Optional[int] = 12
    continue_conversation: Optional[bool] = False  # 是否继续已有对话


class ToolListResponse(BaseModel):
    """工具列表响应"""
    total_tools: int
    categories: List[str]
    tools: List[Dict[str, Any]]


# ==================== 工具相关API ====================

@router.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """获取所有可用工具列表"""
    registry = get_tool_registry()
    tools = registry.get_all_tools()
    
    tools_data = []
    for tool in tools:
        tools_data.append({
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameters": tool.parameters,
            "is_async": tool.is_async
        })
    
    return ToolListResponse(
        total_tools=len(tools),
        categories=registry.get_categories(),
        tools=tools_data
    )


@router.get("/tools/categories")
async def list_tool_categories():
    """获取工具类别"""
    registry = get_tool_registry()
    categories_info = {}
    
    for category in registry.get_categories():
        tools = registry.get_tools_by_category(category)
        categories_info[category] = {
            "count": len(tools),
            "tools": [{"name": tool.name, "description": tool.description} for tool in tools]
        }
    
    return categories_info


@router.get("/tools/{category}")
async def get_tools_by_category(category: str):
    """获取指定类别的工具"""
    registry = get_tool_registry()
    tools = registry.get_tools_by_category(category)
    
    if not tools:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    
    return {
        "category": category,
        "count": len(tools),
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "is_async": tool.is_async
            }
            for tool in tools
        ]
    }


@router.post("/tools/execute")
@router.post("/tools/call")  # 添加兼容路由
async def execute_tool(request: ToolExecuteRequest):
    """执行工具"""
    registry = get_tool_registry()
    tool = registry.get_tool(request.tool_name)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found")
    
    try:
        # 直接调用工具处理函数
        if tool.is_async:
            result = await tool.handler(**request.parameters)
        else:
            result = tool.handler(**request.parameters)
        
        # 如果结果是字符串（JSON格式），尝试解析
        if isinstance(result, str):
            try:
                parsed_result = json.loads(result)
                return {
                    "success": True,
                    "tool_name": request.tool_name,
                    "result": parsed_result
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "tool_name": request.tool_name,
                    "result": result
                }
        else:
            return {
                "success": True,
                "tool_name": request.tool_name,
                "result": result
            }
            
    except Exception as e:
        return {
            "success": False,
            "tool_name": request.tool_name,
            "error": {
                "code": "EXECUTION_ERROR",
                "message": str(e)
            }
        }


# ==================== 对话相关API ====================

@router.post("/conversation/plan")
async def plan_and_execute(request: ConversationRequest):
    """规划并执行任务（ReAct架构）"""
    
    # 生成线程ID
    thread_id = request.thread_id or str(uuid4())
    
    try:
        conversation_manager = get_conversation_manager()
        
        # 执行对话
        result = await conversation_manager.run_conversation(
            user_input=request.question,
            session_id=thread_id,
            max_steps=request.max_steps or 12
        )
        
        # 构建响应格式
        response = {
            "ok": True,
            "answer": {"ok": True, "data": result.get("final_answer", "")},
            "steps": result.get("steps", []),
            "known_tables": [],
            "known_schemas": {},
            "thread_id": thread_id,
            "status": "completed" if result.get("success", False) else "partial",
            "total_steps": len(result.get("steps", []))
        }
        
        return response
            
    except Exception as e:
        error_response = {
            "ok": False,
            "thread_id": thread_id,
            "question": request.question,
            "error": str(e),
            "status": "error",
            "answer": {"ok": False, "data": []},
            "steps": [],
            "known_tables": []
        }
        return error_response


@router.post("/conversation/plan/stream")
async def plan_stream(request: ConversationRequest):
    """流式执行计划，支持Server-Sent Events"""
    
    # 生成线程ID
    thread_id = request.thread_id or str(uuid4())
    
    async def generate_stream():
        # 用于收集对话状态
        collected_state = {
            "question": request.question,
            "steps": [],
            "answer": None,
            "done": False,
            "messages": []  # 收集完整的消息列表
        }
        
        try:
            conversation_manager = get_conversation_manager()
            
            # 检测用户是否要继续对话（输入"继续"、"continue"等）
            user_input_lower = request.question.strip().lower()
            is_continue = (user_input_lower in ["继续", "continue", "继续执行", "继续任务"] or 
                          request.continue_conversation)
            
            # 如果用户要继续，确保有thread_id
            if is_continue and not thread_id:
                # 尝试从最近的对话中获取thread_id（这里简化处理，实际可能需要更复杂的逻辑）
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': '无法继续：未指定thread_id'}}, ensure_ascii=False)}\n\n"
                return
            
            # ========== 关键修复：同一会话中自动恢复上下文 ==========
            # 如果提供了thread_id，尝试加载历史状态
            # 如果历史状态存在，说明这是同一会话的后续问题，应该恢复上下文
            should_continue = is_continue or request.continue_conversation
            if thread_id and not should_continue:
                # 检查是否存在历史状态
                existing_state = conversation_manager.load_conversation(thread_id)
                if existing_state and len(existing_state.messages) > 0:
                    # 存在历史状态，自动恢复上下文
                    should_continue = True
                    print(f"[API] 检测到历史状态，自动恢复上下文。已有 {len(existing_state.messages)} 条消息，{len(existing_state.steps)} 个步骤")
            
            # 发送初始化信息
            yield f"data: {json.dumps({'type': 'init', 'data': {'thread_id': thread_id, 'question': request.question}}, ensure_ascii=False)}\n\n"
            
            # 添加用户消息
            collected_state["messages"].append({
                "role": "user",
                "content": request.question
            })
            
            # 执行流式对话
            # 如果应该继续，使用continue_conversation=True来恢复历史上下文
            continue_flag = should_continue
            
            # 用于保存coordinator返回的完整状态
            final_state = None
            
            async for step_data in conversation_manager.run_conversation_stream(
                user_input=request.question if not is_continue else "继续执行之前的任务",
                session_id=thread_id,
                max_steps=request.max_steps or 12,
                continue_conversation=continue_flag
            ):
                # 收集步骤数据
                if step_data["type"] == "step":
                    collected_state["steps"].append(step_data["data"])
                elif step_data["type"] == "finish":
                    collected_state["done"] = True
                    collected_state["answer"] = step_data["data"].get("answer", "")
                    # 添加助手的最终回答
                    collected_state["messages"].append({
                        "role": "assistant",
                        "content": step_data["data"].get("answer", "")
                    })
                    # 保存coordinator返回的完整状态
                    if "state" in step_data["data"]:
                        final_state = step_data["data"]["state"]
                elif step_data["type"] == "pause":
                    # 达到最大步数，返回总结并询问是否继续
                    collected_state["done"] = False  # 未完成，需要继续
                    summary = step_data["data"].get("summary", "")
                    collected_state["answer"] = summary
                    # 添加总结到消息历史
                    collected_state["messages"].append({
                        "role": "assistant",
                        "content": summary + "\n\n" + step_data["data"].get("message", "")
                    })
                    # 保存coordinator返回的完整状态
                    if "state" in step_data["data"]:
                        final_state = step_data["data"]["state"]
                elif step_data["type"] == "state_snapshot":
                    # 保存状态快照
                    if "state" in step_data["data"]:
                        final_state = step_data["data"]["state"]
                
                # 发送步骤数据
                yield f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"
                
                # 添加小延迟以确保前端能正确接收
                await asyncio.sleep(0.1)
            
            # ========== 关键修复：保存对话到数据库 ==========
            from ..core.schemas import AgentState
            from ..core.conversation_manager import ConversationMetadata
            from datetime import datetime
            
            # 如果coordinator返回了完整状态，使用它；否则从收集的数据构建
            if final_state:
                # 使用coordinator返回的完整状态（包含known_tables等）
                state = AgentState(**final_state)
                print(f"[API] 使用coordinator返回的完整状态: 已知表 {len(state.known_tables)} 个")
            else:
                # 如果没有收到完整状态，从收集的数据构建（兼容旧逻辑）
                state = AgentState(
                    question=collected_state["question"],
                    messages=collected_state["messages"],
                    steps=collected_state["steps"],
                    done=collected_state["done"],
                    answer={"ok": True, "data": collected_state["answer"]} if collected_state["answer"] else None,
                    max_steps=request.max_steps or 12,
                    known_tables=[],
                    known_schemas={},
                    candidate_tables=[],
                    known_samples={},
                    error_history=[],
                    sql_history=[],
                    last_error=None
                )
                print(f"[API] 警告：未收到coordinator的完整状态，使用默认值")
            
            # 保存到数据库
            metadata = ConversationMetadata(
                thread_id=thread_id,
                user_id="default",
                title=request.question[:50],  # 使用问题的前50个字符作为标题
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tool_categories=[],
                tags=[]
            )
            
            conversation_manager.save_conversation(metadata, state)
            print(f"✅ [API] 对话已保存到数据库: {thread_id}")
            
            # 发送完成信号（包含最终答案）
            yield f"data: {json.dumps({{'type': 'final', 'data': {{'content': collected_state['answer'], 'thread_id': thread_id}}}}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'data': {'thread_id': thread_id}}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            # 发送错误信息
            error_data = {
                "type": "error",
                "data": {
                    "thread_id": thread_id,
                    "error": str(e)
                }
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


# ==================== 测试API（简化对话，不使用ReAct）====================

@router.post("/conversation/test/simple")
async def simple_test_conversation(request: ConversationRequest):
    """
    简化测试接口 - 不使用ReAct，直接返回固定回答
    用于测试会话管理功能，排除ReAct引擎的干扰
    """
    from ..core.schemas import AgentState
    from ..core.conversation_manager import ConversationMetadata
    from datetime import datetime
    
    # 生成或使用已有的线程ID
    thread_id = request.thread_id or str(uuid4())
    
    # 固定的AI回答
    fixed_answer = f"这是测试回答（简化模式）。您的问题是：{request.question}"
    
    try:
        conversation_manager = get_conversation_manager()
        
        # 构建简单的状态对象
        state = AgentState(
            question=request.question,
            messages=[
                {"role": "user", "content": request.question},
                {"role": "assistant", "content": fixed_answer}
            ],
            steps=[],  # 测试模式不记录步骤
            done=True,
            answer={"ok": True, "data": fixed_answer},
            max_steps=1,
            known_tables=[],
            known_schemas={},
            candidate_tables=[],
            known_samples={},
            error_history=[],
            sql_history=[],
            last_error=None
        )
        
        # 保存到数据库
        metadata = ConversationMetadata(
            thread_id=thread_id,
            user_id="default",
            title=request.question[:50],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tool_categories=["test"],
            tags=["simple-test"]
        )
        
        conversation_manager.save_conversation(metadata, state)
        print(f"✅ [TEST API] 测试对话已保存: {thread_id}")
        
        return {
            "ok": True,
            "thread_id": thread_id,
            "answer": fixed_answer,
            "message": "测试对话已保存（简化模式）"
        }
        
    except Exception as e:
        print(f"❌ [TEST API] 保存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存测试对话失败: {str(e)}")


@router.post("/conversation/test/stream")
async def simple_test_stream(request: ConversationRequest):
    """
    简化测试接口（流式）- 不使用ReAct，直接返回固定回答
    用于测试会话管理功能，排除ReAct引擎的干扰
    """
    from ..core.schemas import AgentState
    from ..core.conversation_manager import ConversationMetadata
    from datetime import datetime
    
    # 生成或使用已有的线程ID
    thread_id = request.thread_id or str(uuid4())
    
    async def generate_simple_stream():
        try:
            # 固定的AI回答
            fixed_answer = f"这是测试回答（简化流式模式）。您的问题是：{request.question}"
            
            # 发送初始化信息
            yield f"data: {json.dumps({'type': 'init', 'data': {'thread_id': thread_id, 'question': request.question}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)
            
            # 发送思考步骤（模拟）
            yield f"data: {json.dumps({'type': 'thinking', 'data': {'step': 1, 'message': '正在处理（测试模式）...'}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.2)
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'finish', 'data': {'answer': fixed_answer, 'total_steps': 1}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)
            
            # ========== 保存到数据库 ==========
            conversation_manager = get_conversation_manager()
            
            # 检查是否已有会话，如果有就追加消息
            existing_state = conversation_manager.load_conversation(thread_id)
            
            if existing_state:
                # 追加新消息到现有会话
                existing_state.messages.extend([
                    {"role": "user", "content": request.question},
                    {"role": "assistant", "content": fixed_answer}
                ])
                existing_state.question = request.question  # 更新最新问题
                existing_state.answer = {"ok": True, "data": fixed_answer}
                
                # 使用现有的元数据，只更新时间
                metadata = ConversationMetadata(
                    thread_id=thread_id,
                    user_id="default",
                    title=request.question[:50],
                    created_at=datetime.now(),  # 使用当前时间作为创建时间
                    updated_at=datetime.now(),
                    tool_categories=["test"],
                    tags=["simple-test-stream"]
                )
                
                conversation_manager.save_conversation(metadata, existing_state)
                print(f"✅ [TEST STREAM API] 测试对话已更新（追加消息）: {thread_id}")
            else:
                # 创建新会话
                state = AgentState(
                    question=request.question,
                    messages=[
                        {"role": "user", "content": request.question},
                        {"role": "assistant", "content": fixed_answer}
                    ],
                    steps=[],
                    done=True,
                    answer={"ok": True, "data": fixed_answer},
                    max_steps=1,
                    known_tables=[],
                    known_schemas={},
                    candidate_tables=[],
                    known_samples={},
                    error_history=[],
                    sql_history=[],
                    last_error=None
                )
                
                metadata = ConversationMetadata(
                    thread_id=thread_id,
                    user_id="default",
                    title=request.question[:50],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tool_categories=["test"],
                    tags=["simple-test-stream"]
                )
                
                conversation_manager.save_conversation(metadata, state)
                print(f"✅ [TEST STREAM API] 测试对话已创建: {thread_id}")
            
            # 发送最终答案
            yield f"data: {json.dumps({'type': 'final', 'data': {'content': fixed_answer, 'thread_id': thread_id}}, ensure_ascii=False)}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'complete', 'data': {'thread_id': thread_id}}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            print(f"❌ [TEST STREAM API] 错误: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e), 'thread_id': thread_id}}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_simple_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


# ==================== 会话历史API ====================

@router.get("/conversation/history")
async def list_conversations(
    user_id: str = "default",
    tool_category: Optional[str] = None,
    limit: int = 100
):
    """列出对话历史"""
    try:
        conversation_manager = get_conversation_manager()
        conversations = conversation_manager.list_conversations(
            user_id=user_id,
            tool_category=tool_category,
            limit=limit
        )
        
        return {
            "ok": True,
            "conversations": conversations,
            "total": len(conversations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")


@router.get("/conversation/{thread_id}")
async def get_conversation(thread_id: str):
    """获取指定对话的详情"""
    try:
        conversation_manager = get_conversation_manager()
        state = conversation_manager.load_conversation(thread_id)
        
        if state is None:
            raise HTTPException(status_code=404, detail=f"对话 {thread_id} 不存在")
        
        # 过滤消息，只保留用户消息和最终答案（过滤掉过程步骤）
        filtered_messages = []
        for msg in state.messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            # 保留用户消息
            if role == "user":
                # 过滤掉错误提示消息
                if not content.startswith("格式错误：") and not content.startswith("错误："):
                    filtered_messages.append(msg)
            # 保留助手消息中的最终答案（不是过程步骤）
            elif role == "assistant":
                # 过滤掉过程步骤（思考、行动、观察）
                if not (content.startswith("思考:") or 
                        content.startswith("行动:") or 
                        content.startswith("观察:") or
                        content.startswith("## 历史对话摘要")):
                    filtered_messages.append(msg)
            # 保留系统消息（但通常不需要显示）
            elif role == "system":
                # 系统消息通常不显示，跳过
        
        # 如果有最终答案，确保它被包含在消息中
        if state.answer and state.answer.get("ok") and state.answer.get("data"):
            final_answer = state.answer["data"]
            # 检查最后一条助手消息是否已经是最终答案
            if not filtered_messages or \
               filtered_messages[-1].get("role") != "assistant" or \
               filtered_messages[-1].get("content") != final_answer:
                filtered_messages.append({
                    "role": "assistant",
                    "content": final_answer
                })
        
        # 创建过滤后的状态
        state_dict = state.dict() if hasattr(state, 'dict') else state.__dict__
        state_dict["messages"] = filtered_messages
        
        return {
            "ok": True,
            "thread_id": thread_id,
            "state": state_dict,
            "final_answer": state.answer.get("data") if state.answer else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话失败: {str(e)}")


@router.delete("/conversation/{thread_id}")
async def delete_conversation(thread_id: str):
    """删除指定对话"""
    try:
        conversation_manager = get_conversation_manager()
        conversation_manager.delete_conversation(thread_id)
        
        return {
            "ok": True,
            "message": f"对话 {thread_id} 已删除"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")


# ==================== 数据库快捷API ====================

@router.get("/database/tables")
async def list_database_tables():
    """快捷API：列出数据库表"""
    registry = get_tool_registry()
    tool = registry.get_tool("list_tables")
    
    if not tool:
        raise HTTPException(status_code=404, detail="Database tools not available")
    
    try:
        result = tool.handler()
        if isinstance(result, str):
            return json.loads(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/tables/{table_name}")
async def describe_database_table(table_name: str):
    """快捷API：描述数据库表"""
    registry = get_tool_registry()
    tool = registry.get_tool("describe_table")
    
    if not tool:
        raise HTTPException(status_code=404, detail="Database tools not available")
    
    try:
        result = tool.handler(table=table_name)
        if isinstance(result, str):
            return json.loads(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/query")
async def execute_database_query(sql: str, limit: int = 100):
    """快捷API：执行数据库查询"""
    registry = get_tool_registry()
    tool = registry.get_tool("run_sql")
    
    if not tool:
        raise HTTPException(status_code=404, detail="Database tools not available")
    
    try:
        result = tool.handler(sql=sql, limit=limit)
        if isinstance(result, str):
            return json.loads(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/tables/{table_name}/sample")
async def sample_database_table(table_name: str, limit: int = 5, columns: Optional[str] = None):
    """快捷API：获取表的示例数据"""
    registry = get_tool_registry()
    tool = registry.get_tool("sample_rows")
    
    if not tool:
        raise HTTPException(status_code=404, detail="Database tools not available")
    
    try:
        result = tool.handler(table=table_name, limit=limit, columns=columns)
        if isinstance(result, str):
            return json.loads(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统信息API ====================

@router.get("/system/info")
async def get_system_info():
    """获取系统信息"""
    registry = get_tool_registry()
    return {
        "system": "Database Explorer Agent",
        "version": "2.0.0",
        "architecture": "Unified MCP + ReAct",
        "tools": {
            "total": len(registry.get_all_tools()),
            "categories": registry.get_categories(),
            "registered_tools": registry.get_registered_tools()
        },
        "features": [
            "MCP工具调用",
            "ReAct推理架构", 
            "流式对话",
            "会话历史管理",
            "数据库探索",
            "智能问答"
        ]
    }


@router.get("/system/prompt")
async def get_system_prompt():
    """获取系统提示词"""
    registry = get_tool_registry()
    return {
        "system_prompt": registry.get_combined_system_prompt(),
        "categories": registry.get_categories()
    }
