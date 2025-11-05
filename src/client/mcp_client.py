"""
统一的 MCP 客户端包装器
用于连接 MCP Server 并调用工具
"""

import asyncio
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """MCP 客户端包装器"""
    
    def __init__(self, server_script_path: str = "src/server.py"):
        """
        初始化 MCP 客户端
        
        Args:
            server_script_path: MCP 服务器脚本路径
        """
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self._server_params = None
        self._read = None
        self._write = None
        self._tools_cache: Dict[str, Any] = {}
    
    @asynccontextmanager
    async def connect(self):
        """连接到 MCP 服务器的上下文管理器"""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path],
            env=None
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await self._initialize_tools()
                try:
                    yield self
                finally:
                    self.session = None
                    self._tools_cache.clear()
    
    async def _initialize_tools(self):
        """初始化并缓存可用工具列表"""
        if not self.session:
            raise RuntimeError("MCP session not initialized")
        
        # 获取可用工具列表
        tools_result = await self.session.list_tools()
        for tool in tools_result.tools:
            self._tools_cache[tool.name] = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具执行结果
        """
        if not self.session:
            raise RuntimeError("MCP session not initialized. Use 'async with client.connect():'")
        
        try:
            # 调用工具
            result = await self.session.call_tool(tool_name, arguments or {})
            
            # 解析结果
            if result.content:
                # MCP 返回的 content 是一个列表，取第一个结果
                content = result.content[0]
                if hasattr(content, 'text'):
                    import json
                    # 尝试解析 JSON 结果
                    try:
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        return {"ok": True, "data": content.text}
                else:
                    return {"ok": True, "data": str(content)}
            
            return {"ok": True, "data": None}
            
        except Exception as e:
            return {
                "ok": False,
                "error": {
                    "code": "TOOL_EXECUTION_ERROR",
                    "message": str(e)
                }
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return list(self._tools_cache.values())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""
        return self._tools_cache.get(tool_name)
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools_cache.keys())


# 全局单例客户端
_global_client: Optional[MCPClient] = None
_client_lock = asyncio.Lock()


async def get_mcp_client(server_script_path: str = "src/server.py") -> MCPClient:
    """
    获取全局 MCP 客户端实例
    
    注意：这个客户端需要在异步上下文中使用
    """
    global _global_client
    
    async with _client_lock:
        if _global_client is None:
            _global_client = MCPClient(server_script_path)
    
    return _global_client

