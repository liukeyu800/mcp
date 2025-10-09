"""前端对话界面专用API接口"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from uuid import uuid4
import json

from core.conversation_manager import ConversationManager, ConversationMetadata
from core.schemas import AgentState, Step

# 创建路由器
router = APIRouter(prefix="/frontend", tags=["frontend"])

# 全局对话管理器实例
conversation_manager = None


def get_conversation_manager() -> ConversationManager:
    """获取对话管理器实例"""
    global conversation_manager
    if conversation_manager is None:
        conversation_manager = ConversationManager("conversations.db")
    return conversation_manager


# 请求和响应模型
class ConversationListResponse(BaseModel):
    """对话列表响应"""
    conversations: List[Dict[str, Any]]
    total: int


class ConversationDetailResponse(BaseModel):
    """对话详情响应"""
    thread_id: str
    metadata: Dict[str, Any]
    messages: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]


class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    question: str
    user_id: Optional[str] = "default"
    title: Optional[str] = None


class MessageRequest(BaseModel):
    """发送消息请求"""
    message: str
    thread_id: str


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str = "default",
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None
):
    """获取对话列表"""
    try:
        manager = get_conversation_manager()
        
        if search:
            # 搜索对话
            conversations_meta = manager.search_conversations(search, user_id)
        else:
            # 获取所有对话
            conversations_meta = manager.list_conversations(user_id)
        
        # 分页处理
        total = len(conversations_meta)
        conversations_meta = conversations_meta[offset:offset + limit]
        
        # 转换为前端友好的格式
        conversations = []
        for meta in conversations_meta:
            conversations.append({
                "thread_id": meta.thread_id,
                "title": meta.title,
                "created_at": meta.created_at.isoformat() if meta.created_at else None,
                "updated_at": meta.updated_at.isoformat() if meta.updated_at else None,
                "tool_categories": meta.tool_categories,
                "tags": meta.tags,
                "user_id": meta.user_id
            })
        
        return ConversationListResponse(
            conversations=conversations,
            total=total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")


@router.get("/conversations/{thread_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(thread_id: str):
    """获取对话详情"""
    try:
        manager = get_conversation_manager()
        
        # 获取对话元数据
        metadata = manager.get_conversation_metadata(thread_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 获取对话状态
        state = manager.load_conversation(thread_id)
        if not state:
            raise HTTPException(status_code=404, detail="对话状态不存在")
        
        # 构建消息列表（基于步骤历史）
        messages = []
        
        # 添加初始问题
        messages.append({
            "role": "user",
            "content": state.question,
            "timestamp": metadata.created_at.isoformat() if metadata.created_at else None,
            "type": "question"
        })
        
        # 添加步骤中的对话
        for i, step in enumerate(state.steps):
            if hasattr(step, 'thought') and step.thought:
                messages.append({
                    "role": "assistant",
                    "content": step.thought,
                    "timestamp": None,  # 步骤没有单独的时间戳
                    "type": "thought",
                    "step_index": i,
                    "action": getattr(step, 'action', None),
                    "args": getattr(step, 'args', {})
                })
            
            if hasattr(step, 'observation') and step.observation:
                messages.append({
                    "role": "system",
                    "content": json.dumps(step.observation, ensure_ascii=False) if isinstance(step.observation, dict) else str(step.observation),
                    "timestamp": None,
                    "type": "observation",
                    "step_index": i
                })
        
        # 构建步骤列表
        steps = []
        for i, step in enumerate(state.steps):
            steps.append({
                "index": i,
                "thought": getattr(step, 'thought', ''),
                "action": getattr(step, 'action', None),
                "args": getattr(step, 'args', {}),
                "observation": getattr(step, 'observation', None),
                "step_type": getattr(step, 'step_type', 'reasoning')
            })
        
        return ConversationDetailResponse(
            thread_id=thread_id,
            metadata={
                "title": metadata.title,
                "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
                "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
                "tool_categories": metadata.tool_categories,
                "tags": metadata.tags,
                "user_id": metadata.user_id,
                "question": state.question,
                "done": state.done,
                "max_steps": state.max_steps
            },
            messages=messages,
            steps=steps
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话详情失败: {str(e)}")


@router.post("/conversations")
async def create_conversation(request: CreateConversationRequest):
    """创建新对话"""
    try:
        manager = get_conversation_manager()
        
        # 生成新的thread_id
        thread_id = str(uuid4())
        
        # 创建对话
        state = manager.create_conversation(
            thread_id=thread_id,
            question=request.question,
            user_id=request.user_id
        )
        
        return {
            "status": "success",
            "thread_id": thread_id,
            "message": "对话创建成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")


@router.delete("/conversations/{thread_id}")
async def delete_conversation(thread_id: str):
    """删除对话"""
    try:
        manager = get_conversation_manager()
        
        # 检查对话是否存在
        metadata = manager.get_conversation_metadata(thread_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 删除对话
        manager.delete_conversation(thread_id)
        
        return {
            "status": "success",
            "message": "对话删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")


@router.put("/conversations/{thread_id}/title")
async def update_conversation_title(thread_id: str, title: str):
    """更新对话标题"""
    try:
        manager = get_conversation_manager()
        
        # 检查对话是否存在
        metadata = manager.get_conversation_metadata(thread_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 更新标题
        manager.update_conversation_title(thread_id, title)
        
        return {
            "status": "success",
            "message": "标题更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新标题失败: {str(e)}")


@router.get("/conversations/{thread_id}/export")
async def export_conversation(thread_id: str, format: str = "json"):
    """导出对话"""
    try:
        manager = get_conversation_manager()
        
        # 获取对话详情
        detail = await get_conversation_detail(thread_id)
        
        if format == "json":
            return {
                "status": "success",
                "data": detail.dict(),
                "format": "json"
            }
        elif format == "markdown":
            # 生成Markdown格式
            md_content = f"# {detail.metadata['title']}\n\n"
            md_content += f"**创建时间**: {detail.metadata['created_at']}\n"
            md_content += f"**更新时间**: {detail.metadata['updated_at']}\n"
            md_content += f"**对话ID**: {detail.thread_id}\n\n"
            
            md_content += "## 对话内容\n\n"
            for msg in detail.messages:
                if msg["role"] == "user":
                    md_content += f"**用户**: {msg['content']}\n\n"
                elif msg["role"] == "assistant":
                    md_content += f"**助手**: {msg['content']}\n\n"
                elif msg["role"] == "system":
                    md_content += f"**系统**: {msg['content']}\n\n"
            
            return {
                "status": "success",
                "data": md_content,
                "format": "markdown"
            }
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出对话失败: {str(e)}")


@router.get("/stats")
async def get_conversation_stats(user_id: str = "default"):
    """获取对话统计信息"""
    try:
        manager = get_conversation_manager()
        
        # 获取所有对话
        conversations = manager.list_conversations(user_id)
        
        # 统计信息
        total_conversations = len(conversations)
        
        # 按工具类型统计
        tool_stats = {}
        for conv in conversations:
            for tool_cat in conv.tool_categories:
                tool_stats[tool_cat] = tool_stats.get(tool_cat, 0) + 1
        
        # 按日期统计（最近7天）
        from collections import defaultdict
        date_stats = defaultdict(int)
        for conv in conversations:
            if conv.created_at:
                date_key = conv.created_at.strftime("%Y-%m-%d")
                date_stats[date_key] += 1
        
        return {
            "status": "success",
            "stats": {
                "total_conversations": total_conversations,
                "tool_usage": tool_stats,
                "daily_conversations": dict(date_stats)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
