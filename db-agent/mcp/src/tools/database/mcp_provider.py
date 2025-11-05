"""数据库工具的MCP提供者 - 统一的MCP架构实现"""

from typing import Dict, Any, List
from ...core.mcp_tool_registry import BaseMCPToolProvider, MCPToolInfo, ToolCategory
from .database_tools import list_tables, describe_table, run_sql, sample_rows
import json


class DatabaseMCPProvider(BaseMCPToolProvider):
    """数据库工具的MCP提供者"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
    
    def get_category(self) -> str:
        """获取工具类别"""
        return ToolCategory.DATABASE
    
    def get_tools(self) -> List[MCPToolInfo]:
        """获取工具列表"""
        return [
            MCPToolInfo(
                name="list_tables",
                description="列出数据库中的所有表",
                category=self.get_category(),
                parameters={},
                handler=self._list_tables_wrapper,
                is_async=False
            ),
            MCPToolInfo(
                name="describe_table",
                description="获取指定表的结构信息（列名和类型）",
                category=self.get_category(),
                parameters={
                    "table": {
                        "type": "string",
                        "description": "表名"
                    }
                },
                handler=self._describe_table_wrapper,
                is_async=False
            ),
            MCPToolInfo(
                name="run_sql",
                description="执行SQL查询并返回结果",
                category=self.get_category(),
                parameters={
                    "sql": {
                        "type": "string",
                        "description": "要执行的SQL语句"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果的最大行数，默认100",
                        "default": 100
                    }
                },
                handler=self._run_sql_wrapper,
                is_async=False
            ),
            MCPToolInfo(
                name="sample_rows",
                description="获取指定表的示例数据",
                category=self.get_category(),
                parameters={
                    "table": {
                        "type": "string",
                        "description": "表名"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回的示例行数，默认2",
                        "default": 2
                    },
                    "columns": {
                        "type": "string",
                        "description": "指定要查询的列，用逗号分隔，如 'id,name,status'。如果为None则查询所有列",
                        "required": False
                    }
                },
                handler=self._sample_rows_wrapper,
                is_async=False
            )
        ]
    
    def get_system_prompt(self) -> str:
        """获取数据库工具的系统提示词"""
        return """
数据库工具集合，用于查询和探索数据库：

1. list_tables: 列出所有表
2. describe_table: 查看表结构
3. run_sql: 执行SQL查询
4. sample_rows: 获取表的示例数据

使用建议：
- 先用 list_tables 了解数据库结构
- 用 describe_table 查看感兴趣表的字段
- 用 sample_rows 查看数据示例
- 最后用 run_sql 执行具体查询

注意：所有查询都有行数限制以避免返回过多数据。
        """.strip()
    
    def get_domain_context(self, state: Any = None) -> List[Dict[str, str]]:
        """获取数据库领域特定上下文"""
        context = []
        
        # 尝试获取当前数据库的基本信息
        try:
            tables_result = list_tables()
            if tables_result.get("ok"):
                tables = tables_result["data"]["tables"]
                context.append({
                    "type": "database_schema",
                    "content": f"当前数据库包含 {len(tables)} 个表: {', '.join(tables)}"
                })
        except Exception:
            pass
        
        return context
    
    # 包装函数，将原有的工具函数包装成统一的格式
    def _list_tables_wrapper(self) -> str:
        """列出数据库中的所有表"""
        try:
            result = list_tables()
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            error_result = {
                "ok": False,
                "error": {"code": "DATABASE_ERROR", "message": str(e)}
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    def _describe_table_wrapper(self, table: str) -> str:
        """获取指定表的结构信息"""
        try:
            result = describe_table(table)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            error_result = {
                "ok": False,
                "error": {"code": "DATABASE_ERROR", "message": str(e)}
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    def _run_sql_wrapper(self, sql: str, limit: int = 100) -> str:
        """执行SQL查询并返回结果"""
        try:
            result = run_sql(sql, limit)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            error_result = {
                "ok": False,
                "error": {"code": "DATABASE_ERROR", "message": str(e)}
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    def _sample_rows_wrapper(self, table: str, limit: int = 2, columns: str = None) -> str:
        """获取指定表的示例数据"""
        try:
            result = sample_rows(table, limit, columns)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            error_result = {
                "ok": False,
                "error": {"code": "DATABASE_ERROR", "message": str(e)}
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)


def register_database_mcp_tools(registry, db_path: str = None):
    """注册数据库工具到MCP工具注册表"""
    provider = DatabaseMCPProvider(db_path)
    registry.register_provider(provider)
    return provider
