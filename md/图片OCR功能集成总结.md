# 🖼️ 图片OCR功能集成总结

## ✅ 已完成的功能

### 1. 后端OCR服务 (`ocr_service.py`)

独立的OCR识别服务，运行在端口8002：

**功能特性：**
- 接收图片上传并进行OCR识别
- 支持多种图片格式（jpg、png、webp等）
- 基于PaddleOCR引擎
- 自动角度矫正
- 返回识别的文字内容

**API接口：**
- `POST /api/ocr/recognize` - 图片识别
- `GET /api/ocr/status` - 服务状态
- `GET /health` - 健康检查

### 2. 前端OCR Hook (`frontend/src/hooks/useImageOCR.ts`)

自定义React Hook，处理图片OCR识别：

**功能：**
- 管理OCR识别状态
- 调用后端OCR服务
- 错误处理和用户反馈
- 返回识别结果

### 3. 前端界面集成 (`frontend/src/chat/ChatInterface.tsx`)

在聊天界面集成OCR功能：

**用户体验：**
- 点击📎按钮上传图片
- 拖拽图片到上传区域
- 自动识别图片中的文字
- 识别结果自动填入输入框
- 可以编辑后发送给大模型

## 🚀 使用方法

### 启动服务

```bash
# 终端1: 主服务
python main.py

# 终端2: OCR服务
python ocr_service.py
```

### 使用OCR功能

1. 访问 http://localhost:8000
2. 点击输入框左侧的📎（回形针）按钮
3. 上传图片文件
4. 系统自动识别文字并填入输入框
5. 可以编辑识别结果
6. 点击发送按钮将内容传递给大模型

## 📁 新增文件

```
项目根目录/
├── ocr_service.py                     # OCR识别服务（端口8002）
├── OCR_SETUP.md                       # OCR使用指南
├── OCR_INTEGRATION.md                 # 集成总结（本文档）
└── frontend/src/
    └── hooks/
        └── useImageOCR.ts             # OCR识别Hook
```

## 🔄 工作流程

```
用户上传图片
    ↓
前端调用 useImageOCR Hook
    ↓
发送到 http://localhost:8002/api/ocr/recognize
    ↓
PaddleOCR 识别图片文字
    ↓
返回识别结果
    ↓
自动填入输入框
    ↓
用户编辑（可选）
    ↓
发送给大模型处理
```

## 🎯 使用场景

### 场景1: 识别文档
1. 拍摄或扫描纸质文档
2. 上传图片
3. 提取文字内容
4. 向AI提问关于文档的问题

**示例：**
- 上传合同图片 → 提取文字 → 问："合同的关键条款是什么？"
- 上传发票图片 → 提取文字 → 问："帮我总结这张发票的信息"

### 场景2: 识别截图
1. 截取屏幕内容
2. 上传截图
3. 提取文字
4. 用于查询或分析

**示例：**
- 上传错误信息截图 → 提取错误文本 → 问："这个错误怎么解决？"
- 上传代码截图 → 提取代码 → 问："帮我优化这段代码"

### 场景3: 识别表格数据
1. 上传包含表格的图片
2. OCR提取内容
3. AI分析数据

**示例：**
- 上传报表图片 → 提取数据 → 问："帮我分析这个报表的趋势"

## 🔧 技术栈

**后端：**
- FastAPI - Web框架
- PaddleOCR - OCR引擎
- PaddlePaddle - 深度学习框架

**前端：**
- React - UI框架
- Ant Design X - 聊天组件
- TypeScript - 类型安全

## 📊 服务端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| 主服务 | 8000 | 数据库查询、对话管理 |
| 语音识别 | 8001 | FireRedASR语音识别 |
| 图片OCR | 8002 | PaddleOCR文字识别 |

## 🛠️ 依赖安装

```bash
# OCR相关依赖
pip install paddleocr paddlepaddle

# 如果有GPU
pip install paddlepaddle-gpu

# 其他依赖
pip install fastapi uvicorn python-multipart
```

## ⚙️ 配置选项

### GPU加速

在 `ocr_service.py` 中，PaddleOCR会自动检测GPU：
- 如果有GPU且安装了paddlepaddle-gpu，自动使用GPU
- 否则使用CPU模式

### 识别语言

默认支持中英文混合识别，可以在初始化时配置：
```python
PaddleOCR(
    use_angle_cls=True,  # 角度矫正
    lang='ch',           # 语言：ch(中文) / en(英文)
    show_log=False       # 隐藏详细日志
)
```

## 🔍 调试方法

### 1. 检查OCR服务状态

```bash
# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:8002/api/ocr/status"

# Linux/Mac
curl http://localhost:8002/api/ocr/status
```

### 2. 查看服务日志

OCR服务会输出详细的处理日志：
```
INFO:__main__:接收到图片: image.jpg, 类型: image/jpeg
INFO:__main__:图片已保存到临时文件: /tmp/xxx.jpg
INFO:__main__:开始OCR识别...
INFO:__main__:OCR识别完成，共识别 10 行文本
```

### 3. 手动测试API

```bash
# 使用curl测试
curl -X POST -F "image=@test.jpg" http://localhost:8002/api/ocr/recognize
```

## 📝 常见问题

### 1. OCR服务启动失败

**问题**: ModuleNotFoundError: No module named 'paddleocr'

**解决**: 
```bash
pip install paddleocr paddlepaddle
```

### 2. 识别准确率低

**原因**:
- 图片模糊或分辨率低
- 光线不足
- 文字倾斜角度大

**解决**:
- 提高图片质量
- 确保文字清晰
- PaddleOCR会自动矫正角度

### 3. 前端无法连接服务

**检查**:
1. OCR服务是否在运行
2. 端口8002是否被占用
3. 防火墙是否阻止连接

## 🎨 功能扩展

### 未来可以添加的功能

1. **批量识别**: 一次上传多张图片
2. **表格识别**: 识别并保留表格结构
3. **公式识别**: 识别数学公式和LaTeX
4. **手写识别**: 识别手写文字
5. **PDF识别**: 直接识别PDF文件

### 与其他功能的配合

- **语音 + OCR**: 语音描述 + 图片识别，多模态输入
- **OCR + 数据库**: 识别文档后存入数据库
- **OCR + 图表**: 识别数据后生成图表

## 📈 性能优化

### 建议

1. **图片大小**: 建议宽度800-1200px
2. **图片格式**: JPG或PNG
3. **GPU加速**: 使用GPU可提升5-10倍速度
4. **并发控制**: 同时处理多个请求时控制并发数

### 内存优化

OCR服务使用完图片后会自动删除临时文件，避免内存泄漏。

## 🎉 总结

OCR功能已成功集成到系统中：

✅ 独立的OCR服务（端口8002）  
✅ 前端文件上传支持  
✅ 自动OCR识别  
✅ 识别结果填入输入框  
✅ 可传递给大模型处理  
✅ 完善的错误处理  
✅ 详细的使用文档  

现在用户可以通过上传图片的方式，让AI理解图片中的文字内容！
