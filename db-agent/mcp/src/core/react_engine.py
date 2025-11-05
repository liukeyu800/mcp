"""ReAct推理引擎 - 专门负责ReAct架构的实现"""

import json
import os
from typing import Dict, Any, List, Optional, AsyncGenerator, TYPE_CHECKING
from datetime import datetime
import httpx

from .schemas import FlexibleDecideOut, validate_flexible_decide, get_flexible_system_prompt
from .mcp_tool_registry import MCPToolRegistry

if TYPE_CHECKING:
    from .schemas import AgentState


class ReActEngine:
    """ReAct推理引擎 - 负责思考-行动-观察循环"""
    
    def __init__(self, tool_registry: MCPToolRegistry):
        self.tool_registry = tool_registry
        
    async def execute_react_step(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """执行一个ReAct步骤
        
        Args:
            messages: 对话历史消息
            
        Returns:
            包含步骤类型和内容的字典
        """
        print(f"[ReAct Engine] 开始执行ReAct步骤，消息数量: {len(messages)}")
        
        # 调用LLM获取决策
        llm_response = await self._call_llm(messages)
        print(f"[ReAct Engine] LLM响应类型: {type(llm_response)}, 长度: {len(str(llm_response)) if llm_response else 0}")
        
        # 解析LLM响应
        try:
            print(f"[ReAct Engine] 开始解析LLM响应...")
            if isinstance(llm_response, str):
                response_dict = self._extract_json_from_response(llm_response)
                print(f"[ReAct Engine] [SUCCESS] JSON提取成功: {response_dict.keys()}")
            else:
                response_dict = llm_response
                print(f"[ReAct Engine] 响应已是字典格式")
            
            decision = validate_flexible_decide(response_dict)
            print(f"[ReAct Engine] [SUCCESS] 决策验证成功: step_type={decision.step_type}")
            if decision.step_type == "action":
                print(f"[ReAct Engine]   - 行动: {decision.action}")
                print(f"[ReAct Engine]   - 参数: {decision.args}")
            elif decision.step_type == "finish":
                print(f"[ReAct Engine]   - 答案长度: {len(decision.answer) if decision.answer else 0} 字符")
        except Exception as e:
            print(f"[ReAct Engine] [ERROR] 响应解析失败: {type(e).__name__}: {e}")
            print(f"[ReAct Engine] 原始响应（前500字符）: {str(llm_response)[:500]}")
            # 返回错误类型，让协调器可以将错误信息添加到对话历史并重试
            return {
                "type": "error",
                "data": {
                    "error": f"JSON解析失败: {str(e)}",
                    "error_type": "json_parse_error",
                    "raw_response": str(llm_response)[:1000],  # 保存原始响应供LLM参考
                    "thought": "LLM响应格式不正确，需要重新生成符合JSON格式的响应"
                }
            }
        
        # 根据决策类型执行相应操作
        if decision.step_type == "reasoning":
            return await self._handle_reasoning_step(decision)
        elif decision.step_type == "action":
            return await self._handle_action_step(decision)
        elif decision.step_type == "finish":
            return await self._handle_finish_step(decision, messages)
        else:
            # 未知步骤类型，默认完成
            return {
                "type": "finish",
                "data": {
                    "answer": "处理完成",
                    "rationale": "未知步骤类型"
                }
            }
    
    async def _handle_reasoning_step(self, decision: FlexibleDecideOut) -> Dict[str, Any]:
        """处理推理步骤"""
        return {
            "type": "reasoning",
            "data": {
                "thought": decision.thought,
                "analysis": decision.analysis,
                "plan": decision.plan
            }
        }
    
    async def _handle_action_step(self, decision: FlexibleDecideOut) -> Dict[str, Any]:
        """处理行动步骤"""
        tool_name = decision.action
        tool_params = decision.args or {}
        
        print(f"[ReAct Engine] 准备执行工具: {tool_name}")
        print(f"[ReAct Engine] 工具参数: {tool_params}")
        
        try:
            # 执行工具
            tool_result = await self.tool_registry.execute_tool(tool_name, **tool_params)
            print(f"[ReAct Engine] [SUCCESS] 工具执行成功: {tool_name}")
            print(f"[ReAct Engine] 结果类型: {type(tool_result)}")
            
            return {
                "type": "action",
                "data": {
                    "thought": decision.thought,
                    "tool_name": tool_name,
                    "parameters": tool_params,
                    "result": tool_result
                }
            }
        except Exception as e:
            print(f"[ReAct Engine] [ERROR] 工具执行失败: {tool_name}")
            print(f"[ReAct Engine] 错误: {type(e).__name__}: {e}")
            import traceback
            print(f"[ReAct Engine] 异常堆栈: {traceback.format_exc()}")
            
            return {
                "type": "error",
                "data": {
                    "thought": decision.thought,
                    "tool_name": tool_name,
                    "error": str(e)
                }
            }
    
    async def _handle_finish_step(self, decision: FlexibleDecideOut, messages: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """处理完成步骤
        
        Args:
            decision: 决策结果
            messages: 对话历史（用于检查用户要求）
        """
        # 检查用户是否要求举例/展示，但未查询实际数据
        if messages:
            user_queries = [msg.get("content", "") for msg in messages if msg.get("role") == "user"]
            last_user_query = user_queries[-1] if user_queries else ""
            
            # 检查是否包含需要实际数据的关键词
            requires_data_keywords = ["举例", "举例子", "展示", "列出", "有哪些", "包含哪些数据", "具体数据", "数据内容"]
            requires_data = any(keyword in last_user_query for keyword in requires_data_keywords)
            
            if requires_data:
                # 检查是否已执行过数据查询工具（sample_rows或run_sql）
                has_data_query = False
                
                # 从后往前查找，找到最近的用户查询后的所有消息
                last_user_idx = -1
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        last_user_idx = i
                        break
                
                # 检查从最后一次用户查询后的消息中是否有数据查询
                for msg in messages[last_user_idx + 1:]:
                    content = msg.get("content", "")
                    # 检查是否有sample_rows或run_sql的观察结果
                    if "观察:" in content:
                        obs_content = content.replace("观察:", "").strip()
                        try:
                            import json
                            obs_data = json.loads(obs_content)
                            # 检查是否是sample_rows或run_sql的结果
                            if isinstance(obs_data, dict):
                                # 检查是否有数据行（sample_rows和run_sql的特征）
                                has_rows = "rows" in obs_data or "sample_rows" in obs_data
                                has_data = "data" in obs_data and isinstance(obs_data.get("data"), list)
                                # 或者检查观察结果中是否包含实际的卫星/数据信息
                                obs_str = json.dumps(obs_data, ensure_ascii=False)
                                # 如果包含aircraft_id、aircraft_name等实际数据字段，说明有数据
                                has_actual_data = any(keyword in obs_str for keyword in 
                                    ["aircraft_id", "aircraft_name", "aircraft_code", "rows", "sample_rows"])
                                
                                if has_rows or has_data or has_actual_data:
                                    has_data_query = True
                                    print(f"[ReAct Engine] 检测到已执行数据查询工具")
                                    break
                        except:
                            pass
                    
                    # 也检查助手消息中是否有工具执行提示
                    if msg.get("role") == "assistant" and ("行动:" in content or "调用工具:" in content):
                        if "sample_rows" in content or "run_sql" in content:
                            # 找到工具调用，但需要确认是否有观察结果
                            # 继续检查后续消息
                            continue
                
                if not has_data_query:
                    # 用户要求举例但未查询数据，拒绝finish
                    print(f"[ReAct Engine] [WARNING] 用户要求举例但未查询实际数据，拒绝finish")
                    return {
                        "type": "error",
                        "data": {
                            "error": "用户要求举例或展示数据，但尚未查询实际数据。必须先使用 sample_rows 或 run_sql 查询实际数据后才能回答。",
                            "error_type": "premature_finish",
                            "thought": "需要先查询实际数据才能回答用户的问题",
                            "suggestion": "请使用 sample_rows 或 run_sql 工具查询实际数据"
                        }
                    }
        
        return {
            "type": "finish",
            "data": {
                "thought": decision.thought,
                "answer": decision.answer,
                "rationale": decision.rationale
            }
        }
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用LLM获取推理结果"""
        # 从环境变量读取LLM配置
        llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        
        if llm_provider == "ollama":
            # 使用Ollama配置
            ollama_base = os.getenv("OLLAMA_BASE", "http://localhost:11434")
            llm_api_url = f"{ollama_base}/v1/chat/completions"
            llm_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        else:
            # 使用通用配置
            llm_api_url = os.getenv("LLM_API_URL", "http://localhost:11434/v1/chat/completions")
            llm_model = os.getenv("LLM_MODEL", "qwen2.5:7b")
        
        llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        llm_timeout = int(os.getenv("LLM_TIMEOUT", "60"))  # 增加默认超时到60秒
        
        print(f"[ReAct Engine] LLM Config - URL: {llm_api_url}, Model: {llm_model}")
        
        try:
            # 禁用代理以避免连接问题
            old_http_proxy = os.environ.get('HTTP_PROXY')
            old_https_proxy = os.environ.get('HTTPS_PROXY')
            old_http_proxy_lower = os.environ.get('http_proxy')
            old_https_proxy_lower = os.environ.get('https_proxy')
            
            print(f"[ReAct Engine] 原始代理设置: HTTP_PROXY={old_http_proxy}, http_proxy={old_http_proxy_lower}")
            
            # 临时清除代理环境变量
            proxies_cleared = []
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
                proxies_cleared.append('HTTP_PROXY')
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']
                proxies_cleared.append('HTTPS_PROXY')
            if 'http_proxy' in os.environ:
                del os.environ['http_proxy']
                proxies_cleared.append('http_proxy')
            if 'https_proxy' in os.environ:
                del os.environ['https_proxy']
                proxies_cleared.append('https_proxy')
            
            if proxies_cleared:
                print(f"[ReAct Engine] 已清除代理: {', '.join(proxies_cleared)}")
            else:
                print(f"[ReAct Engine] 未检测到代理设置")
            
            try:
                # trust_env=False 禁用从系统读取代理设置
                async with httpx.AsyncClient(timeout=llm_timeout, trust_env=False) as client:
                    print(f"[ReAct Engine] 正在调用LLM: {llm_api_url}")
                    print(f"[ReAct Engine] 请求参数: model={llm_model}, temperature={llm_temperature}, max_tokens={llm_max_tokens}")
                    
                    response = await client.post(
                        llm_api_url,
                        json={
                            "model": llm_model,
                            "messages": messages,
                            "temperature": llm_temperature,
                            "max_tokens": llm_max_tokens,
                            "stream": False
                        }
                    )
                    
                print(f"[ReAct Engine] [SUCCESS] HTTP状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    llm_response = result["choices"][0]["message"]["content"]
                    print(f"[ReAct Engine] [SUCCESS] LLM响应成功")
                    print(f"[ReAct Engine] 响应内容（前200字符）: {llm_response[:200] if len(llm_response) > 200 else llm_response}")
                    print(f"[ReAct Engine] 完整响应长度: {len(llm_response)} 字符")
                    return llm_response
                else:
                    print(f"[ReAct Engine] [ERROR] LLM Error: HTTP {response.status_code}")
                    print(f"[ReAct Engine] 错误详情: {response.text[:500]}")
                    print(f"[ReAct Engine] 请检查LLM服务是否正常运行: {llm_api_url}")
                    return self._fallback_response(messages)
            finally:
                # 恢复代理环境变量
                if old_http_proxy:
                    os.environ['HTTP_PROXY'] = old_http_proxy
                if old_https_proxy:
                    os.environ['HTTPS_PROXY'] = old_https_proxy
                if old_http_proxy_lower:
                    os.environ['http_proxy'] = old_http_proxy_lower
                if old_https_proxy_lower:
                    os.environ['https_proxy'] = old_https_proxy_lower
                    
        except httpx.TimeoutException as e:
            print(f"[ReAct Engine] [ERROR] LLM请求超时: {e}")
            print(f"[ReAct Engine] 超时设置: {llm_timeout}秒")
            print(f"[ReAct Engine] 建议: 增加LLM_TIMEOUT环境变量或检查网络")
            return self._fallback_response(messages)
        except httpx.ConnectError as e:
            print(f"[ReAct Engine] [ERROR] LLM连接错误: {e}")
            print(f"[ReAct Engine] 目标地址: {llm_api_url}")
            print(f"[ReAct Engine] 建议: 检查LLM服务是否运行，或检查代理设置")
            return self._fallback_response(messages)
        except Exception as e:
            print(f"[ReAct Engine] [ERROR] LLM调用异常: {type(e).__name__}: {e}")
            import traceback
            print(f"[ReAct Engine] 异常堆栈: {traceback.format_exc()}")
            return self._fallback_response(messages)
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """从LLM响应中提取有效的JSON对象
        
        支持多种格式：
        1. 纯JSON对象
        2. JSON对象前有文本（如"已经完成\n\n\n{...}"）
        3. JSON对象后有文本
        4. JSON对象被包裹在markdown代码块中
        """
        import re
        
        if not response or not response.strip():
            raise ValueError("响应为空，无法提取JSON")
        
        # 首先尝试直接解析整个响应
        try:
            parsed = json.loads(response.strip())
            if self._is_valid_decision(parsed):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # 尝试提取markdown代码块中的JSON
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        code_matches = re.findall(code_block_pattern, response, re.DOTALL)
        for match in code_matches:
            try:
                json_obj = json.loads(match.strip())
                if self._is_valid_decision(json_obj):
                    return json_obj
            except json.JSONDecodeError:
                continue
        
        # 尝试查找最长的JSON对象（使用括号匹配）
        # 从后往前查找，找到第一个{，然后尝试匹配到对应的}
        depth = 0
        start_pos = -1
        for i in range(len(response) - 1, -1, -1):
            if response[i] == '}':
                depth += 1
            elif response[i] == '{':
                if depth == 0:
                    start_pos = i
                    # 尝试从这个位置开始，找到匹配的结束位置
                    depth = 1
                    end_pos = i + 1
                    while end_pos < len(response) and depth > 0:
                        if response[end_pos] == '{':
                            depth += 1
                        elif response[end_pos] == '}':
                            depth -= 1
                        end_pos += 1
                    
                    if depth == 0:
                        # 找到了匹配的JSON对象
                        candidate = response[start_pos:end_pos]
                        try:
                            json_obj = json.loads(candidate)
                            if self._is_valid_decision(json_obj):
                                return json_obj
                        except json.JSONDecodeError:
                            pass
                    depth = 0
                else:
                    depth -= 1
        
        # 使用递归下降方法查找嵌套的JSON对象
        # 查找所有可能的JSON对象（使用更复杂的正则）
        # 匹配嵌套的JSON结构
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\})*)*\}))*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        # 按长度降序排序，优先尝试更长的匹配（可能是完整的JSON）
        matches.sort(key=len, reverse=True)
        
        for match in matches:
            try:
                json_obj = json.loads(match)
                if self._is_valid_decision(json_obj):
                    return json_obj
            except json.JSONDecodeError:
                continue
        
        # 最后的尝试：查找包含step_type字段的JSON对象
        # 使用更宽松的匹配，允许不完整的JSON
        step_type_pattern = r'\{[^}]*"step_type"[^}]*\}'
        step_matches = re.findall(step_type_pattern, response, re.DOTALL)
        for match in step_matches:
            try:
                # 尝试修复常见的JSON格式问题
                fixed_match = match
                # 如果缺少引号，尝试添加
                if '"step_type"' not in fixed_match and "'step_type'" in fixed_match:
                    fixed_match = fixed_match.replace("'", '"')
                
                json_obj = json.loads(fixed_match)
                if self._is_valid_decision(json_obj):
                    return json_obj
            except json.JSONDecodeError:
                continue
        
        # 如果都失败了，输出详细信息并抛出异常
        print(f"[ReAct Engine] 无法从响应中提取有效JSON")
        print(f"[ReAct Engine] 原始响应长度: {len(response)} 字符")
        print(f"[ReAct Engine] 原始响应（前500字符）: {response[:500]}")
        print(f"[ReAct Engine] 原始响应（后500字符）: {response[-500:] if len(response) > 500 else response}")
        raise ValueError(f"无法从响应中提取有效的JSON对象")
    
    def _is_valid_decision(self, obj: Dict[str, Any]) -> bool:
        """验证决策对象是否有效"""
        if 'step_type' not in obj:
            return False
        
        step_type = obj.get('step_type')
        
        # reasoning类型：可以只有step_type
        if step_type == 'reasoning':
            return True
        
        # action类型：必须有action字段
        if step_type == 'action':
            return 'action' in obj
        
        # finish类型：必须有answer字段
        if step_type == 'finish':
            return 'answer' in obj
        
        return False
    
    def _fallback_response(self, messages: List[Dict[str, str]]) -> str:
        """当LLM不可用时的后备响应"""
        return json.dumps({
            "thought": "LLM服务暂时不可用，无法进行智能推理。",
            "step_type": "finish",
            "answer": "抱歉，LLM服务暂时不可用，无法处理您的请求。请检查以下配置：\n\n1. 确认LLM服务正在运行\n2. 检查环境变量配置：\n   - OLLAMA_BASE: 当前配置为 " + os.getenv("OLLAMA_BASE", "未配置") + "\n   - OLLAMA_MODEL: 当前配置为 " + os.getenv("OLLAMA_MODEL", "未配置") + "\n\n请联系管理员或稍后重试。",
            "rationale": "LLM服务连接失败"
        }, ensure_ascii=False)
    
    def build_system_message(self, state: Optional['AgentState'] = None) -> Dict[str, str]:
        """构建系统消息
        
        Args:
            state: 可选的AgentState，用于包含已知表信息
        """
        base_prompt = get_flexible_system_prompt()
        
        # 从工具注册系统动态生成工具列表
        tools = self.tool_registry.get_all_tools()
        if tools:
            tools_section = ""
            for i, tool in enumerate(tools, 1):
                tools_section += f"{i}. **{tool.name}**: {tool.description}\n"
                # 如果有参数信息，添加参数说明
                if tool.parameters:
                    # 参数可能是直接字典格式或JSON Schema格式
                    params = tool.parameters
                    if isinstance(params, dict) and "properties" in params:
                        # JSON Schema格式
                        params = params["properties"]
                    
                    if params and isinstance(params, dict):
                        param_list = []
                        for param_name, param_info in params.items():
                            if isinstance(param_info, dict):
                                param_type = param_info.get("type", "string")
                                param_desc = param_info.get("description", "")
                                # 检查是否必需：如果有default值或required=False，则为可选
                                has_default = "default" in param_info
                                required = param_info.get("required", not has_default)
                                param_str = f"{param_name} ({param_type})"
                                if param_desc:
                                    param_str += f": {param_desc}"
                                if has_default:
                                    default_val = param_info.get("default")
                                    param_str += f" [默认: {default_val}]"
                                elif not required:
                                    param_str += " [可选]"
                                param_list.append(param_str)
                            else:
                                param_list.append(f"{param_name}")
                        
                        if param_list:
                            tools_section += "   - 参数: " + ", ".join(param_list) + "\n"
            
            # 替换工具列表部分
            # 查找"## 可用工具"后的内容并替换
            import re
            pattern = r'## 可用工具\n\n(.*?)(?=\n## |$)'
            replacement = f"## 可用工具\n\n{tools_section.strip()}"
            base_prompt = re.sub(pattern, replacement, base_prompt, flags=re.DOTALL)
        
        # 如果有状态信息，增强提示词
        if state and (state.known_tables or state.known_schemas):
            context_info = "\n\n## 当前已知信息\n\n"
            
            if state.known_tables:
                context_info += f"**已知表列表**: {', '.join(state.known_tables)}\n\n"
            
            if state.known_schemas:
                context_info += "**已知表结构**:\n"
                for table_name, schema in state.known_schemas.items():
                    columns = schema.get("columns", [])
                    if isinstance(columns, list):
                        column_names = [col.get("name", col) if isinstance(col, dict) else str(col) for col in columns[:5]]
                        context_info += f"- {table_name}: {', '.join(column_names)}"
                        if len(columns) > 5:
                            context_info += f" (共{len(columns)}个字段)"
                        context_info += "\n"

            
            base_prompt += context_info
        
        return {
            "role": "system", 
            "content": base_prompt
        }
    
    def build_observation_message(self, tool_name: str, tool_result: Any) -> Dict[str, str]:
        """构建观察消息"""
        # 处理工具结果：如果已经是字符串（可能是JSON字符串），直接使用
        # 如果是字典，转换为JSON字符串
        # 如果是其他类型，转换为字符串
        if isinstance(tool_result, str):
            # 如果已经是字符串，检查是否是有效的JSON
            try:
                # 尝试解析，如果成功说明是JSON字符串，直接使用
                json.loads(tool_result)
                content = tool_result
            except json.JSONDecodeError:
                # 如果不是JSON字符串，转换为JSON格式
                content = json.dumps({"raw": tool_result}, ensure_ascii=False)
        elif isinstance(tool_result, dict):
            # 如果是字典，转换为JSON字符串
            content = json.dumps(tool_result, ensure_ascii=False)
        else:
            # 其他类型，转换为JSON字符串
            content = json.dumps(tool_result, ensure_ascii=False, default=str)
        
        return {
            "role": "user",
            "content": f"观察: {content}"
        }
