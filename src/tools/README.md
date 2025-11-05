# 工具包索引 (Tools Index)

## 📋 概述

本目录包含了所有可用的工具包，每个工具包都是独立的模块，提供特定领域的功能。

## 🛠️ 可用工具包

### 1. 数据库工具包 (Database Tools)
**路径**: `database/`  
**主要功能**: 智能数据库查询助手

#### 核心特性
- 🧠 **自然语言理解**: 将自然语言转换为SQL查询
- 🔍 **智能表发现**: 自动识别相关数据库表
- ⚡ **自动SQL生成**: 生成优化的SQL查询语句
- 🛡️ **安全防护**: SQL注入防护和权限控制
- 💾 **会话管理**: 保持对话上下文和历史记录
- 📊 **结果分析**: 智能分析和解释查询结果

#### 主要模块
- `client.py` - 主协调器 (205行，精简46%)
- `session_manager.py` - 会话管理器
- `execution_engine.py` - 执行引擎
- `action_executor.py` - 动作执行器
- `query_strategy.py` - 查询策略
- `knowledge_manager.py` - 知识管理器
- `observation_processor.py` - 观察处理器

#### 快速使用
```python
from src.agent_mcp.tools.database.client import DatabaseMCPClient

client = DatabaseMCPClient()
result = await client.plan_and_execute("查找销售额最高的产品")
```

#### 详细文档
📖 [数据库工具包详细文档](database/README.md)

---

## 🚀 如何添加新工具包

### 方式一：添加新的MCP工具（推荐）

#### 1. 定义核心业务函数
在 `src/tools/your_category/` 目录下创建业务逻辑文件：

```python
# src/tools/your_category/your_tools.py
from typing import Dict, Any

def your_function(param1: str, param2: int = 10) -> Dict[str, Any]:
    """你的工具函数描述"""
    try:
        # 实现具体业务逻辑
        result = f"处理 {param1} 和 {param2}"
        
        # 返回标准格式
        return {
            "ok": True,
            "data": {
                "result": result,
                "summary": f"成功处理了参数 {param1}"
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": {"code": "PROCESSING_ERROR", "message": str(e)}
        }
```

#### 2. 创建MCP包装器
```python
# 在同一文件中添加MCP包装器
def _your_function_wrapper(param1: str, param2: int = 10) -> str:
    """MCP工具包装器"""
    try:
        result = your_function(param1, param2)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "ok": False,
            "error": {"code": "TOOL_ERROR", "message": str(e)}
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
```

#### 3. 创建MCP Provider
```python
# src/tools/your_category/mcp_provider.py
from typing import List
from ...core.mcp_tool_registry import BaseMCPToolProvider, MCPToolInfo, ToolCategory
from .your_tools import _your_function_wrapper

class YourCategoryMCPProvider(BaseMCPToolProvider):
    """你的工具类别的MCP提供者"""
    
    def get_category(self) -> str:
        return "your_category"  # 或使用 ToolCategory.ANALYSIS 等
    
    def get_tools(self) -> List[MCPToolInfo]:
        return [
            MCPToolInfo(
                name="your_function",
                description="你的工具函数描述",
                category=self.get_category(),
                parameters={
                    "param1": {
                        "type": "string",
                        "description": "第一个参数的描述"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "第二个参数的描述",
                        "default": 10
                    }
                },
                handler=_your_function_wrapper,
                is_async=False
            )
        ]
    
    def get_system_prompt(self) -> str:
        return """
        你的工具类别说明：
        
        1. your_function: 工具功能描述
        
        使用建议：
        - 何时使用这个工具
        - 注意事项
        """.strip()

# 注册函数
def register_your_category_mcp_tools(registry):
    """注册你的工具类别到MCP工具注册表"""
    provider = YourCategoryMCPProvider()
    registry.register_provider(provider)
    return provider
```

#### 4. 注册到主应用
在 `main.py` 或相应的初始化文件中：

```python
# 导入你的注册函数
from src.tools.your_category.mcp_provider import register_your_category_mcp_tools

def create_mcp_server():
    """创建MCP服务器"""
    mcp_server = FastMCP("Your App Name")
    tool_registry = MCPToolRegistry(mcp_server)
    
    # 注册现有工具
    register_database_mcp_tools(tool_registry)
    
    # 注册你的新工具
    register_your_category_mcp_tools(tool_registry)
    
    return mcp_server, tool_registry
```

#### 5. 完整的调用流程
```
1. 客户端调用 your_function
   ↓
2. MCP服务器接收请求
   ↓
3. tool_wrapper 验证参数
   ↓
4. _your_function_wrapper 处理调用
   ↓
5. your_function 执行业务逻辑
   ↓
6. 返回JSON格式结果给客户端
```

### 方式二：传统工具包方式

#### 1. 创建工具包目录
```bash
mkdir src/tools/your_tool_name/
```

#### 2. 创建核心文件
```
your_tool_name/
├── __init__.py          # 包初始化
├── client.py            # 主要客户端类
├── mcp_provider.py      # MCP提供者（推荐）
├── README.md            # 详细文档
└── ...                  # 其他模块文件
```

#### 3. 实现标准接口
每个工具包都应该实现以下标准接口：

```python
class YourToolClient:
    def __init__(self):
        """初始化工具客户端"""
        pass
    
    async def execute(self, request: str, **kwargs) -> dict:
        """执行工具请求的主要方法"""
        pass
    
    def get_capabilities(self) -> list:
        """返回工具的能力列表"""
        pass
```

### 工具开发最佳实践

#### 1. 错误处理标准
```python
# 统一的错误格式
def _format_error(code: str, message: str) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}

def _format_success(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}
```

#### 2. 参数验证
```python
def validate_parameters(param1: str, param2: int):
    """参数验证示例"""
    if not param1 or not isinstance(param1, str):
        raise ValueError("param1 必须是非空字符串")
    if not isinstance(param2, int) or param2 < 0:
        raise ValueError("param2 必须是非负整数")
```

#### 3. 日志记录
```python
import logging
logger = logging.getLogger(__name__)

def your_function(param1: str):
    logger.info(f"开始处理参数: {param1}")
    try:
        # 业务逻辑
        result = process(param1)
        logger.info(f"处理完成: {result}")
        return _format_success(result)
    except Exception as e:
        logger.error(f"处理失败: {e}")
        return _format_error("PROCESSING_ERROR", str(e))
```

#### 4. 编写详细文档
在工具包目录下创建 `README.md`，包含：
- 📋 工具概述和用途
- 🚀 核心功能列表
- 🏗️ 架构设计说明
- 📦 模块详细说明
- 🔧 使用方法和示例
- 🎯 特色功能展示
- 🧪 测试指南
- ⚙️ 配置选项

#### 5. 更新索引
在本文档中添加新工具包的信息。

---

## 🎯 MCP工具开发完整示例

### 示例：创建一个文本处理工具

#### 步骤1：定义业务函数
```python
# src/tools/text/text_tools.py
import json
from typing import Dict, Any

def count_words(text: str) -> Dict[str, Any]:
    """统计文本中的单词数量"""
    try:
        if not text or not isinstance(text, str):
            return {
                "ok": False,
                "error": {"code": "INVALID_INPUT", "message": "文本不能为空"}
            }
        
        words = text.split()
        word_count = len(words)
        char_count = len(text)
        
        return {
            "ok": True,
            "data": {
                "word_count": word_count,
                "char_count": char_count,
                "text_preview": text[:50] + "..." if len(text) > 50 else text,
                "summary": f"文本包含 {word_count} 个单词，{char_count} 个字符"
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": {"code": "PROCESSING_ERROR", "message": str(e)}
        }

def _count_words_wrapper(text: str) -> str:
    """MCP包装器"""
    try:
        result = count_words(text)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "ok": False,
            "error": {"code": "WRAPPER_ERROR", "message": str(e)}
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
```

#### 步骤2：创建MCP Provider
```python
# src/tools/text/mcp_provider.py
from typing import List
from ...core.mcp_tool_registry import BaseMCPToolProvider, MCPToolInfo, ToolCategory
from .text_tools import _count_words_wrapper

class TextMCPProvider(BaseMCPToolProvider):
    """文本处理工具的MCP提供者"""
    
    def get_category(self) -> str:
        return ToolCategory.ANALYSIS
    
    def get_tools(self) -> List[MCPToolInfo]:
        return [
            MCPToolInfo(
                name="count_words",
                description="统计文本中的单词和字符数量",
                category=self.get_category(),
                parameters={
                    "text": {
                        "type": "string",
                        "description": "要分析的文本内容"
                    }
                },
                handler=_count_words_wrapper,
                is_async=False
            )
        ]
    
    def get_system_prompt(self) -> str:
        return """
        文本分析工具集合：
        
        1. count_words: 统计文本的单词数和字符数
        
        使用建议：
        - 适用于文本长度分析
        - 可用于内容审核和统计
        """.strip()

def register_text_mcp_tools(registry):
    """注册文本工具到MCP工具注册表"""
    provider = TextMCPProvider()
    registry.register_provider(provider)
    return provider
```

#### 步骤3：注册到主应用
```python
# 在 main.py 中添加
from src.tools.text.mcp_provider import register_text_mcp_tools

def create_mcp_server():
    # ... 现有代码 ...
    
    # 注册文本工具
    register_text_mcp_tools(tool_registry)
    
    return mcp_server, tool_registry
```

#### 步骤4：测试工具
```python
# 测试脚本
async def test_text_tools():
    # 假设已经有了tool_registry实例
    result = await tool_registry.call_tool("count_words", text="Hello world! This is a test.")
    print(result)
    # 输出: {"ok": true, "data": {"word_count": 6, "char_count": 28, ...}}
```

### 工具开发检查清单

#### ✅ 开发前检查
- [ ] 确定工具的功能和用途
- [ ] 选择合适的工具类别
- [ ] 设计参数和返回值格式
- [ ] 考虑错误处理场景

#### ✅ 开发中检查
- [ ] 实现核心业务函数
- [ ] 添加MCP包装器
- [ ] 创建Provider类
- [ ] 定义工具元数据
- [ ] 编写系统提示词

#### ✅ 开发后检查
- [ ] 注册到主应用
- [ ] 编写测试用例
- [ ] 更新文档
- [ ] 验证工具功能
- [ ] 检查错误处理

### 常见问题和解决方案

#### Q: 工具参数验证失败
```python
# 解决方案：在包装器中添加参数验证
def _your_tool_wrapper(param: str) -> str:
    if not param:
        return json.dumps({
            "ok": False,
            "error": {"code": "INVALID_PARAM", "message": "参数不能为空"}
        })
    # ... 继续处理
```

#### Q: 工具执行超时
```python
# 解决方案：设置超时和异步处理
import asyncio
from concurrent.futures import TimeoutError

async def _async_tool_wrapper(param: str) -> str:
    try:
        # 设置5秒超时
        result = await asyncio.wait_for(
            your_long_running_function(param), 
            timeout=5.0
        )
        return json.dumps(result)
    except TimeoutError:
        return json.dumps({
            "ok": False,
            "error": {"code": "TIMEOUT", "message": "工具执行超时"}
        })
```

#### Q: 工具返回数据过大
```python
# 解决方案：限制返回数据大小
def _your_tool_wrapper(param: str) -> str:
    result = your_function(param)
    
    # 限制返回数据大小（例如1MB）
    result_str = json.dumps(result, ensure_ascii=False)
    if len(result_str) > 1024 * 1024:  # 1MB
        return json.dumps({
            "ok": False,
            "error": {"code": "DATA_TOO_LARGE", "message": "返回数据过大"}
        })
    
    return result_str
```

---

## 📚 工具包设计原则

### 1. 单一职责原则
每个工具包只负责一个特定领域的功能。

### 2. 模块化设计
工具包内部应该进一步模块化，便于维护和扩展。

### 3. 标准化接口
所有工具包都应该遵循统一的接口规范。

### 4. 完整文档
每个工具包都必须有详细的使用文档。

### 5. 测试覆盖
每个工具包都应该有完整的测试用例。

---

## 🔧 工具包管理

### 导入工具包
```python
# 导入特定工具包
from src.agent_mcp.tools.database import DatabaseMCPClient

# 动态导入
import importlib
tool_module = importlib.import_module('src.agent_mcp.tools.database')
```

### 工具包注册
```python
# 在主应用中注册工具包
AVAILABLE_TOOLS = {
    'database': 'src.agent_mcp.tools.database.client.DatabaseMCPClient',
    # 添加更多工具包...
}
```

### 工具包发现
```python
def discover_tools():
    """自动发现所有可用的工具包"""
    tools_dir = Path('src/agent_mcp/tools')
    available_tools = []
    
    for tool_dir in tools_dir.iterdir():
        if tool_dir.is_dir() and (tool_dir / 'client.py').exists():
            available_tools.append(tool_dir.name)
    
    return available_tools
```

---

## 📊 工具包统计

| 工具包 | 状态 | 模块数 | 代码行数 | 测试覆盖率 |
|--------|------|--------|----------|------------|
| Database | ✅ 已完成 | 7 | ~1200 | 95% |
| *待添加* | 🚧 规划中 | - | - | - |

---

## 🤝 贡献指南

1. **Fork** 项目
2. **创建** 新的工具包分支
3. **开发** 工具包功能
4. **编写** 测试用例
5. **更新** 文档
6. **提交** Pull Request

---

## 📞 支持与反馈

如有问题或建议，请：
- 提交 Issue
- 联系开发团队
- 查看相关文档

---

**最后更新**: 2024年1月  
**维护者**: Agent MCP 开发团队