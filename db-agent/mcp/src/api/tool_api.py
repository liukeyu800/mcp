"""
工具相关API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.tool_registry import ToolRegistry
from tools.database.provider import DatabaseToolProvider
from tools.charts.provider import ChartToolProvider

router = APIRouter(prefix="/tools", tags=["tools"])

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


class ToolRequest(BaseModel):
    tool_name: str
    parameters: dict


@router.get("/")
async def list_tools():
    """获取可用工具列表"""
    try:
        registry = get_tool_registry()
        tools_info = registry.get_all_tools()
        
        tools = []
        for tool_info in tools_info:
            tools.append({
                "name": tool_info.name,
                "description": tool_info.description,
                "category": tool_info.category,
                "parameters": tool_info.parameters
            })
        
        return {
            "status": "success", 
            "tools": tools,
            "total_tools": len(tools)
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")


@router.post("/call")
async def call_tool(request: ToolRequest):
    """直接调用指定工具"""
    try:
        registry = get_tool_registry()
        result = await registry.execute_tool(request.tool_name, **request.parameters)
        
        return {"status": "success", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工具调用失败: {str(e)}")


@router.get("/categories")
async def list_tool_categories():
    """获取工具分类"""
    try:
        registry = get_tool_registry()
        tools_info = registry.get_all_tools()
        
        categories = {}
        for tool_info in tools_info:
            category = tool_info.category
            if category not in categories:
                categories[category] = []
            categories[category].append({
                "name": tool_info.name,
                "description": tool_info.description
            })
        
        return {
            "status": "success",
            "categories": categories,
            "total_categories": len(categories)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具分类失败: {str(e)}")