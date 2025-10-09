"""
会话管理相关API路由
"""

from fastapi import APIRouter, HTTPException
from core.memory import memory_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/")
async def list_sessions():
    """列出所有会话"""
    try:
        sessions = memory_manager.list_sessions()
        return {"status": "success", "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    try:
        session_data = memory_manager.load_state(session_id)
        if session_data is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "success", "session": session_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        memory_manager.delete_state(session_id)
        return {"status": "success", "message": f"Session {session_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/{thread_id}/memory")
async def get_memory(thread_id: str):
    """获取指定线程的记忆"""
    try:
        conversations = memory_manager.get_conversations(thread_id)
        return {"thread_id": thread_id, "conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")