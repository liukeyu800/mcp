#!/usr/bin/env python3
"""启动MCP Database Agent的FastAPI接口"""

import sys
import os
import uvicorn

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9623)