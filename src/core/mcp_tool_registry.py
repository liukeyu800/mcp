"""统一的MCP工具注册系统 - 替代原有的双重工具系统"""

from typing import Dict, Any, List, Optional, Callable, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP
import inspect
import json


@dataclass
class MCPToolInfo:
    """MCP工具信息"""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    handler: Callable
    is_async: bool = False


class ToolCategory:
    """工具类别常量"""
    DATABASE = "database"
    VISUALIZATION = "visualization"
    ANALYSIS = "analysis"
    GENERAL = "general"


class BaseMCPToolProvider(ABC):
    """MCP工具提供者基类"""
    
    @abstractmethod
    def get_category(self) -> str:
        """获取工具类别"""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[MCPToolInfo]:
        """获取工具列表"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取该类别工具的系统提示词"""
        pass
    
    def get_domain_context(self, state: Any = None) -> List[Dict[str, str]]:
        """获取领域特定上下文（可选实现）"""
        return []


class MCPToolRegistry:
    """统一的MCP工具注册中心"""
    
    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self._providers: Dict[str, BaseMCPToolProvider] = {}
        self._tools: Dict[str, MCPToolInfo] = {}
        self._categories: Dict[str, List[str]] = {}
        self._registered_tools: List[str] = []
    
    def register_provider(self, provider: BaseMCPToolProvider):
        """注册工具提供者"""
        category = provider.get_category()
        self._providers[category] = provider
        
        # 注册该提供者的所有工具到MCP服务器
        tools = provider.get_tools()
        for tool in tools:
            self._register_tool_to_mcp(tool)
            self._tools[tool.name] = tool
            
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(tool.name)
    
    def _register_tool_to_mcp(self, tool: MCPToolInfo):
        """将工具注册到MCP服务器"""
        # 创建包装函数来处理工具调用
        async def tool_wrapper(**kwargs):
            try:
                # 检查参数
                sig = inspect.signature(tool.handler)
                bound_args = sig.bind(**kwargs)
                bound_args.apply_defaults()
                
                # 执行工具
                if tool.is_async:
                    result = await tool.handler(**bound_args.arguments)
                else:
                    result = tool.handler(**bound_args.arguments)
                
                # 确保返回字符串格式（MCP要求）
                if isinstance(result, dict):
                    return json.dumps(result, ensure_ascii=False, indent=2)
                elif isinstance(result, str):
                    return result
                else:
                    return str(result)
                    
            except Exception as e:
                error_result = {
                    "status": "error",
                    "code": "EXECUTION_ERROR",
                    "message": str(e)
                }
                return json.dumps(error_result, ensure_ascii=False, indent=2)
        
        # 使用MCP装饰器注册工具
        decorated_func = self.mcp_server.tool(
            name=tool.name,
            description=tool.description
        )(tool_wrapper)
        
        self._registered_tools.append(tool.name)
        return decorated_func
    
    def register_function(self, 
                         func: Callable = None,
                         name: Optional[str] = None, 
                         description: Optional[str] = None,
                         category: str = ToolCategory.GENERAL,
                         parameters: Dict[str, Any] = None):
        """直接注册单个函数为工具 - 支持装饰器和直接调用两种方式"""
        
        def _register(f):
            tool_name = name or f.__name__
            tool_desc = description or f.__doc__ or f"Tool: {tool_name}"
            
            tool_info = MCPToolInfo(
                name=tool_name,
                description=tool_desc,
                category=category,
                parameters=parameters or {},
                handler=f,
                is_async=inspect.iscoroutinefunction(f)
            )
            
            self._register_tool_to_mcp(tool_info)
            self._tools[tool_name] = tool_info
            
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(tool_name)
            
            return f
        
        # 支持装饰器用法
        if func is None:
            return _register
        else:
            return _register(func)
    
    def get_tool(self, tool_name: str) -> Optional[MCPToolInfo]:
        """获取工具信息"""
        return self._tools.get(tool_name)
    
    def get_tools_by_category(self, category: str) -> List[MCPToolInfo]:
        """获取指定类别的工具"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names]
    
    def get_all_tools(self) -> List[MCPToolInfo]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_available_actions(self) -> List[str]:
        """获取所有可用动作名称"""
        return list(self._tools.keys())
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        try:
            # 检查参数
            sig = inspect.signature(tool.handler)
            bound_args = sig.bind(**kwargs)
            bound_args.apply_defaults()
            
            # 执行工具
            if tool.is_async:
                result = await tool.handler(**bound_args.arguments)
            else:
                result = tool.handler(**bound_args.arguments)
            
            return result
                
        except Exception as e:
            raise Exception(f"Tool execution failed: {str(e)}")
    
    def get_provider(self, category: str) -> Optional[BaseMCPToolProvider]:
        """获取工具提供者"""
        return self._providers.get(category)
    
    def get_categories(self) -> List[str]:
        """获取所有工具类别"""
        return list(self._categories.keys())
    
    def get_registered_tools(self) -> List[str]:
        """获取已注册到MCP的工具列表"""
        return self._registered_tools.copy()
    
    def get_combined_system_prompt(self, categories: List[str] = None) -> str:
        """获取组合的系统提示词"""
        if categories is None:
            categories = self.get_categories()
        
        prompts = []
        for category in categories:
            provider = self._providers.get(category)
            if provider:
                prompts.append(f"## {category.upper()}工具\n{provider.get_system_prompt()}")
        
        return "\n\n".join(prompts)
    
    def get_combined_domain_context(self, state: Any = None, categories: List[str] = None) -> List[Dict[str, str]]:
        """获取组合的领域上下文"""
        if categories is None:
            categories = self.get_categories()
        
        context = []
        for category in categories:
            provider = self._providers.get(category)
            if provider:
                context.extend(provider.get_domain_context(state))
        
        return context


# 工具装饰器 - 用于快速注册单个工具函数
def mcp_tool(name: str = None, 
             description: str = None, 
             category: str = ToolCategory.GENERAL,
             parameters: Dict[str, Any] = None):
    """MCP工具装饰器 - 用于快速注册单个工具函数
    
    使用方式:
    @mcp_tool(name="my_tool", description="我的工具", category=ToolCategory.DATABASE)
    def my_function(param1: str, param2: int = 10):
        return {"result": f"处理 {param1} 和 {param2}"}
    """
    def decorator(func):
        # 注意：这里不能立即注册，因为可能还没有registry实例
        # 实际注册会在registry.register_function被调用时进行
        func._mcp_tool_info = {
            'name': name or func.__name__,
            'description': description or func.__doc__ or f"Tool: {func.__name__}",
            'category': category,
            'parameters': parameters or {}
        }
        return func
    return decorator


def format_tool_result(success: bool, data: Any = None, error: str = None) -> Dict[str, Any]:
    """格式化工具结果的标准格式"""
    if success:
        return {"status": "success", "data": data}
    else:
        return {"status": "error", "message": error or "Unknown error"}


def tool_result_ok(data: Any) -> Dict[str, Any]:
    """返回成功结果的标准格式"""
    return format_tool_result(True, data)


def tool_result_error(code: str, message: str) -> Dict[str, Any]:
    """返回错误结果的标准格式"""
    return format_tool_result(False, error=f"{code}: {message}")
