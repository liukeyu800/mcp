#!/usr/bin/env python3
"""
简单的流式输出调试脚本
"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.conversation_manager import ConversationManager
from core.tool_registry import ToolRegistry
from tools.database.provider import DatabaseToolProvider

async def test_stream_directly():
    """直接测试conversation_manager的流式方法"""
    print("🔧 直接测试conversation_manager...")
    
    try:
        # 初始化工具注册系统
        tool_registry = ToolRegistry()
        db_provider = DatabaseToolProvider()
        tool_registry.register_provider(db_provider)
        print("✅ 工具注册表初始化成功")
        
        # 初始化对话管理器
        conversation_manager = ConversationManager("conversations.db")
        conversation_manager.tool_registry = tool_registry
        print("✅ 获取conversation_manager成功")
        
        # 测试流式方法
        print("\n" + "="*60)
        print("🚀 开始流式对话")
        print("📝 用户输入: 我一共有多少个卫星？")
        print("="*60)
        
        step_count = 0
        current_step_type = None
        
        import time
        session_id = f"debug_test_{int(time.time())}"  # 使用时间戳生成唯一session_id
        async for event in conversation_manager.run_conversation_stream(
            user_input="我一共有多少个卫星？",
            session_id=session_id,
            max_steps=10
        ):

            event_type = event.get("type", "unknown")
            
            if event_type == "step":
                step_count += 1
                data = event.get("data", {})
                step_type = data.get("step_type", "unknown")
                current_step_type = step_type
                
                print(f"\n🔄 【第 {step_count} 轮】 - {step_type.upper()}")
                print("-" * 40)
                
                if step_type == "reasoning":
                    print(f"🧠 思考: {data.get('thought', 'N/A')}")
                    if 'analysis' in data:
                        print(f"📊 分析: {data.get('analysis', 'N/A')}")
                    if 'plan' in data:
                        print(f"📋 计划: {data.get('plan', 'N/A')}")
                        
                elif step_type == "action":
                    print(f"🧠 思考: {data.get('thought', 'N/A')}")
                    print(f"🔧 执行工具: {data.get('action', 'N/A')}")
                    print(f"📥 参数: {data.get('args', {})}")
                    
                elif step_type == "finish":
                    print(f"🧠 思考: {data.get('thought', 'N/A')}")

                    answer = data.get('answer', 'N/A')
                    if answer and answer != 'N/A':
                        # 如果答案很长，进行格式化显示
                        if len(str(answer)) > 100:
                            print(f"✅ 最终答案:")
                            print(f"   {answer}")
                        else:
                            print(f"✅ 最终答案: {answer}")
                    else:
                        print(f"✅ 最终答案: N/A")
                    print(f"📝 完成理由: {data.get('rationale', 'N/A')}")
                    
            elif event_type == "observation":
                data = event.get("data", {})
                print(f"👁️ 观察结果:")
                print(f"   工具: {data.get('action', 'N/A')}")
                observation = data.get('observation', {})
                if isinstance(observation, dict):
                    if observation.get('ok'):
                        print(f"   ✅ 成功: {observation.get('data', {}).get('summary', '执行成功')}")
                    else:
                        print(f"   ❌ 失败: {observation.get('error', '未知错误')}")
                else:
                    print(f"   📄 结果: {observation}")
                    
            elif event_type == "final":
                data = event.get("data", {})
                print(f"\n🎯 【最终结果】")
                print("-" * 40)
                answer = data.get('answer', 'N/A')
                if isinstance(answer, dict):
                    print(f"✅ 答案: {answer.get('answer', 'N/A')}")
                    if answer.get('rationale'):
                        print(f"📝 理由: {answer.get('rationale')}")
                else:
                    print(f"✅ 答案: {answer}")
                print(f"📊 总步骤数: {data.get('total_steps', 0)}")
                print(f"🎉 成功: {'是' if data.get('success', False) else '否'}")
                
            elif event_type == "warning":
                data = event.get("data", {})
                print(f"⚠️ 警告: {data.get('message', 'N/A')}")
                
            else:
                print(f"📡 其他事件 [{event_type}]: {event}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 流式输出直接调试")
    print("=" * 50)
    
    asyncio.run(test_stream_directly())
    
    print("\n🏁 调试完成!")