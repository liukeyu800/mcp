"""
Database Agent MCP - Unified Architecture Database Agent

A unified architecture database agent that provides tools for safe and 
efficient database operations using a modern tool registry system.

Features:
- Unified tool registry: Centralized tool management
- Database tools: Query, inspect, and manage database operations
- Conversation management: Intelligent conversation flow
- Memory management: Persistent conversation history
- Security: SQL injection protection and safe database operations
- Modular architecture: Easy to extend with additional tool providers

Usage:
    from agent_mcp.core.tool_registry import ToolRegistry
    from agent_mcp.tools.database.provider import DatabaseToolProvider
    from agent_mcp.core.conversation_manager import ConversationManager
"""

__version__ = "0.4.0"
__author__ = "Database Agent MCP Team"

# Import main components
from .server import mcp

# Import unified architecture components
from .core.tool_registry import ToolRegistry, BaseToolProvider, ToolInfo
from .core.conversation_manager import ConversationManager
from .tools.database.provider import DatabaseToolProvider

# Import tool framework
from .tools.base import (
    BaseTool,
    format_tool_result
)

# Import database tools
from .tools.database.database_tools import DatabaseTools

# Import core modules
from .core import (
    memory_manager,
    MemoryManager,
    ActionName,
    DecideOut,
    Step,
    AgentState,
    ensure_safe_sql
)

__all__ = [
    # Main components
    "mcp",
    
    # Unified architecture components
    "ToolRegistry",
    "BaseToolProvider", 
    "ToolInfo",
    "ConversationManager",
    "DatabaseToolProvider",
    
    # Tool framework
    "BaseTool",
    "format_tool_result",
    
    # Database tools
    "DatabaseTools",
    
    # Core components
    "memory_manager",
    "MemoryManager",
    "ActionName",
    "DecideOut",
    "Step",
    "AgentState",
    "ensure_safe_sql",
    
    # Metadata
    "__version__",
    "__author__"
]