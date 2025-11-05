#!/usr/bin/env python3
"""
独立的语音识别服务
运行在单独的端口，与主服务分离
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Speech Recognition Service",
    description="独立的语音识别服务，基于FireRedASR",
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

# FireRedASR配置
FIREREDASR_PATH = Path(__file__).parent / "FireRedASR"
MODEL_DIR = FIREREDASR_PATH / "pretrained_models" / "FireRedASR-AED-L"
PYTHON_PATH = FIREREDASR_PATH / "fireredasr"

def check_fireredasr_setup():
    """检查FireRedASR环境是否配置正确"""
    if not FIREREDASR_PATH.exists():
        raise HTTPException(
            status_code=500, 
            detail="FireRedASR目录不存在，请确保FireRedASR已正确安装"
        )
    
    if not MODEL_DIR.exists():
        raise HTTPException(
            status_code=500, 
            detail="FireRedASR模型目录不存在，请下载模型文件"
        )
    
    return True

def convert_audio_to_wav(input_path: str, output_path: str) -> bool:
    """使用ffmpeg转换音频格式为16kHz WAV"""
    try:
        cmd = [
            "ffmpeg", "-i", input_path,
            "-ar", "16000",  # 采样率16kHz
            "-ac", "1",      # 单声道
            "-acodec", "pcm_s16le",  # 16位PCM编码
            "-f", "wav",     # WAV格式
            "-y",            # 覆盖输出文件
            output_path
        ]
        
        logger.info(f"执行ffmpeg命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg转换失败，返回码: {result.returncode}")
            logger.error(f"ffmpeg stderr: {result.stderr}")
            return False
        
        logger.info(f"ffmpeg转换成功: {input_path} -> {output_path}")
        return True
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg转换超时")
        return False
    except Exception as e:
        logger.error(f"ffmpeg转换异常: {e}", exc_info=True)
        return False

def run_fireredasr(wav_path: str) -> Optional[str]:
    """运行FireRedASR进行语音识别"""
    try:
        # 设置环境变量
        env = os.environ.copy()
        
        # Windows使用;分隔，Linux/Mac使用:分隔
        path_sep = ';' if os.name == 'nt' else ':'
        env["PATH"] = f"{PYTHON_PATH}{path_sep}{PYTHON_PATH / 'utils'}{path_sep}{env.get('PATH', '')}"
        env["PYTHONPATH"] = f"{FIREREDASR_PATH}{path_sep}{env.get('PYTHONPATH', '')}"
        
        # 构建命令 - 使用相对路径，因为工作目录已经是FireRedASR
        cmd = [
            "python", "fireredasr/speech2text.py",
            "--asr_type", "aed",
            "--model_dir", "pretrained_models/FireRedASR-AED-L",
            "--wav_path", os.path.abspath(wav_path),  # 使用绝对路径
            "--use_gpu", "0",  # 使用CPU，如果有GPU可以改为1
            "--batch_size", "1",
            "--beam_size", "1"
        ]
        
        logger.info(f"执行FireRedASR命令: {' '.join(cmd)}")
        logger.info(f"工作目录: {FIREREDASR_PATH}")
        logger.info(f"PYTHONPATH: {env.get('PYTHONPATH', '')}")
        
        # 执行命令
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60,
            env=env,
            cwd=str(FIREREDASR_PATH)
        )
        
        # 记录完整输出用于调试
        logger.info(f"FireRedASR stdout: {result.stdout}")
        logger.info(f"FireRedASR stderr: {result.stderr}")
        logger.info(f"FireRedASR returncode: {result.returncode}")
        
        if result.returncode != 0:
            logger.error(f"FireRedASR执行失败: {result.stderr}")
            return None
        
        # 解析输出结果
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            # 尝试解析Python字典格式的输出
            if line.strip().startswith('{') and "'text':" in line:
                try:
                    import ast
                    result_dict = ast.literal_eval(line.strip())
                    if 'text' in result_dict:
                        text = result_dict['text']
                        logger.info(f"识别结果: {text}")
                        return text
                except Exception as e:
                    logger.error(f"解析字典格式失败: {e}")
            
            # 尝试解析 uttid\ttext 格式
            if '\t' in line:
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    text = parts[1].strip()
                    logger.info(f"识别结果: {text}")
                    return text
        
        logger.error(f"无法解析FireRedASR输出结果，输出内容: {result.stdout}")
        return None
        
    except subprocess.TimeoutExpired:
        logger.error("FireRedASR执行超时")
        return None
    except Exception as e:
        logger.error(f"FireRedASR执行异常: {e}", exc_info=True)
        return None

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Speech Recognition Service",
        "version": "1.0.0",
        "description": "独立的语音识别服务，基于FireRedASR",
        "endpoints": {
            "recognize": "/api/speech/recognize",
            "status": "/api/speech/status",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "speech-recognition"}

@app.get("/api/speech/status")
async def get_speech_status():
    """
    获取语音识别服务状态
    """
    try:
        check_fireredasr_setup()
        
        # 检查ffmpeg是否可用
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            ffmpeg_available = True
        except:
            ffmpeg_available = False
        
        return JSONResponse(content={
            "success": True,
            "fireredasr_available": True,
            "ffmpeg_available": ffmpeg_available,
            "model_path": str(MODEL_DIR),
            "message": "语音识别服务正常"
        })
        
    except HTTPException as e:
        return JSONResponse(content={
            "success": False,
            "fireredasr_available": False,
            "ffmpeg_available": False,
            "error": e.detail,
            "message": "语音识别服务不可用"
        })
    except Exception as e:
        logger.error(f"状态检查异常: {e}")
        return JSONResponse(content={
            "success": False,
            "fireredasr_available": False,
            "ffmpeg_available": False,
            "error": str(e),
            "message": "语音识别服务异常"
        })

@app.post("/api/speech/recognize")
async def recognize_speech(audio: UploadFile = File(...)):
    """
    语音识别接口
    接收音频文件，返回识别结果
    """
    try:
        # 检查FireRedASR环境
        check_fireredasr_setup()
        
        # 验证文件类型
        if not audio.content_type or not audio.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="请上传音频文件")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_input:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_output:
                try:
                    # 保存上传的音频文件
                    content = await audio.read()
                    temp_input.write(content)
                    temp_input.flush()
                    
                    # 转换音频格式
                    if not convert_audio_to_wav(temp_input.name, temp_output.name):
                        raise HTTPException(status_code=500, detail="音频格式转换失败")
                    
                    # 执行语音识别
                    result_text = run_fireredasr(temp_output.name)
                    
                    if result_text is None:
                        raise HTTPException(status_code=500, detail="语音识别失败")
                    
                    return JSONResponse(content={
                        "success": True,
                        "text": result_text,
                        "message": "语音识别成功"
                    })
                    
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_input.name)
                        os.unlink(temp_output.name)
                    except:
                        pass
                        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音识别接口异常: {e}")
        raise HTTPException(status_code=500, detail=f"语音识别服务异常: {str(e)}")

def main():
    """主函数"""
    print("🎤 启动独立语音识别服务...")
    print("=" * 50)
    
    # 检查环境
    try:
        check_fireredasr_setup()
        print("✅ FireRedASR环境检查通过")
    except Exception as e:
        print(f"❌ FireRedASR环境检查失败: {e}")
        print("请确保:")
        print("1. FireRedASR目录存在")
        print("2. 模型文件已下载到 pretrained_models/FireRedASR-AED-L/")
        print("3. ffmpeg已安装")
        return
    
    # 检查ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        print("✅ ffmpeg检查通过")
    except:
        print("❌ ffmpeg不可用，请安装ffmpeg")
        return
    
    print("\n🚀 启动服务...")
    print("服务地址: http://localhost:8001")
    print("API文档: http://localhost:8001/docs")
    print("健康检查: http://localhost:8001/health")
    print("服务状态: http://localhost:8001/api/speech/status")
    print("\n按 Ctrl+C 停止服务")
    
    # 启动服务
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
