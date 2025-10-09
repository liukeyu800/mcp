"""完全MCP化的数据库服务器"""

import asyncio
import sys
import os
from mcp.server.fastmcp import FastMCP

# 添加src目录到Python路径以支持直接运行
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

# 导入数据库工具函数
try:
    from tools.database.database_tools import (
        list_tables, describe_table, run_sql, sample_rows, 
        get_table_stats, list_available_tools
    )
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from agent_mcp.tools.database.database_tools import (
        list_tables, describe_table, run_sql, sample_rows, 
        get_table_stats, list_available_tools
    )

# 创建MCP服务器
mcp = FastMCP("Database Agent MCP Server")

# 注册数据库工具
@mcp.tool("list_tables")
def list_tables_tool():
    """列出数据库中的所有表"""
    return list_tables()

@mcp.tool("describe_table")
def describe_table_tool(table: str):
    """获取指定表的结构信息（列名和类型）
    
    Args:
        table: 表名
    """
    return describe_table(table)

@mcp.tool("run_sql")
def run_sql_tool(sql: str, limit: int = 100):
    """执行SQL查询并返回结果
    
    Args:
        sql: 要执行的SQL语句
        limit: 返回结果的最大行数，默认100（减少上下文长度）
    """
    return run_sql(sql, limit)

@mcp.tool("sample_rows")
def sample_rows_tool(table: str, limit: int = 2, columns: str = None):
    """获取指定表的示例数据
    
    Args:
        table: 表名
        limit: 返回的示例行数，默认2（减少上下文长度）
        columns: 指定要查询的列，用逗号分隔，如 "id,name,status"。如果为None则查询所有列
    """
    return sample_rows(table, limit, columns)



@mcp.tool()
def get_table_stats_tool(table: str):
    """获取表的统计信息
    
    Args:
        table: 表名
    """
    return get_table_stats(table)

@mcp.tool()
def list_available_tools_tool():
    """列出所有可用的数据库工具"""
    return list_available_tools()

if __name__ == "__main__":
    mcp.run()