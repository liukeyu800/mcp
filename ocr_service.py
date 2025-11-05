#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片OCR识别服务
支持上传图片进行OCR识别，识别结果可直接传递给大模型
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="OCR Recognition Service",
    description="图片OCR识别服务，基于PaddleOCR",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局OCR引擎实例
_ocr_engine = None


def get_ocr_engine():
    """获取OCR引擎实例"""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            logger.info("正在初始化PaddleOCR引擎...")
            _ocr_engine = PaddleOCR(
                use_angle_cls=True,  # 角度分类器
                lang='ch'  # 语言：中文
            )
            logger.info("✅ PaddleOCR引擎初始化成功")
        except Exception as e:
            logger.error(f"❌ PaddleOCR引擎初始化失败: {e}")
            raise
    return _ocr_engine


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "OCR Recognition Service",
        "version": "1.0.0",
        "description": "图片OCR识别服务，基于PaddleOCR",
        "endpoints": {
            "recognize": "/api/ocr/recognize",
            "status": "/api/ocr/status",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "ocr-recognition"}


@app.get("/api/ocr/status")
async def get_ocr_status():
    """获取OCR服务状态"""
    try:
        # 检查PaddleOCR是否可用
        try:
            import paddleocr
            paddleocr_available = True
            paddleocr_version = getattr(paddleocr, '__version__', 'unknown')
        except:
            paddleocr_available = False
            paddleocr_version = None
        
        # 检查Paddle是否可用
        try:
            import paddle
            paddle_available = True
            paddle_version = paddle.__version__
            
            # 检查GPU支持
            gpu_available = False
            if hasattr(paddle, "is_compiled_with_cuda"):
                gpu_available = paddle.is_compiled_with_cuda()
        except:
            paddle_available = False
            paddle_version = None
            gpu_available = False
        
        return JSONResponse(content={
            "success": True,
            "paddleocr_available": paddleocr_available,
            "paddleocr_version": paddleocr_version,
            "paddle_available": paddle_available,
            "paddle_version": paddle_version,
            "gpu_available": gpu_available,
            "message": "OCR服务正常" if paddleocr_available else "OCR服务不可用"
        })
        
    except Exception as e:
        logger.error(f"状态检查异常: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "message": "OCR服务异常"
        })


@app.post("/api/ocr/recognize")
async def recognize_image(image: UploadFile = File(...)):
    """
    图片OCR识别接口
    接收图片文件，返回OCR识别结果
    """
    temp_path = None
    try:
        # 验证文件类型
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")
        
        logger.info(f"📥 接收到图片: {image.filename}, 类型: {image.content_type}")
        
        # 创建临时文件保存上传的图片
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix) as temp_file:
            # 保存上传的图片
            content = await image.read()
            temp_file.write(content)
            temp_file.flush()
            temp_path = temp_file.name
            
            logger.info(f"💾 图片已保存到临时文件: {temp_path}")
            logger.info(f"📊 文件大小: {len(content)} bytes")
            
            # 获取OCR引擎
            ocr_engine = get_ocr_engine()
            
            # 执行OCR识别
            print("🔍 开始OCR识别...")
            logger.info("🔍 开始OCR识别...")
            result = ocr_engine.predict(temp_path)
            
            # 详细日志
            print(f"📋 OCR原始结果类型: {type(result)}")
            print(f"📋 OCR原始结果: {str(result)[:500]}...")  # 只显示前500字符
            logger.info(f"📋 OCR原始结果类型: {type(result)}")
            logger.info(f"📋 OCR原始结果: {str(result)[:500]}...")  # 只显示前500字符
            
            if not result:
                logger.warning("⚠️  OCR识别结果为空")
                return JSONResponse(content={
                    "success": True,
                    "text": "",
                    "line_count": 0,
                    "message": "未识别到文字内容"
                })
            
            # 提取识别的文本
            texts = []
            
            # 处理结果 - 新版PaddleOCR返回OCRResult对象
            try:
                # result通常是一个列表，第一个元素包含所有识别结果
                ocr_results = result[0] if isinstance(result, list) and len(result) > 0 else result
                
                print(f"📝 ocr_results类型: {type(ocr_results)}")
                print(f"📝 ocr_results长度: {len(ocr_results) if hasattr(ocr_results, '__len__') else 'N/A'}")
                logger.info(f"📝 ocr_results类型: {type(ocr_results)}")
                logger.info(f"📝 ocr_results长度: {len(ocr_results) if hasattr(ocr_results, '__len__') else 'N/A'}")
                
                # 检查是否是OCRResult对象
                if hasattr(ocr_results, '__class__') and 'OCRResult' in str(type(ocr_results)):
                    print("📦 检测到OCRResult对象")
                    
                    # OCRResult对象的文本在 rec_texts 属性中
                    if hasattr(ocr_results, 'rec_texts'):
                        rec_texts = ocr_results.rec_texts
                        print(f"📄 rec_texts类型: {type(rec_texts)}")
                        print(f"📄 rec_texts内容: {rec_texts}")
                        if isinstance(rec_texts, list):
                            for idx, text in enumerate(rec_texts):
                                if text:
                                    texts.append(str(text))
                                    # 获取对应的置信度
                                    confidence = "N/A"
                                    if hasattr(ocr_results, 'rec_scores') and idx < len(ocr_results.rec_scores):
                                        confidence = f"{ocr_results.rec_scores[idx]:.2f}"
                                    print(f"  ✅ 识别文本[{idx+1}]: {text} (置信度: {confidence})")
                        elif isinstance(rec_texts, str):
                            texts.append(rec_texts)
                            print(f"  ✅ 识别文本: {rec_texts}")
                    
                    # 如果没有rec_texts，尝试text属性
                    elif hasattr(ocr_results, 'text'):
                        texts_data = ocr_results.text
                        print(f"📄 text属性类型: {type(texts_data)}")
                        print(f"📄 text内容: {texts_data}")
                        if isinstance(texts_data, str):
                            texts.append(texts_data)
                        elif isinstance(texts_data, list):
                            texts.extend([str(t) for t in texts_data if t])
                    
                    else:
                        print("⚠️  未找到rec_texts或text属性，尝试从json中提取")
                        # 尝试从json属性中提取
                        if hasattr(ocr_results, 'json'):
                            json_data = ocr_results.json
                            print(f"📄 json数据结构: {str(json_data)[:500]}")
                            
                            # 从json中提取rec_texts
                            if isinstance(json_data, dict):
                                res = json_data.get('res', json_data)
                                if 'rec_texts' in res:
                                    rec_texts = res['rec_texts']
                                    rec_scores = res.get('rec_scores', [])
                                    print(f"📄 从json提取rec_texts: {rec_texts}")
                                    for idx, text in enumerate(rec_texts):
                                        if text:
                                            texts.append(str(text))
                                            confidence = rec_scores[idx] if idx < len(rec_scores) else "N/A"
                                            print(f"  ✅ 识别文本[{idx+1}]: {text} (置信度: {confidence})")
                        
                        # 如果还是没有，打印可用属性
                        if not texts:
                            if hasattr(ocr_results, '__dict__'):
                                print(f"可用属性: {list(ocr_results.__dict__.keys())}")
                            print("⚠️  无法从OCRResult对象中提取文本")
                
                elif not ocr_results:
                    logger.warning("⚠️  解析后的OCR结果为空")
                    return JSONResponse(content={
                        "success": True,
                        "text": "",
                        "line_count": 0,
                        "message": "未识别到文字内容"
                    })
                
                else:
                    # 传统格式处理
                    for idx, item in enumerate(ocr_results):
                        try:
                            logger.info(f"  处理第{idx+1}项，类型: {type(item)}")
                            
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                # 格式: [[bbox], (text, confidence)]
                                text_info = item[1]
                                if isinstance(text_info, (list, tuple)) and len(text_info) >= 1:
                                    text = text_info[0]
                                    confidence = text_info[1] if len(text_info) > 1 else 1.0
                                    texts.append(str(text))
                                    print(f"  ✅ 识别文本: {text} (置信度: {confidence:.2f})")
                                    logger.info(f"  ✅ 识别文本: {text} (置信度: {confidence:.2f})")
                            elif isinstance(item, dict):
                                # 如果是字典格式
                                if 'text' in item:
                                    texts.append(str(item['text']))
                                    logger.info(f"  ✅ 识别文本(字典): {item['text']}")
                        except Exception as e:
                            logger.warning(f"  ⚠️  解析第{idx+1}项失败: {e}")
                            continue
                
            except Exception as e:
                logger.error(f"❌ 解析OCR结果异常: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"解析OCR结果失败: {str(e)}")
            
            full_text = '\n'.join(texts)
            print(f"✅ OCR识别完成，共识别 {len(texts)} 行文本")
            logger.info(f"✅ OCR识别完成，共识别 {len(texts)} 行文本")
            if full_text:
                print(f"📄 识别内容预览: {full_text[:100]}...")
                logger.info(f"📄 识别内容预览: {full_text[:100]}...")
            
            return JSONResponse(content={
                "success": True,
                "text": full_text,
                "line_count": len(texts),
                "message": "OCR识别成功" if texts else "未识别到文字内容"
            })
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OCR识别接口异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR识别服务异常: {str(e)}")
    finally:
        # 清理临时文件
        if temp_path:
            try:
                os.unlink(temp_path)
                logger.debug(f"🗑️  临时文件已删除: {temp_path}")
            except:
                pass


def main():
    """主函数"""
    print("🔍 启动OCR识别服务...")
    print("=" * 50)
    
    # 检查环境
    try:
        import paddleocr
        print("✅ PaddleOCR已安装")
    except ImportError:
        print("❌ PaddleOCR未安装")
        print("请安装: pip install paddleocr")
        return
    
    try:
        import paddle
        print(f"✅ PaddlePaddle已安装 (版本: {paddle.__version__})")
        
        if hasattr(paddle, "is_compiled_with_cuda") and paddle.is_compiled_with_cuda():
            print("✅ GPU支持可用")
        else:
            print("⚠️  仅CPU模式")
    except ImportError:
        print("❌ PaddlePaddle未安装")
        print("请安装: pip install paddlepaddle")
        return
    
    print("\n🚀 启动服务...")
    print("服务地址: http://localhost:8002")
    print("API文档: http://localhost:8002/docs")
    print("健康检查: http://localhost:8002/health")
    print("服务状态: http://localhost:8002/api/ocr/status")
    print("\n按 Ctrl+C 停止服务\n")
    
    # 启动服务
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()

