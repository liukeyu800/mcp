"""
对话相关API路由
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
import asyncio
import json
from core.conversation_manager import ConversationManager
from core.tool_registry import ToolRegistry
from tools.database.provider import DatabaseToolProvider

router = APIRouter(prefix="/conversation", tags=["conversation"])

# 全局实例
_conversation_manager = None
_tool_registry = None

def get_conversation_manager():
    """获取对话管理器实例"""
    global _conversation_manager, _tool_registry
    if _conversation_manager is None:
        # 初始化工具注册系统
        _tool_registry = ToolRegistry()
        db_provider = DatabaseToolProvider()
        _tool_registry.register_provider(db_provider)
        
        # 初始化对话管理器
        _conversation_manager = ConversationManager("conversations.db")
        # 将工具注册表关联到对话管理器
        _conversation_manager.tool_registry = _tool_registry
    return _conversation_manager


class PlanRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None
    max_steps: Optional[int] = 12


@router.post("/plan")
async def plan_and_execute(request: PlanRequest):
    """规划并执行任务"""
    
    # 生成线程ID
    thread_id = request.thread_id or str(uuid4())
    
    try:
        # 使用统一架构的对话管理器
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


@router.post("/plan/stream")
async def plan_stream(request: PlanRequest):
    """流式执行计划，支持Server-Sent Events"""
    
    # 生成线程ID
    thread_id = request.thread_id or str(uuid4())
    
    async def generate_stream():
        try:
            # 使用统一架构的对话管理器
            conversation_manager = get_conversation_manager()
            
            # 发送初始化信息
            yield f"data: {json.dumps({'type': 'init', 'data': {'thread_id': thread_id, 'question': request.question}}, ensure_ascii=False)}\n\n"
            
            # 执行流式对话
            async for step_data in conversation_manager.run_conversation_stream(
                user_input=request.question,
                session_id=thread_id,
                max_steps=request.max_steps or 12
            ):
                # 发送步骤数据
                yield f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"
                
                # 添加小延迟以确保前端能正确接收
                await asyncio.sleep(0.1)
            
            # 发送完成信号
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