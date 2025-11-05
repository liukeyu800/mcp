# 图片OCR识别功能使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install paddleocr paddlepaddle
```

如果有GPU，可以安装GPU版本：
```bash
pip install paddlepaddle-gpu
```

### 2. 启动OCR服务

```bash
python ocr_service.py
```

服务将在端口8002启动。

### 3. 使用OCR功能

#### 方法1: 通过文件上传按钮

1. 访问 http://localhost:8000
2. 点击输入框左侧的📎按钮
3. 上传图片文件（支持jpg、png等格式）
4. 系统会自动识别图片中的文字
5. 识别结果会自动填入输入框

#### 方法2: 拖拽上传

1. 直接将图片文件拖拽到上传区域
2. 系统自动识别并填入文字

## 支持的功能

- ✅ 自动识别中文和英文
- ✅ 支持多行文字识别
- ✅ 自动角度矫正
- ✅ 识别结果可直接发送给大模型

## 系统要求

- Python 3.8+
- PaddleOCR 2.0+
- PaddlePaddle 2.0+

## 服务端口

- 主服务: 8000
- 语音识别: 8001
- OCR识别: 8002

## 工作流程

```
1. 用户上传图片
   ↓
2. 前端调用OCR服务 (端口8002)
   ↓
3. PaddleOCR识别图片文字
   ↓
4. 识别结果返回前端
   ↓
5. 文字自动填入输入框
   ↓
6. 用户可以编辑并发送给大模型
```

## API接口

### 图片识别

**POST** `http://localhost:8002/api/ocr/recognize`

**请求:**
- Content-Type: `multipart/form-data`
- 参数: `image` (图片文件)

**响应:**
```json
{
  "success": true,
  "text": "识别到的文字内容",
  "line_count": 10,
  "message": "OCR识别成功"
}
```

### 服务状态

**GET** `http://localhost:8002/api/ocr/status`

**响应:**
```json
{
  "success": true,
  "paddleocr_available": true,
  "paddle_version": "2.5.0",
  "gpu_available": false,
  "message": "OCR服务正常"
}
```

## 常见问题

### 1. OCR识别失败

- 确保图片清晰
- 检查PaddleOCR是否正确安装
- 查看服务端日志

### 2. 识别准确率低

- 提高图片分辨率
- 确保文字清晰可见
- 尝试调整图片角度

### 3. 服务无法启动

检查依赖安装：
```bash
pip list | grep paddle
```

### 4. GPU不可用

如果需要GPU加速，确保：
- 安装CUDA
- 安装paddlepaddle-gpu版本

## 性能优化

- GPU加速可大幅提升识别速度
- 图片压缩到合适大小（建议宽度800-1200px）
- 批量处理时建议控制并发数

## 使用示例

### 场景1: 识别文档

1. 拍摄或扫描纸质文档
2. 上传图片
3. 系统自动提取文字
4. 向AI提问关于文档的问题

### 场景2: 识别截图

1. 截取屏幕内容
2. 上传截图
3. 提取文字内容
4. 用于查询或分析

### 场景3: 识别表格

1. 上传包含表格的图片
2. OCR提取文字内容
3. AI帮助整理和分析数据

## 技术栈

- **后端**: FastAPI + PaddleOCR
- **前端**: React + Ant Design X
- **OCR引擎**: PaddleOCR (支持80+语言)

## 更新日志

- **v1.0.0**: 初始版本，支持基础图片文字识别
