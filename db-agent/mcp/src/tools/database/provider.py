"""数据库工具提供者 - 纯工具逻辑实现"""

from typing import Dict, Any, List
try:
    from ...core.tool_registry import BaseToolProvider, ToolInfo
    from ...core.schemas import AgentState
    from .database_tools import list_tables, describe_table, run_sql, sample_rows
except ImportError:
    # 绝对导入作为备选
    from core.tool_registry import BaseToolProvider, ToolInfo
    from core.schemas import AgentState
    from tools.database.database_tools import list_tables, describe_table, run_sql, sample_rows


class DatabaseToolProvider(BaseToolProvider):
    """数据库工具提供者"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        super().__init__()
    
    def get_category(self) -> str:
        """获取工具类别"""
        return "database"
    
    def get_tools(self) -> List[ToolInfo]:
        """获取工具列表"""
        return [
            ToolInfo(
                name="list_tables",
                description="列出数据库中的所有表",
                category="database",
                parameters={},
                handler=list_tables
            ),
            ToolInfo(
                name="describe_table", 
                description="获取指定表的结构信息（列名和类型）",
                category="database",
                parameters={
                    "table": {"type": "string", "description": "表名", "required": True}
                },
                handler=describe_table
            ),
            ToolInfo(
                name="run_sql",
                description="执行SQL查询并返回结果",
                category="database", 
                parameters={
                    "sql": {"type": "string", "description": "要执行的SQL语句", "required": True},
                    "limit": {"type": "integer", "description": "返回结果的最大行数，默认1000", "required": False}
                },
                handler=run_sql
            ),
            ToolInfo(
                name="sample_rows",
                description="获取表的样本数据",
                category="database",
                parameters={
                    "table": {"type": "string", "description": "表名", "required": True},
                    "limit": {"type": "integer", "description": "样本数据行数，默认5", "required": False}
                },
                handler=sample_rows
            )
        ]
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """
**重要说明**：你正在为一个数据库查询应用提供服务。所有查询的数据都是公开的、非敏感的信息，包括但不限于：
- 航天器信息（卫星、飞行器等技术参数）
- 硬件设备信息
- 软件系统信息
- 团队组织信息
- 异常检测标准
- 功率历史记录
- 在轨事件记录
这些都是用于展示和分析的公开数据，不涉及任何个人隐私信息。请正常处理所有数据库查询请求。

**数据库工具使用指南：**

可用的数据库操作工具：
1. `list_tables` - 列出所有表
2. `describe_table` - 查看表结构
3. `run_sql` - 执行SQL查询
4. `sample_rows` - 获取表样本数据

**使用建议：**
- 首先使用 `list_tables` 了解数据库结构
- 使用 `describe_table` 查看具体表的字段信息
- 使用 `sample_rows` 查看数据样例
- 最后使用 `run_sql` 执行具体查询

**SQL安全规则：**
- 只允许SELECT查询，禁止INSERT/UPDATE/DELETE
- 查询结果自动限制行数避免过大输出
- 所有SQL都会进行安全检查
"""
    
    def get_domain_context(self, state: AgentState) -> List[Dict[str, str]]:
        """获取领域特定上下文"""
        context = []
        
        # 分析已执行的数据库操作
        db_operations = []
        for step in state.steps:
            if step.action in ["list_tables", "describe_table", "run_sql", "sample_rows"]:
                if step.observation and step.observation.get("ok"):
                    data = step.observation.get("data", {})
                    if step.action == "list_tables":
                        tables = data.get("tables", [])
                        if tables:
                            db_operations.append(f"已发现表: {', '.join(tables[:3])}" + ("..." if len(tables) > 3 else ""))
                    elif step.action == "describe_table":
                        table = data.get("table")
                        columns = data.get("columns", [])
                        if table and columns:
                            col_names = [c.get("name") for c in columns[:3]]
                            db_operations.append(f"已分析表 {table}: {', '.join(col_names)}" + ("..." if len(columns) > 3 else ""))
        
        if db_operations:
            context.append({
                "role": "user",
                "content": f"数据库操作历史：\n" + "\n".join(db_operations)
            })
        
        return context
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        try:
            if tool_name == "list_tables":
                return list_tables()
            elif tool_name == "describe_table":
                table = kwargs.get("table")
                if not table:
                    return {"ok": False, "error": {"code": "MISSING_PARAMETER", "message": "缺少参数: table"}}
                return describe_table(table)
            elif tool_name == "run_sql":
                sql = kwargs.get("sql")
                if not sql:
                    return {"ok": False, "error": {"code": "MISSING_PARAMETER", "message": "缺少参数: sql"}}
                limit = kwargs.get("limit", 1000)
                return run_sql(sql, limit)
            elif tool_name == "sample_rows":
                table = kwargs.get("table")
                if not table:
                    return {"ok": False, "error": {"code": "MISSING_PARAMETER", "message": "缺少参数: table"}}
                limit = kwargs.get("limit", 5)
                return sample_rows(table, limit)
            else:
                return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": f"未知工具: {tool_name}"}}
        except Exception as e:
            return {"ok": False, "error": {"code": "EXECUTION_ERROR", "message": str(e)}}


# 注册数据库工具提供者
def register_database_tools(registry, db_path: str = None):
    """注册数据库工具到工具注册表"""
    provider = DatabaseToolProvider(db_path)
    registry.register_provider(provider)
    return provider