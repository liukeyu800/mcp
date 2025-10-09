"""工具基类和注册机制"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from mcp.server.fastmcp import FastMCP


class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass


class ToolRegistry:
    """工具注册器"""
    
    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self.registered_tools: List[str] = []
    
    def register_tool(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        """注册单个工具"""
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"Tool: {tool_name}"
        
        # 使用MCP装饰器注册工具
        decorated_func = self.mcp_server.tool(name=tool_name, description=tool_desc)(func)
        self.registered_tools.append(tool_name)
        
        return decorated_func
    
    def register_tool_class(self, tool_class: type):
        """注册工具类中的所有工具方法"""
        if hasattr(tool_class, 'register_tools'):
            tool_class.register_tools(self)
        else:
            # 自动发现工具方法（以tool_开头的方法）
            for attr_name in dir(tool_class):
                if attr_name.startswith('tool_') and callable(getattr(tool_class, attr_name)):
                    method = getattr(tool_class, attr_name)
                    self.register_tool(method, name=attr_name[5:])  # 去掉tool_前缀
    
    def get_registered_tools(self) -> List[str]:
        """获取已注册的工具列表"""
        return self.registered_tools.copy()


def format_tool_result(success: bool, data: Any = None, error: str = None) -> Dict[str, Any]:
    """格式化工具结果的标准格式"""
    if success:
        return {"status": "success", "data": data}
    else:
        return {"status": "error", "message": error or "Unknown error"}


def tool_result_ok(data: Any) -> Dict[str, Any]:
    """返回成功结果的标准格式（向后兼容）"""
    return format_tool_result(True, data)


def tool_result_error(code: str, message: str) -> Dict[str, Any]:
    """返回错误结果的标准格式（向后兼容）"""
    return format_tool_result(False, error=f"{code}: {message}")