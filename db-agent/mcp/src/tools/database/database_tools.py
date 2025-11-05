"""数据库工具函数模块"""

import os
import sys
import json
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError, OperationalError, NoSuchTableError
from dotenv import load_dotenv
from .field_selector import SmartFieldSelector

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

def _optimize_select_query(sql: str, question: str) -> tuple:
    """优化SELECT查询的字段选择
    
    Args:
        sql: 原始SQL查询
        question: 用户问题
        
    Returns:
        tuple: (优化后的SQL, 优化信息)
    """
    try:
        import re
        
        # 简单的SQL解析，提取表名和字段
        # 匹配 SELECT ... FROM table_name 的模式
        select_pattern = r'SELECT\s+(.*?)\s+FROM\s+(\w+)'
        match = re.search(select_pattern, sql.upper())
        
        if not match:
            return sql, None
            
        fields_part = match.group(1).strip()
        table_name = match.group(2).lower()
        
        # 如果已经指定了具体字段（不是SELECT *），则不优化
        if fields_part != '*':
            return sql, None
            
        # 获取表的字段信息
        engine = _get_engine()
        inspector = inspect(engine)
        
        if table_name not in inspector.get_table_names():
            return sql, None
            
        table_columns = [col["name"] for col in inspector.get_columns(table_name)]
        
        # 使用智能字段选择器
        selector = SmartFieldSelector()
        selected_fields = selector.select_relevant_fields(table_columns, question)
        
        # 如果选择的字段数量与总字段数量相同，说明没有优化空间
        if len(selected_fields) >= len(table_columns):
            return sql, None
            
        # 构建优化后的SQL
        optimized_sql = sql.replace('SELECT *', f'SELECT {", ".join(selected_fields)}', 1)
        
        # 生成优化信息
        optimization_info = {
            "original_fields_count": len(table_columns),
            "selected_fields_count": len(selected_fields),
            "selected_fields": selected_fields,
            "optimization_ratio": f"{(1 - len(selected_fields) / len(table_columns)) * 100:.1f}%",
            "explanation": selector.explain_selection(table_columns, question, selected_fields)
        }
        
        return optimized_sql, optimization_info
        
    except Exception:
        # 如果优化过程出错，返回原始SQL
        return sql, None

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

def run_sql(sql: str, limit: int = 100, question: str = None) -> Dict[str, Any]:
    """执行SQL查询并返回结果
    
    Args:
        sql: 要执行的SQL语句
        limit: 返回结果的最大行数，默认100（减少上下文长度）
        question: 用户问题，用于智能优化SELECT查询的字段选择
    """
    try:
        # 安全检查
        if not ensure_safe_sql(sql):
            return _format_error("UNSAFE_SQL", "SQL语句包含潜在的不安全操作")
        
        # 如果提供了问题且是SELECT查询，尝试智能优化字段选择
        optimized_sql = sql
        field_optimization_info = None
        
        if question and sql.strip().upper().startswith('SELECT'):
            optimized_sql, field_optimization_info = _optimize_select_query(sql, question)
        
        engine = _get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(optimized_sql))
            
            # 如果是查询语句，返回结果
            if result.returns_rows:
                rows = result.fetchmany(limit)
                columns = list(result.keys())
                # 转换数据，处理datetime对象
                data = [_convert_row_data(dict(zip(columns, row))) for row in rows]
                
                response_data = {
                    "columns": columns,
                    "rows": data,
                    "row_count": len(data),
                    "summary": f"查询返回 {len(data)} 行数据" + (f"（限制 {limit} 行）" if len(data) == limit else "")
                }
                
                # 如果进行了字段优化，添加优化信息
                if field_optimization_info:
                    response_data["field_optimization"] = field_optimization_info
                    
                return _format_success(response_data)
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

def sample_rows(table: str, limit: int = 2, columns: str = None, question: str = None) -> Dict[str, Any]:
    """获取指定表的示例数据
    
    Args:
        table: 表名
        limit: 返回的示例行数，默认2（减少上下文长度）
        columns: 指定要查询的列，用逗号分隔，如 "id,name,status"。如果为None则查询所有列
        question: 用户问题，用于智能选择相关字段
    """
    try:
        engine = _get_engine()
        inspector = inspect(engine)
        
        # 检查表是否存在
        if table not in inspector.get_table_names():
            return _format_error("TABLE_NOT_FOUND", f"表 '{table}' 不存在")
        
        # 获取表的所有列信息
        table_columns = [col["name"] for col in inspector.get_columns(table)]
        
        # 构建SQL查询
        if columns:
            # 验证指定的列是否存在
            requested_columns = [col.strip() for col in columns.split(",")]
            valid_columns = [col for col in requested_columns if col in table_columns]
            
            if not valid_columns:
                return _format_error("INVALID_COLUMNS", f"指定的列 '{columns}' 在表 '{table}' 中不存在")
            
            columns_str = ", ".join(valid_columns)
            sql = f"SELECT {columns_str} FROM {table} LIMIT {limit}"
        elif question:
            # 使用智能字段选择
            selector = SmartFieldSelector()
            selected_fields = selector.select_relevant_fields(table_columns, question)
            columns_str = ", ".join(selected_fields)
            sql = f"SELECT {columns_str} FROM {table} LIMIT {limit}"
            
            # 添加字段选择说明
            explanation = selector.explain_selection(table_columns, question, selected_fields)
        else:
            sql = f"SELECT * FROM {table} LIMIT {limit}"
        
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns_list = list(result.keys())
            # 转换数据，处理datetime对象
            data = [_convert_row_data(dict(zip(columns_list, row))) for row in rows]
            
        response_data = {
            "table": table,
            "columns": columns_list,
            "sample_rows": data,
            "row_count": len(data),
            "summary": f"表 {table} 的 {len(data)} 行示例数据" + (f"（仅显示字段: {', '.join(columns_list)}）" if columns or question else "")
        }
        
        # 如果使用了智能字段选择，添加选择说明
        if question and 'explanation' in locals():
            response_data["field_selection_explanation"] = explanation
            
        return _format_success(response_data)
        
    except Exception as e:
        return _format_error("DATABASE_ERROR", str(e))


def list_available_tools() -> Dict[str, Any]:
    """列出所有可用的数据库工具"""
    tools = [
        "list_tables - 列出所有表",
        "describe_table - 描述表结构",
        "sample_rows - 查看表样本数据",
        "run_sql - 执行SQL查询"
    ]
    
    return _format_success({
        "tools": tools,
        "count": len(tools),
        "summary": f"共有 {len(tools)} 个可用工具"
    })

