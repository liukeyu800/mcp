"""
数据库探索智能体 - 统一MCP架构
"""

__version__ = "2.0.0"
__author__ = "Database Explorer Agent Team"
__description__ = "基于MCP架构的数据库探索智能体"

# 导入核心组件
from .core.mcp_tool_registry import MCPToolRegistry, ToolCategory
from .core.conversation_manager import ConversationManager
from .tools.database.mcp_provider import register_database_mcp_tools

__all__ = [
    "MCPToolRegistry",
    "ToolCategory", 
    "ConversationManager",
    "register_database_mcp_tools"
]