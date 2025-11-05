"""
统一API模块包 - 基于MCP架构的完整API系统
"""

from .complete_api import router as complete_router
from .demo_api import router as demo_router

__all__ = [
    "complete_router",
    "demo_router"
]