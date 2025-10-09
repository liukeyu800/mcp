"""数据库工具函数模块"""

import os
import sys
import json
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError, OperationalError, NoSuchTableError
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加core目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(os.path.dirname(current_dir))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from core.guard import ensure_safe_sql
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from agent_mcp.core.guard import ensure_safe_sql

# 全局数据库引擎
def _serialize_datetime(obj):
    """处理datetime对象的JSON序列化"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def _convert_row_data(data):
    """转换行数据中的datetime对象为字符串"""
    if isinstance(data, list):
        return [_convert_row_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: _convert_row_data(value) for key, value in data.items()}
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    else:
        return data

# 全局数据库引擎
_engine = None

def _get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        db_url = os.getenv("DATABASE_URL", "sqlite:///memory.db")
        _engine = create_engine(db_url)
    return _engine

def _format_success(data: Any) -> Dict[str, Any]:
    """格式化成功结果"""
    return {"ok": True, "data": data}

def _format_error(code: str, message: str) -> Dict[str, Any]:
    """格式化错误结果"""
    return {"ok": False, "error": {"code": code, "message": message}}

def list_tables() -> Dict[str, Any]:
    """列出数据库中的所有表"""
    try:
        engine = _get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return _format_success({
            "tables": tables,
            "count": len(tables),
            "summary": f"发现 {len(tables)} 个表: {', '.join(tables[:5])}" + ("..." if len(tables) > 5 else "")
        })
    except Exception as e:
        return _format_error("DATABASE_ERROR", str(e))

def describe_table(table: str) -> Dict[str, Any]:
    """获取指定表的结构信息（列名和类型）
    
    Args:
        table: 表名
    """
    try:
        engine = _get_engine()
        inspector = inspect(engine)
        
        # 检查表是否存在
        if table not in inspector.get_table_names():
            return _format_error("TABLE_NOT_FOUND", f"表 '{table}' 不存在")
        
        # 获取列信息
        columns = inspector.get_columns(table)
        column_info = []
        for col in columns:
            column_info.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": col.get("default")
            })
        
        return _format_success({
            "table": table,
            "columns": column_info,
            "column_count": len(column_info),
            "summary": f"表 {table} 有 {len(column_info)} 个字段: {', '.join([c['name'] for c in column_info[:5]])}" + ("..." if len(column_info) > 5 else "")
        })
    except Exception as e:
        return _format_error("DATABASE_ERROR", str(e))

def run_sql(sql: str, limit: int = 100) -> Dict[str, Any]:
    """执行SQL查询并返回结果
    
    Args:
        sql: 要执行的SQL语句
        limit: 返回结果的最大行数，默认100（减少上下文长度）
    """
    try:
        # 安全检查
        if not ensure_safe_sql(sql):
            return _format_error("UNSAFE_SQL", "SQL语句包含潜在的不安全操作")
        
        engine = _get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            
            # 如果是查询语句，返回结果
            if result.returns_rows:
                rows = result.fetchmany(limit)
                columns = list(result.keys())
                # 转换数据，处理datetime对象
                data = [_convert_row_data(dict(zip(columns, row))) for row in rows]
                return _format_success({
                    "columns": columns,
                    "rows": data,
                    "row_count": len(data),
                    "summary": f"查询返回 {len(data)} 行数据" + (f"（限制 {limit} 行）" if len(data) == limit else "")
                })
            else:
                # 如果是修改语句，返回影响的行数
                return _format_success({
                    "affected_rows": result.rowcount,
                    "summary": f"操作影响了 {result.rowcount} 行"
                })
                
    except (ProgrammingError, OperationalError, NoSuchTableError) as e:
        return _format_error("SQL_ERROR", str(e))
    except Exception as e:
        return _format_error("DATABASE_ERROR", str(e))

def sample_rows(table: str, limit: int = 2, columns: str = None) -> Dict[str, Any]:
    """获取指定表的示例数据
    
    Args:
        table: 表名
        limit: 返回的示例行数，默认2（减少上下文长度）
        columns: 指定要查询的列，用逗号分隔，如 "id,name,status"。如果为None则查询所有列
    """
    try:
        engine = _get_engine()
        inspector = inspect(engine)
        
        # 检查表是否存在
        if table not in inspector.get_table_names():
            return _format_error("TABLE_NOT_FOUND", f"表 '{table}' 不存在")
        
        # 构建SQL查询
        if columns:
            # 验证指定的列是否存在
            table_columns = [col["name"] for col in inspector.get_columns(table)]
            requested_columns = [col.strip() for col in columns.split(",")]
            valid_columns = [col for col in requested_columns if col in table_columns]
            
            if not valid_columns:
                return _format_error("INVALID_COLUMNS", f"指定的列 '{columns}' 在表 '{table}' 中不存在")
            
            columns_str = ", ".join(valid_columns)
            sql = f"SELECT {columns_str} FROM {table} LIMIT {limit}"
        else:
            sql = f"SELECT * FROM {table} LIMIT {limit}"
        
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns_list = list(result.keys())
            # 转换数据，处理datetime对象
            data = [_convert_row_data(dict(zip(columns_list, row))) for row in rows]
            
        return _format_success({
            "table": table,
            "columns": columns_list,
            "sample_rows": data,
            "row_count": len(data),
            "summary": f"表 {table} 的 {len(data)} 行示例数据" + (f"（仅显示字段: {', '.join(columns_list)}）" if columns else "")
        })
        
    except Exception as e:
        return _format_error("DATABASE_ERROR", str(e))



def get_table_stats(table: str) -> Dict[str, Any]:
    """获取表的统计信息
    
    Args:
        table: 表名
    """
    try:
        engine = _get_engine()
        inspector = inspect(engine)
        
        # 检查表是否存在
        if table not in inspector.get_table_names():
            return _format_error("TABLE_NOT_FOUND", f"表 '{table}' 不存在")
        
        # 获取行数
        with engine.connect() as conn:
            count_result = conn.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
            row_count = count_result.fetchone()[0]
        
        # 获取列信息
        columns = inspector.get_columns(table)
        
        return _format_success({
            "table": table,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": [{"name": col["name"], "type": str(col["type"])} for col in columns],
            "summary": f"表 {table} 有 {row_count} 行数据，{len(columns)} 个字段"
        })
        
    except Exception as e:
        return _format_error("DATABASE_ERROR", str(e))

def list_available_tools() -> Dict[str, Any]:
    """列出所有可用的数据库工具"""
    tools = [
        "list_tables - 列出所有表",
        "describe_table - 描述表结构",
        "sample_rows - 查看表样本数据",
        "run_sql - 执行SQL查询",
        "get_table_stats - 获取表统计信息"
    ]
    
    return _format_success({
        "tools": tools,
        "count": len(tools),
        "summary": f"共有 {len(tools)} 个可用工具"
    })


# 为了向后兼容，添加面向对象的DatabaseTools类
class DatabaseTools:
    """数据库工具集合 - 面向对象接口"""
    
    def __init__(self):
        self._engine = None
        self._db_url = None
    
    def _get_engine(self):
        """获取数据库引擎"""
        if self._engine is None:
            # 使用全局引擎获取函数
            self._engine = _get_engine()
        return self._engine
    
    @staticmethod
    def register_tools(registry):
        """注册所有数据库工具到MCP服务器"""
        db_tools = DatabaseTools()
        
        @registry.mcp_server.tool()
        def list_tables_mcp() -> str:
            """列出数据库中的所有表"""
            return db_tools.list_tables()
        
        @registry.mcp_server.tool()
        def describe_table_mcp(table: str) -> str:
            """获取指定表的结构信息（列名和类型）
            
            Args:
                table: 表名
            """
            return db_tools.describe_table(table)
        
        @registry.mcp_server.tool()
        def run_sql_mcp(sql: str, limit: int = 100) -> str:
            """执行SQL查询并返回结果
            
            Args:
                sql: 要执行的SQL语句
                limit: 返回结果的最大行数，默认100（减少上下文长度）
            """
            return db_tools.run_sql(sql, limit)
        
        @registry.mcp_server.tool()
        def sample_rows_mcp(table: str, limit: int = 2, columns: str = None) -> str:
            """获取指定表的示例数据
            
            Args:
                table: 表名
                limit: 返回的示例行数，默认2（减少上下文长度）
                columns: 指定要查询的列，用逗号分隔，如 "id,name,status"。如果为None则查询所有列
            """
            return db_tools.sample_rows(table, limit, columns)
        
        # 更新注册表
        registry.registered_tools.extend(['list_tables_mcp', 'describe_table_mcp', 'run_sql_mcp', 'sample_rows_mcp'])
    
    def list_tables(self) -> str:
        """列出数据库中的所有表"""
        try:
            result = list_tables()
            if result.get("ok"):
                return self._tool_result_ok(result["data"])
            else:
                return self._tool_result_error(result["error"]["code"], result["error"]["message"])
        except Exception as e:
            return self._tool_result_error("DATABASE_ERROR", str(e))
    
    def describe_table(self, table: str) -> str:
        """获取指定表的结构信息"""
        try:
            result = describe_table(table)
            if result.get("ok"):
                return self._tool_result_ok(result["data"])
            else:
                return self._tool_result_error(result["error"]["code"], result["error"]["message"])
        except Exception as e:
            return self._tool_result_error("DATABASE_ERROR", str(e))
    
    def run_sql(self, sql: str, limit: int = 1000) -> str:
        """执行SQL查询并返回结果"""
        try:
            result = run_sql(sql, limit)
            if result.get("ok"):
                return self._tool_result_ok(result["data"])
            else:
                return self._tool_result_error(result["error"]["code"], result["error"]["message"])
        except Exception as e:
            return self._tool_result_error("DATABASE_ERROR", str(e))
    
    def sample_rows(self, table: str, limit: int = 5) -> str:
        """获取指定表的示例数据"""
        try:
            result = sample_rows(table, limit)
            if result.get("ok"):
                return self._tool_result_ok(result["data"])
            else:
                return self._tool_result_error(result["error"]["code"], result["error"]["message"])
        except Exception as e:
            return self._tool_result_error("DATABASE_ERROR", str(e))
    
    def _tool_result_ok(self, data: Any) -> str:
        """格式化成功结果为字符串"""
        import json
        # 使用自定义的datetime序列化处理
        converted_data = _convert_row_data(data)
        return json.dumps({"status": "success", "data": converted_data}, ensure_ascii=False, indent=2)
    
    def _tool_result_error(self, code: str, message: str) -> str:
        """格式化错误结果为字符串"""
        import json
        return json.dumps({"status": "error", "code": code, "message": message}, ensure_ascii=False, indent=2)


def register_database_tools(registry):
    """注册数据库工具到注册器"""
    DatabaseTools.register_tools(registry)