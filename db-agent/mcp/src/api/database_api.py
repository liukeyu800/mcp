"""
数据库相关API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.tool_registry import ToolRegistry
from tools.database.provider import DatabaseToolProvider
from tools.charts.provider import ChartToolProvider

router = APIRouter(prefix="/database", tags=["database"])

# 全局工具注册表实例
_tool_registry = None

def get_tool_registry():
    """获取工具注册系统实例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        # 注册数据库工具
        db_provider = DatabaseToolProvider()
        _tool_registry.register_provider(db_provider)
        # 注册图表工具
        chart_provider = ChartToolProvider()
        _tool_registry.register_provider(chart_provider)
    return _tool_registry


class SQLRequest(BaseModel):
    query: str
    limit: Optional[int] = 100


class TableRequest(BaseModel):
    table_name: str
    limit: Optional[int] = 5


@router.get("/tables")
async def list_tables():
    """列出所有数据库表"""
    try:
        registry = get_tool_registry()
        result = await registry.execute_tool("list_tables")
        return {"status": "success", "tables": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表列表失败: {str(e)}")


@router.get("/tables/{table_name}/schema")
async def describe_table(table_name: str):
    """获取表结构"""
    try:
        registry = get_tool_registry()
        result = await registry.execute_tool("describe_table", table=table_name)
        return {"status": "success", "schema": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表结构失败: {str(e)}")


@router.get("/tables/{table_name}/sample")
async def sample_table_data(table_name: str, limit: int = 5):
    """获取表的示例数据"""
    try:
        registry = get_tool_registry()
        result = await registry.execute_tool("sample_rows", table=table_name, limit=limit)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取示例数据失败: {str(e)}")


@router.post("/query")
async def execute_sql(request: SQLRequest):
    """执行SQL查询"""
    try:
        registry = get_tool_registry()
        result = await registry.execute_tool("run_sql", sql=request.query, limit=request.limit)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL查询失败: {str(e)}")


@router.get("/stats")
async def database_stats():
    """获取数据库统计信息"""
    try:
        registry = get_tool_registry()
        
        # 获取表列表
        tables = await registry.execute_tool("list_tables")
        
        # 统计信息
        stats = {
            "total_tables": len(tables) if isinstance(tables, list) else 0,
            "tables": tables
        }
        
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库统计失败: {str(e)}")