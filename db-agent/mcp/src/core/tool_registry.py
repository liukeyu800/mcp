"""工具注册系统 - 统一管理所有工具类型"""

from typing import Dict, Any, List, Type, Optional, Callable
from abc import ABC, abstractmethod
import inspect
from dataclasses import dataclass


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    handler: Callable


class ToolCategory:
    """工具类别常量"""
    DATABASE = "database"
    VISUALIZATION = "visualization"
    ANALYSIS = "analysis"
    GENERAL = "general"


class BaseToolProvider(ABC):
    """工具提供者基类"""
    
    @abstractmethod
    def get_category(self) -> str:
        """获取工具类别"""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[ToolInfo]:
        """获取工具列表"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取该类别工具的系统提示词"""
        pass
    
    @abstractmethod
    def get_domain_context(self, state: Any) -> List[Dict[str, str]]:
        """获取领域特定上下文"""
        pass


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._providers: Dict[str, BaseToolProvider] = {}
        self._tools: Dict[str, ToolInfo] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register_provider(self, provider: BaseToolProvider):
        """注册工具提供者"""
        category = provider.get_category()
        self._providers[category] = provider
        
        # 注册该提供者的所有工具
        tools = provider.get_tools()
        for tool in tools:
            self._tools[tool.name] = tool
            
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(tool.name)
    
    def get_tool(self, tool_name: str) -> Optional[ToolInfo]:
        """获取工具信息"""
        return self._tools.get(tool_name)
    
    def get_tools_by_category(self, category: str) -> List[ToolInfo]:
        """获取指定类别的工具"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names]
    
    def get_all_tools(self) -> List[ToolInfo]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_available_actions(self) -> List[str]:
        """获取所有可用动作名称"""
        return list(self._tools.keys())
    
    def get_provider(self, category: str) -> Optional[BaseToolProvider]:
        """获取工具提供者"""
        return self._providers.get(category)
    
    def get_categories(self) -> List[str]:
        """获取所有工具类别"""
        return list(self._categories.keys())
    
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
    
    def get_combined_domain_context(self, state: Any, categories: List[str] = None) -> List[Dict[str, str]]:
        """获取组合的领域上下文"""
        if categories is None:
            categories = self.get_categories()
        
        context = []
        for category in categories:
            provider = self._providers.get(category)
            if provider:
                context.extend(provider.get_domain_context(state))
        
        return context
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "ok": False,
                "error": {"code": "TOOL_NOT_FOUND", "message": f"工具 {tool_name} 不存在"}
            }
        
        try:
            # 检查参数
            sig = inspect.signature(tool.handler)
            bound_args = sig.bind(**kwargs)
            bound_args.apply_defaults()
            
            # 执行工具
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**bound_args.arguments)
            else:
                result = tool.handler(**bound_args.arguments)
            
            return result
            
        except Exception as e:
            return {
                "ok": False,
                "error": {"code": "EXECUTION_ERROR", "message": str(e)}
            }


# 全局工具注册中心实例
_global_registry = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册中心"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool_provider(provider: BaseToolProvider):
    """注册工具提供者到全局注册中心"""
    registry = get_tool_registry()
    registry.register_provider(provider)


def tool(name: str, description: str, category: str = ToolCategory.GENERAL, 
         parameters: Dict[str, Any] = None):
    """工具装饰器 - 用于快速注册单个工具函数"""
    def decorator(func):
        tool_info = ToolInfo(
            name=name,
            description=description,
            category=category,
            parameters=parameters or {},
            handler=func
        )
        
        # 直接注册到全局注册中心
        registry = get_tool_registry()
        registry._tools[name] = tool_info
        
        if category not in registry._categories:
            registry._categories[category] = []
        registry._categories[category].append(name)
        
        return func
    return decorator