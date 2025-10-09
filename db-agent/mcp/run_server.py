#!/usr/bin/env python3
"""启动MCP Database Agent服务器"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

if __name__ == "__main__":
    # 直接运行server.py
    import subprocess
    server_path = os.path.join(os.path.dirname(__file__), "src", "server.py")
    subprocess.run([sys.executable, server_path])