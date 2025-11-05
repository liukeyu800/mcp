"""
工具模块包

提供各种工具实现：
- 数据库工具：数据库查询和管理
- 图表工具：数据可视化
- 未来可扩展：数据分析工具等

现在使用统一的MCP工具注册架构。
"""

# 导入新的MCP架构组件
from ..core.mcp_tool_registry import (
    MCPToolRegistry, 
    BaseMCPToolProvider, 
    MCPToolInfo, 
    ToolCategory,
    format_tool_result,
    tool_result_ok,
    tool_result_error
)

# 导入数据库工具
from .database.mcp_provider import register_database_mcp_tools

# 导入图表工具（如果需要的话）
from .charts import create_line_chart, create_pie_chart, create_funnel_chart


def initialize_mcp_tools(mcp_server):
    """初始化所有MCP工具"""
    # 创建MCP工具注册中心
    tool_registry = MCPToolRegistry(mcp_server)
    
    # 注册数据库工具
    register_database_mcp_tools(tool_registry)
    
    # 如果需要图表工具，可以在这里添加
    # register_chart_mcp_tools(tool_registry)
    
    print(f"已注册 {len(tool_registry.get_categories())} 个工具类别")
    for category in tool_registry.get_categories():
        tools = tool_registry.get_tools_by_category(category)
        print(f"   {category}: {len(tools)} 个工具")
    
    return tool_registry


__all__ = [
    "MCPToolRegistry",
    "BaseMCPToolProvider", 
    "MCPToolInfo",
    "ToolCategory",
    "format_tool_result",
    "tool_result_ok",
    "tool_result_error",
    "initialize_mcp_tools",
    "register_database_mcp_tools",
    "create_line_chart",
    "create_pie_chart", 
    "create_funnel_chart"
]