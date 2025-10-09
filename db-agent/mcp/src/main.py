"""
统一API启动器
管理所有API模块的统一入口
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 导入所有API模块
from api import (
    database_router,
    conversation_router,
    session_router,
    tool_router,
    demo_router
)

# 导入前端API路由（保持向后兼容）
from frontend.conversation_api import router as frontend_router

# 加载环境变量
load_dotenv()

def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title="Database Agent MCP - Unified API",
        version="0.5.0",
        description="模块化的数据库代理API服务",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加响应头中间件，确保UTF-8编码
    @app.middleware("http")
    async def add_charset_header(request, call_next):
        response = await call_next(request)
        if response.headers.get("content-type", "").startswith("application/json"):
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response
    
    # 注册所有API路由
    app.include_router(database_router)
    app.include_router(conversation_router)
    app.include_router(session_router)
    app.include_router(tool_router)
    app.include_router(demo_router)
    
    # 保持向后兼容性 - 前端API路由
    app.include_router(frontend_router)
    
    @app.get("/")
    async def root():
        """根路径 - API服务信息"""
        return {
            "message": "Database Agent Unified API Server",
            "version": "0.5.0",
            "architecture": "Modular API Design",
            "modules": [
                "database",
                "conversation", 
                "session",
                "tool",
                "demo",
                "frontend"
            ],
            "endpoints": {
                "database": "/database/*",
                "conversation": "/conversation/*",
                "sessions": "/sessions/*",
                "tools": "/tools/*",
                "demo": "/demo/*",
                "frontend": "/frontend/*",
                "docs": "/docs",
                "health": "/health"
            }
        }
    
    @app.get("/health")
    async def health_check():
        """健康检查"""
        try:
            # 这里可以添加各个模块的健康检查
            return {
                "status": "healthy",
                "message": "所有模块运行正常",
                "version": "0.5.0",
                "architecture": "Modular API Design"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"健康检查失败: {str(e)}",
                "version": "0.5.0"
            }
    
    return app


# 创建全局app实例以支持外部导入
app = create_app()

def main():
    """主启动函数"""
    # 获取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "9623"))
    
    # 创建应用
    app = create_app()
    
    # 启动服务器
    print(f"🚀 启动Database Agent API服务器...")
    print(f"📍 地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    print(f"🎯 演示页面: http://{host}:{port}/demo")
    print(f"🔧 模块化架构已启用")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()