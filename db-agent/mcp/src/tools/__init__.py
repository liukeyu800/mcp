"""
工具模块包

提供各种工具实现：
- 数据库工具：数据库查询和管理
- 未来可扩展：可视化工具、数据分析工具等

所有工具都基于统一的BaseToolProvider基类，并通过ToolRegistry进行注册和管理。
"""

from .base import BaseTool, ToolRegistry, format_tool_result
from .database import DatabaseTools

# 延迟导入避免循环依赖
def initialize_all_tools():
    """初始化所有工具"""
    try:
        from core.tool_registry import get_tool_registry
        from .database.provider import register_database_tools
        from .charts.provider import register_chart_tools
    except ImportError:
        # 如果相对导入失败，尝试绝对导入
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(current_dir)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        
        from core.tool_registry import get_tool_registry
        from tools.database.provider import register_database_tools
        from tools.charts.provider import register_chart_tools
    
    registry = get_tool_registry()
    
    # 注册数据库工具
    register_database_tools(registry)
    
    # 注册图表工具
    register_chart_tools(registry)
    
    print(f"已注册 {len(registry.get_categories())} 个工具类别")
    for category in registry.get_categories():
        tools = registry.get_tools_by_category(category)
        print(f"  {category}: {len(tools)} 个工具")
    
    return registry


__all__ = [
    "BaseTool",
    "ToolRegistry", 
    "format_tool_result",
    "DatabaseTools",
    "initialize_all_tools"
]

# 自动初始化
initialize_all_tools()