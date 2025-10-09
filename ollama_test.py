#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama服务器连接测试工具
用于测试局域网内Ollama服务器的连接状态和性能
"""

import requests
import json
import time
import sys
import socket
import subprocess
import platform
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import statistics

# 连接配置
LLM_BINDING = "ollama"
LLM_MODEL = "gpt-oss:20b"
LLM_BINDING_HOST = "http://121.195.154.220"
OLLAMA_PORT = 80
OLLAMA_URL = f"{LLM_BINDING_HOST}:{OLLAMA_PORT}"

class NetworkDiagnostics:
    """网络诊断工具"""
    
    @staticmethod
    def ping_host(host: str, timeout: int = 5) -> Tuple[bool, str, float]:
        """Ping测试主机连通性"""
        try:
            # 根据操作系统选择ping命令
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", "1", "-W", str(timeout), host]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            end_time = time.time()
            
            ping_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            if result.returncode == 0:
                return True, "Ping成功", ping_time
            else:
                return False, f"Ping失败: {result.stderr.strip()}", ping_time
                
        except subprocess.TimeoutExpired:
            return False, f"Ping超时 (>{timeout}秒)", timeout * 1000
        except Exception as e:
            return False, f"Ping错误: {str(e)}", 0
    
    @staticmethod
    def check_port(host: str, port: int, timeout: int = 5) -> Tuple[bool, str, float]:
        """检查端口连通性"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            end_time = time.time()
            
            sock.close()
            connect_time = (end_time - start_time) * 1000
            
            if result == 0:
                return True, f"端口 {port} 开放", connect_time
            else:
                return False, f"端口 {port} 关闭或不可达", connect_time
                
        except socket.gaierror as e:
            return False, f"DNS解析失败: {str(e)}", 0
        except Exception as e:
            return False, f"端口检测错误: {str(e)}", 0
    
    @staticmethod
    def get_troubleshooting_suggestions(host: str, port: int, ping_success: bool, port_open: bool) -> List[str]:
        """获取故障排除建议"""
        suggestions = []
        
        if not ping_success:
            suggestions.extend([
                "🔍 主机不可达，请检查：",
                "  • 确认服务器IP地址是否正确",
                "  • 检查网络连接是否正常",
                "  • 确认服务器是否在线",
                "  • 检查防火墙是否阻止了ICMP包",
                "  • 尝试使用其他网络或VPN连接"
            ])
        elif not port_open:
            suggestions.extend([
                f"🔍 主机可达但端口 {port} 不可用，请检查：",
                "  • 确认Ollama服务是否已启动",
                f"  • 检查Ollama是否监听在端口 {port}",
                "  • 确认服务器防火墙是否开放了该端口",
                "  • 检查网络防火墙或路由器设置",
                "  • 尝试使用telnet或nc命令测试端口连通性"
            ])
        else:
            suggestions.extend([
                "✅ 网络连接正常，但Ollama API不响应，请检查：",
                "  • Ollama服务是否正确配置",
                "  • API端点路径是否正确 (/api/tags)",
                "  • 服务是否处于健康状态",
                "  • 查看Ollama服务日志获取详细错误信息"
            ])
        
        suggestions.extend([
            "",
            "💡 额外建议：",
            f"  • 在服务器上运行: curl http://localhost:{port}/api/tags",
            "  • 检查Ollama配置文件中的绑定地址",
            "  • 确认模型文件是否正确加载",
            "  • 尝试重启Ollama服务"
        ])
        
        return suggestions

class OllamaTestClient:
    """Ollama测试客户端"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()
        self.session.timeout = 30
        
    def check_connection(self) -> Tuple[bool, str]:
        """检查Ollama服务器连接状态"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                if self.model in model_names:
                    return True, f"连接成功，模型 {self.model} 可用"
                else:
                    return False, f"连接成功但模型 {self.model} 不可用。可用模型: {model_names}"
            else:
                return False, f"服务器响应错误: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"连接失败: {str(e)}"
    
    def generate_response(self, prompt: str, stream: bool = False) -> Tuple[Optional[str], float, Dict]:
        """生成响应并测量性能"""
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2000
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                
                # 性能统计
                stats = {
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'response_length': len(generated_text),
                    'tokens_per_second': len(generated_text.split()) / response_time if response_time > 0 else 0,
                    'success': True
                }
                
                return generated_text, response_time, stats
            else:
                stats = {
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'success': False
                }
                return None, response_time, stats
                
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            response_time = end_time - start_time
            stats = {
                'response_time': response_time,
                'error': str(e),
                'success': False
            }
            return None, response_time, stats

class OllamaTestSuite:
    """Ollama测试套件"""
    
    def __init__(self, client: OllamaTestClient):
        self.client = client
        self.test_results = []
        
    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("=" * 80)
        print(f"🚀 开始Ollama服务器测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📡 服务器地址: {self.client.base_url}")
        print(f"🤖 测试模型: {self.client.model}")
        print("=" * 80)
        
        # 0. 网络诊断
        print("\n🔍 0. 网络连接诊断...")
        host = self.client.base_url.replace("http://", "").replace("https://", "").split(":")[0]
        port = int(self.client.base_url.split(":")[-1]) if ":" in self.client.base_url.split("//")[1] else 80
        
        # Ping测试
        ping_success, ping_msg, ping_time = NetworkDiagnostics.ping_host(host)
        print(f"   Ping测试: {'✅' if ping_success else '❌'} {ping_msg} ({ping_time:.1f}ms)")
        
        # 端口测试
        port_open, port_msg, connect_time = NetworkDiagnostics.check_port(host, port)
        print(f"   端口测试: {'✅' if port_open else '❌'} {port_msg} ({connect_time:.1f}ms)")
        
        # 1. 连接测试
        print("\n🔍 1. Ollama API连接测试...")
        is_connected, connection_msg = self.client.check_connection()
        print(f"   {connection_msg}")
        
        if not is_connected:
            print("\n❌ 连接失败，以下是故障排除建议：")
            suggestions = NetworkDiagnostics.get_troubleshooting_suggestions(host, port, ping_success, port_open)
            for suggestion in suggestions:
                print(f"   {suggestion}")
            
            return {
                "success": False, 
                "error": connection_msg,
                "diagnostics": {
                    "ping_success": ping_success,
                    "ping_message": ping_msg,
                    "ping_time": ping_time,
                    "port_open": port_open,
                    "port_message": port_msg,
                    "connect_time": connect_time,
                    "suggestions": suggestions
                }
            }
        
        # 2. 运行复杂测试问题
        test_questions = self._get_test_questions()
        
        print(f"\n📝 2. 开始执行 {len(test_questions)} 个复杂测试问题...")
        
        for i, (category, question) in enumerate(test_questions, 1):
            print(f"\n   测试 {i}/{len(test_questions)} - {category}")
            print(f"   问题: {question[:100]}{'...' if len(question) > 100 else ''}")
            
            response, response_time, stats = self.client.generate_response(question)
            
            test_result = {
                'test_id': i,
                'category': category,
                'question': question,
                'response': response,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results.append(test_result)
            
            if stats['success']:
                print(f"   ✅ 响应时间: {response_time:.2f}秒")
                print(f"   📊 响应长度: {stats['response_length']} 字符")
                print(f"   ⚡ 处理速度: {stats['tokens_per_second']:.1f} 词/秒")
            else:
                print(f"   ❌ 测试失败: {stats.get('error', '未知错误')}")
        
        # 3. 生成测试报告
        return self._generate_report()
    
    def _get_test_questions(self) -> List[Tuple[str, str]]:
        """获取5个复杂测试问题"""
        return [
            ("逻辑推理", 
             """有一个古老的逻辑谜题：在一个小镇上，有一位理发师，他只给那些不给自己理发的人理发。
             请分析这个悖论的逻辑结构，解释为什么这是一个自相矛盾的陈述，并提出至少三种可能的解决方案。
             同时，请将这个问题与罗素悖论进行比较，说明它们在数学逻辑中的意义。"""),
            
            ("创意写作", 
             """请创作一个科幻短故事（500-800字），故事背景设定在2080年，人类已经实现了意识上传技术。
             主角是一名数据考古学家，专门研究被遗忘的数字文明遗迹。故事要包含以下元素：
             1. 一个关于人工智能觉醒的秘密
             2. 时间悖论的概念
             3. 对人性本质的深度思考
             请确保故事有完整的情节结构和深刻的哲学内涵。"""),
            
            ("数据分析", 
             """假设你是一名数据科学家，需要分析一个电商平台的用户行为数据。给定以下信息：
             - 平台有100万活跃用户
             - 平均每用户每月访问15次
             - 转化率为3.2%
             - 平均订单价值为156元
             - 用户留存率：1个月85%，3个月62%，12个月34%
             
             请设计一个完整的分析框架来：
             1. 识别高价值用户群体
             2. 预测用户流失风险
             3. 制定个性化营销策略
             4. 估算不同策略的ROI
             并解释你的分析方法和预期结果。"""),
            
            ("技术架构", 
             """设计一个支持千万级用户的实时聊天系统架构。系统需要满足以下要求：
             1. 支持文本、图片、语音、视频消息
             2. 消息送达率99.9%以上
             3. 消息延迟小于100ms
             4. 支持群聊（最多1000人）
             5. 消息加密和隐私保护
             6. 跨平台兼容（Web、iOS、Android）
             
             请详细说明：
             - 整体架构设计（包括微服务拆分）
             - 数据库设计和分片策略
             - 消息队列和实时通信方案
             - 负载均衡和容灾机制
             - 安全和隐私保护措施
             - 性能优化策略"""),
            
            ("哲学思辨", 
             """探讨人工智能时代的伦理问题：当AI系统的决策能力超越人类时，我们应该如何定义责任和道德？
             
             请从以下角度进行深入分析：
             1. 道德主体性：AI是否可以成为道德主体？
             2. 责任归属：AI造成的伤害应该由谁承担责任？
             3. 决策透明度：AI的"黑盒"决策是否违背了道德原则？
             4. 人类尊严：AI的超越是否威胁到人类的内在价值？
             5. 未来社会：在AI主导的社会中，人类的角色是什么？
             
             请结合具体案例，提出你的观点和解决方案，并考虑不同文化背景下的伦理差异。""")
        ]
    
    def _generate_report(self) -> Dict:
        """生成详细的测试报告"""
        successful_tests = [r for r in self.test_results if r['stats']['success']]
        failed_tests = [r for r in self.test_results if not r['stats']['success']]
        
        if successful_tests:
            response_times = [r['stats']['response_time'] for r in successful_tests]
            response_lengths = [r['stats']['response_length'] for r in successful_tests]
            tokens_per_second = [r['stats']['tokens_per_second'] for r in successful_tests]
            
            performance_stats = {
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': statistics.median(response_times),
                'avg_response_length': statistics.mean(response_lengths),
                'avg_tokens_per_second': statistics.mean(tokens_per_second)
            }
        else:
            performance_stats = {}
        
        report = {
            'success': len(failed_tests) == 0,
            'total_tests': len(self.test_results),
            'successful_tests': len(successful_tests),
            'failed_tests': len(failed_tests),
            'success_rate': len(successful_tests) / len(self.test_results) * 100,
            'performance_stats': performance_stats,
            'test_results': self.test_results,
            'timestamp': datetime.now().isoformat()
        }
        
        self._print_report(report)
        return report
    
    def _print_report(self, report: Dict):
        """打印测试报告"""
        print("\n" + "=" * 80)
        print("📊 测试报告")
        print("=" * 80)
        
        print(f"🎯 总体结果: {'✅ 全部通过' if report['success'] else '❌ 部分失败'}")
        print(f"📈 成功率: {report['success_rate']:.1f}% ({report['successful_tests']}/{report['total_tests']})")
        
        if report['performance_stats']:
            stats = report['performance_stats']
            print(f"\n⚡ 性能统计:")
            print(f"   平均响应时间: {stats['avg_response_time']:.2f}秒")
            print(f"   响应时间范围: {stats['min_response_time']:.2f}s - {stats['max_response_time']:.2f}s")
            print(f"   中位响应时间: {stats['median_response_time']:.2f}秒")
            print(f"   平均响应长度: {stats['avg_response_length']:.0f} 字符")
            print(f"   平均处理速度: {stats['avg_tokens_per_second']:.1f} 词/秒")
        
        print(f"\n📝 详细结果:")
        for result in report['test_results']:
            status = "✅" if result['stats']['success'] else "❌"
            print(f"   {status} {result['category']}: {result['stats'].get('response_time', 0):.2f}秒")
            if not result['stats']['success']:
                print(f"      错误: {result['stats'].get('error', '未知错误')}")
        
        print("\n" + "=" * 80)

def main():
    """主函数"""
    try:
        # 创建测试客户端
        client = OllamaTestClient(OLLAMA_URL, LLM_MODEL)
        
        # 创建测试套件
        test_suite = OllamaTestSuite(client)
        
        # 运行测试
        results = test_suite.run_all_tests()
        
        # 保存结果到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"ollama_test_results_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 测试结果已保存到: {result_file}")
        
        # 返回退出码
        sys.exit(0 if results['success'] else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()