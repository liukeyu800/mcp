# 数据库探索智能体

一个基于MCP (Model Context Protocol) 架构的智能数据库探索系统，支持自然语言查询、ReAct推理和实时流式对话。

## ✨ 核心特性

🤖 **智能对话** - 使用ReAct架构进行思考-行动-观察循环推理  
🗄️ **数据库探索** - 自然语言转SQL查询，智能数据分析  
🎤 **语音识别** - 本地化语音输入，基于FireRedASR模型  
🖼️ **图片OCR** - 图片文字识别，基于PaddleOCR引擎  
🔄 **流式响应** - 实时查看AI思考过程和执行步骤  
📚 **会话记忆** - 完整的对话历史管理和上下文理解  
🛡️ **安全防护** - SQL注入防护和权限控制  
🔧 **MCP标准** - 基于标准MCP协议的工具调用系统  

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 初始化数据库
```bash
python init_test_db.py
```

### 启动服务
```bash
# 启动主服务（端口8000）
python main.py

# 启动语音识别服务（端口8001，可选）
python speech_service.py

# 启动图片OCR服务（端口8002，可选）
python ocr_service.py

# 查看所有选项
python main.py help
```

### 访问应用
- 🌐 **主页**: http://localhost:8000
- 📚 **API文档**: http://localhost:8000/docs
- 🎮 **演示页面**: http://localhost:8000/demo
- 🎤 **语音识别**: 在主页点击麦克风按钮使用
- 🖼️ **图片OCR**: 在主页点击附件按钮上传图片

### 可选功能
- **语音识别**: 详细配置请参考 [SPEECH_SETUP.md](SPEECH_SETUP.md)
- **图片OCR**: 详细配置请参考 [OCR_SETUP.md](OCR_SETUP.md)

## 🎯 使用场景

### 数据分析师
```
"用户表中有多少活跃用户？"
"分析最近一个月的订单趋势"
"找出销量最好的产品类别"
```

### 开发者
```
"检查数据库表结构"
"查看表之间的关联关系" 
"生成数据统计报告"
```

### 业务人员
```
"本月收入比上月增长了多少？"
"哪些用户最有价值？"
"产品销售情况如何？"
```

## 🛠️ 技术架构

### 核心技术栈
- **FastAPI** - 现代异步Web框架
- **MCP Protocol** - 标准化工具调用协议
- **SQLite** - 轻量级数据库存储
- **React** - 现代化前端界面
- **Server-Sent Events** - 实时流式响应

### 架构设计
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   用户界面      │    │   API服务器     │    │   MCP工具系统   │
│                 │    │                 │    │                 │
│ • Web界面       │◄──►│ • REST API      │◄──►│ • 数据库工具    │
│ • 命令行        │    │ • 流式响应      │    │ • 安全检查      │
│ • API调用       │    │ • 会话管理      │    │ • 查询执行      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲
                                │
                       ┌─────────────────┐
                       │  ReAct推理引擎  │
                       │                 │
                       │ • 思考循环      │
                       │ • 行动规划      │
                       │ • 结果观察      │
                       └─────────────────┘
```

## 📡 API接口

### 工具管理
- `GET /api/tools` - 获取所有工具
- `POST /api/tools/execute` - 执行工具

### 智能对话
- `POST /api/conversation/plan` - 规划执行任务
- `POST /api/conversation/plan/stream` - 流式执行
- `GET /api/conversation/history` - 对话历史

### 数据库操作
- `GET /api/database/tables` - 列出所有表
- `POST /api/database/query` - 执行SQL查询
- `GET /api/database/tables/{table}/sample` - 获取样本数据

## 🎮 演示功能

访问 http://localhost:8000/demo 体验：

### 📊 数据库工具
- 表结构查看
- 数据采样预览
- SQL查询执行
- 结果可视化

### 🤖 智能对话
- 自然语言问答
- 实时思考过程
- 流式响应展示
- 历史对话回顾

### 📈 数据可视化
- 动态图表生成
- 多种图表类型
- 交互式展示

## 🔧 运行模式

```bash
python main.py          # API服务器（默认）
python main.py api      # API服务器模式
python main.py mcp      # MCP服务器模式  
python main.py both     # 同时运行两种模式
python main.py help     # 显示帮助信息
```

## 📁 项目结构

```
mcp/
├── main.py                 # 🎯 统一入口
├── src/                    # 核心代码
│   ├── core/              # 核心功能
│   │   ├── mcp_tool_registry.py          # MCP工具注册
│   │   ├── unified_conversation_manager.py # 对话管理
│   │   ├── schemas.py                     # 数据模型
│   │   └── ...
│   ├── api/               # API接口
│   │   ├── unified_complete_api.py        # 统一API
│   │   └── demo_api.py                    # 演示页面
│   ├── tools/             # 工具实现
│   │   ├── database/                      # 数据库工具
│   │   └── charts/                        # 图表工具
│   └── client/            # MCP客户端
├── frontend/              # React前端
├── init_test_db.py        # 数据库初始化
└── README.md              # 项目文档
```

## 🛡️ 安全特性

- **SQL注入防护** - 自动检测和阻止危险SQL
- **权限控制** - 只允许安全的查询操作
- **查询限制** - 限制返回结果数量
- **操作审计** - 记录所有数据库操作

## 🚀 扩展开发

### 添加新工具
1. 继承 `BaseMCPToolProvider` 创建工具提供者
2. 实现工具逻辑和参数定义
3. 在主入口注册工具提供者

### 自定义对话流程
1. 修改 `unified_conversation_manager.py`
2. 实现自定义ReAct循环
3. 添加新的推理步骤

### 扩展API功能
1. 在 `unified_complete_api.py` 添加路由
2. 使用统一的响应格式
3. 集成到现有工具系统

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**让数据库探索变得智能而简单** 🚀