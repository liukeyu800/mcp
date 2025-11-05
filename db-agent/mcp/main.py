"""数据库探索智能体 - 统一入口"""

import sys
import os
import asyncio

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

from src.core.mcp_tool_registry import MCPToolRegistry
from src.core.conversation_manager import get_conversation_manager
from src.tools.database.mcp_provider import register_database_mcp_tools
from src.api import complete_router, demo_router


def create_fastapi_app():
    """创建FastAPI应用"""
    app = FastAPI(
        title="Database Explorer Agent",
        description="基于MCP架构的数据库探索智能体",
        version="2.0.0"
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册API路由
    app.include_router(complete_router, prefix="/api")
    app.include_router(demo_router)
    
    @app.get("/")
    async def root():
        return {
            "message": "Database Explorer Agent API",
            "version": "2.0.0",
            "architecture": "Unified MCP + ReAct",
            "endpoints": {
                "tools": "/api/tools",
                "conversation": "/api/conversation",
                "database": "/api/database",
                "system": "/api/system",
                "demo": "/demo"
            }
        }
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
    
    return app


def create_mcp_server():
    """创建MCP服务器"""
    # 创建FastMCP服务器
    mcp_server = FastMCP("Database Explorer Agent")
    
    # 创建统一的工具注册中心
    tool_registry = MCPToolRegistry(mcp_server)
    
    # 注册数据库工具
    register_database_mcp_tools(tool_registry)
    
    # 初始化对话管理器
    conversation_manager = get_conversation_manager(tool_registry)
    
    print(f"统一MCP服务器已创建")
    print(f"已注册 {len(tool_registry.get_categories())} 个工具类别")
    print(f"总共 {len(tool_registry.get_all_tools())} 个工具")
    
    for category in tool_registry.get_categories():
        tools = tool_registry.get_tools_by_category(category)
        print(f"   {category}: {len(tools)} 个工具")
        for tool in tools:
            print(f"     - {tool.name}: {tool.description}")
    
    return mcp_server, tool_registry, conversation_manager


async def run_mcp_server():
    """运行MCP服务器"""
    mcp_server, tool_registry, conversation_manager = create_mcp_server()
    
    print("\n启动统一MCP服务器...")
    await mcp_server.run()


def run_api_server():
    """运行API服务器"""
    import uvicorn
    
    app = create_fastapi_app()
    
    print("\n启动API服务器...")
    print("API文档: http://localhost:8000/docs")
    print("演示页面: http://localhost:8000/demo")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )


async def run_both_servers():
    """同时运行MCP服务器和API服务器"""
    import threading
    
    # 在单独线程中运行API服务器
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # 在主线程中运行MCP服务器
    await run_mcp_server()


def show_help():
    """显示帮助信息"""
    print("""
数据库探索智能体 - 统一入口

用法:
    python main.py [模式]

模式:
    api     - 运行API服务器 (默认)
    mcp     - 运行MCP服务器  
    both    - 同时运行两个服务器
    help    - 显示此帮助信息

示例:
    python main.py          # 运行API服务器
    python main.py api      # 运行API服务器
    python main.py mcp      # 运行MCP服务器
    python main.py both     # 同时运行两个服务器

API服务器:
    - 地址: http://localhost:8000
    - 文档: http://localhost:8000/docs
    - 演示: http://localhost:8000/demo
    """)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "help" or mode == "-h" or mode == "--help":
            show_help()
        elif mode == "api":
            run_api_server()
        elif mode == "mcp":
            asyncio.run(run_mcp_server())
        elif mode == "both":
            asyncio.run(run_both_servers())
        else:
            print(f"❌ 未知模式: {mode}")
            show_help()
            sys.exit(1)
    else:
        # 默认运行API服务器
        run_api_server()