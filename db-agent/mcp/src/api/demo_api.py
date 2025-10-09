"""
演示页面相关API路由
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/", response_class=HTMLResponse)
async def demo_page():
    """演示页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Database Agent MCP Demo</title>
        <script src="https://unpkg.com/echarts@5.4.3/dist/echarts.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.3/echarts.min.js" onerror="console.error('备用CDN也无法加载ECharts')"></script>
        <script>
            // 页面加载完成后检查ECharts
            window.addEventListener('load', function() {
                if (typeof echarts === 'undefined') {
                    console.error('所有CDN都无法加载ECharts库');
                    // 尝试本地加载或显示错误信息
                    const errorDiv = document.createElement('div');
                    errorDiv.style.cssText = 'position: fixed; top: 10px; right: 10px; background: #ff4444; color: white; padding: 10px; border-radius: 5px; z-index: 9999;';
                    errorDiv.textContent = 'ECharts库加载失败，图表功能不可用';
                    document.body.appendChild(errorDiv);
                } else {
                    console.log('ECharts库加载成功，版本:', echarts.version);
                }
            });
        </script>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .tool-section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .tool-title { color: #333; margin-bottom: 15px; font-size: 1.2em; }
            button { padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; transition: background 0.3s; }
            button:hover { background: #0056b3; }
            button:disabled { background: #6c757d; cursor: not-allowed; }
            .result { margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 5px; white-space: pre-wrap; max-height: 400px; overflow-y: auto; border: 1px solid #e9ecef; }
            .sql-input, .chat-input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; }
            .chat-input { font-family: Arial, sans-serif; resize: vertical; }
            
            /* 流式输出样式 */
            .stream-container { display: flex; gap: 20px; }
            .stream-left { flex: 1; }
            .stream-right { flex: 1; }
            .step-item { margin: 10px 0; padding: 12px; border-radius: 5px; border-left: 4px solid #007bff; }
            .step-thinking { background: #e3f2fd; border-left-color: #2196f3; }
            .step-action { background: #f3e5f5; border-left-color: #9c27b0; }
            .step-observation { background: #e8f5e8; border-left-color: #4caf50; }
            .step-error { background: #ffebee; border-left-color: #f44336; }
            .step-final { background: #fff3e0; border-left-color: #ff9800; }
            
            .step-header { font-weight: bold; margin-bottom: 8px; display: flex; justify-content: between; align-items: center; }
            .step-content { font-size: 0.9em; line-height: 1.4; }
            .step-index { background: #007bff; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 8px; }
            
            .loading { display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            
            .tabs { display: flex; margin-bottom: 20px; }
            .tab { padding: 10px 20px; background: #e9ecef; border: none; cursor: pointer; border-radius: 5px 5px 0 0; margin-right: 5px; }
            .tab.active { background: #007bff; color: white; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Database Agent MCP 演示</h1>
            <p>这是一个数据库代理，提供安全的数据库操作功能和智能对话：</p>
            
            <!-- 标签页 -->
            <div class="tabs">
                <button class="tab active" onclick="switchTab('tools')">🗄️ 数据库工具</button>
                <button class="tab" onclick="switchTab('charts')">📊 图表工具</button>
                <button class="tab" onclick="switchTab('chat')">🤖 智能对话</button>
                <button class="tab" onclick="switchTab('stream')">📡 流式对话</button>
            </div>
            
            <!-- 数据库工具标签页 -->
            <div id="tools-content" class="tab-content active">
                <div class="tool-section">
                    <h3 class="tool-title">🗄️ 数据库工具</h3>
                    <button onclick="callTool('list_tables', {})">列出所有表</button>
                    <button onclick="loadTables()">刷新表列表</button>
                    
                    <div style="margin-top: 15px;">
                        <h4>查看表结构:</h4>
                        <select id="tableSelect" class="sql-input" style="height: auto; padding: 8px;">
                            <option value="">请先点击"列出所有表"或"刷新表列表"</option>
                        </select>
                        <button onclick="describeSelectedTable()">查看选中表的结构</button>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <h4>查看示例数据:</h4>
                        <select id="sampleTableSelect" class="sql-input" style="height: auto; padding: 8px;">
                            <option value="">请先点击"列出所有表"或"刷新表列表"</option>
                        </select>
                        <label>
                            行数限制: <input type="number" id="sampleLimit" value="5" min="1" max="100" style="width: 80px; padding: 5px; margin-left: 10px;">
                        </label>
                        <button onclick="sampleSelectedTable()">查看选中表的示例数据</button>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <h4>执行SQL查询:</h4>
                        <textarea id="sqlInput" class="sql-input" placeholder="输入SQL查询语句..." rows="3"></textarea>
                        <button onclick="executeSql()">执行查询</button>
                    </div>
                </div>
                
                <div class="tool-section">
                    <h3 class="tool-title">📋 工具信息</h3>
                    <button onclick="listTools()">列出所有可用工具</button>
                </div>
                
                <div id="result" class="result" style="display: none;"></div>
            </div>
            
            <!-- 图表工具标签页 -->
            <div id="charts-content" class="tab-content">
                <div class="tool-section">
                    <h3 class="tool-title">📊 图表工具</h3>
                    <p>使用ECharts创建各种图表，返回可直接渲染的HTML代码：</p>
                    
                    <div style="margin-top: 15px;">
                        <h4>折线图测试:</h4>
                        <button onclick="testLineChart()">创建示例折线图</button>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <h4>饼图测试:</h4>
                        <button onclick="testPieChart()">创建示例饼图</button>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <h4>漏斗图测试:</h4>
                        <button onclick="testFunnelChart()">创建示例漏斗图</button>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <h4>自定义图表:</h4>
                        <select id="chartType" class="sql-input" style="height: auto; padding: 8px; width: 200px;">
                            <option value="line">折线图</option>
                            <option value="pie">饼图</option>
                            <option value="funnel">漏斗图</option>
                        </select>
                        <input type="text" id="chartTitle" class="sql-input" placeholder="图表标题" style="width: 200px; display: inline-block; margin-left: 10px;">
                        <button onclick="createCustomChart()">创建自定义图表</button>
                        
                        <div style="margin-top: 10px;">
                            <textarea id="chartData" class="sql-input" placeholder="输入图表数据 (JSON格式)..." rows="4"></textarea>
                        </div>
                    </div>
                    
                    <div id="chartResult" style="display: none; margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; white-space: pre-wrap; font-family: monospace; max-height: 200px; overflow-y: auto;"></div>
                    <div id="chartDisplay" style="margin-top: 20px; min-height: 400px; border: 1px solid #ddd; border-radius: 5px;"></div>
                </div>
            </div>
            
            <!-- 智能对话标签页 -->
            <div id="chat-content" class="tab-content">
                <div class="tool-section">
                    <h3 class="tool-title">🤖 智能对话</h3>
                    <p>输入您的问题，AI将自动选择合适的工具来回答：</p>
                    <textarea id="chatInput" class="chat-input" placeholder="例如：我的数据库中有哪些表？用户表的结构是什么？" rows="3"></textarea>
                    <button onclick="startChat()" id="chatBtn">开始对话</button>
                    <div id="chatResult" class="result" style="display: none;"></div>
                </div>
            </div>
            
            <!-- 流式对话标签页 -->
            <div id="stream-content" class="tab-content">
                <div class="tool-section">
                    <h3 class="tool-title">📡 流式对话 - 实时查看AI思考过程</h3>
                    <p>实时查看AI的思考过程、工具调用和推理步骤：</p>
                    <div class="stream-container">
                        <div class="stream-left">
                            <textarea id="streamInput" class="chat-input" placeholder="例如：分析用户表的数据分布情况" rows="3"></textarea>
                            <button onclick="startStreamChat()" id="streamBtn">开始流式对话</button>
                        </div>
                        <div class="stream-right">
                            <div id="streamSteps" style="max-height: 500px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: white;"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // 标签页切换
            function switchTab(tabName) {
                // 隐藏所有标签页内容
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // 显示选中的标签页
                document.getElementById(tabName + '-content').classList.add('active');
                event.target.classList.add('active');
            }
            
            // 原有的工具调用功能
            async function callTool(toolName, params) {
                for (let key in params) {
                    if (params[key] === null) {
                        return;
                    }
                }
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.textContent = '调用中...';
                
                try {
                    const response = await fetch('/tools/call', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({tool_name: toolName, parameters: params})
                    });
                    const data = await response.json();
                    resultDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultDiv.textContent = '错误: ' + error.message;
                }
            }
            
            async function executeSql() {
                const sqlInput = document.getElementById('sqlInput');
                const sql = sqlInput.value.trim();
                
                if (!sql) {
                    alert('请输入SQL查询语句');
                    return;
                }
                
                await callTool('run_sql', {query: sql});
            }
            
            async function listTools() {
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.textContent = '获取工具列表...';
                
                try {
                    const response = await fetch('/tools');
                    const data = await response.json();
                    resultDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultDiv.textContent = '错误: ' + error.message;
                }
            }
            
            // 新增的表管理功能
            async function loadTables() {
                const tableSelect = document.getElementById('tableSelect');
                const sampleTableSelect = document.getElementById('sampleTableSelect');
                const resultDiv = document.getElementById('result');
                
                try {
                    const response = await fetch('/tools/call', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({tool_name: 'list_tables', parameters: {}})
                    });
                    const data = await response.json();
                    
                    // 显示完整的响应数据用于调试
                    console.log('API响应:', data);
                    
                    // 检查不同的可能返回格式
                    let tables = [];
                    if (data.status === 'success' && data.result) {
                        if (data.result.ok && data.result.data && data.result.data.tables) {
                            // 格式1: {status: 'success', result: {ok: true, data: {tables: [...]}}}
                            tables = data.result.data.tables;
                        } else if (data.result.tables) {
                            // 格式2: {status: 'success', result: {tables: [...]}}
                            tables = data.result.tables;
                        } else if (Array.isArray(data.result)) {
                            // 格式3: {status: 'success', result: [...]}
                            tables = data.result;
                        }
                    }
                    
                    if (tables && tables.length > 0) {
                        // 清空现有选项
                        tableSelect.innerHTML = '<option value="">请选择表名</option>';
                        sampleTableSelect.innerHTML = '<option value="">请选择表名</option>';
                        
                        // 添加表名选项
                        tables.forEach(table => {
                            const option1 = document.createElement('option');
                            option1.value = table;
                            option1.textContent = table;
                            tableSelect.appendChild(option1);
                            
                            const option2 = document.createElement('option');
                            option2.value = table;
                            option2.textContent = table;
                            sampleTableSelect.appendChild(option2);
                        });
                        
                        // 显示结果
                        resultDiv.style.display = 'block';
                        resultDiv.textContent = `已加载 ${tables.length} 个表: ${tables.join(', ')}`;
                    } else {
                        resultDiv.style.display = 'block';
                        resultDiv.textContent = '刷新失败: 未找到表数据\\n完整响应: ' + JSON.stringify(data, null, 2);
                    }
                } catch (error) {
                    resultDiv.style.display = 'block';
                    resultDiv.textContent = '刷新失败: ' + error.message;
                }
            }
            
            async function describeSelectedTable() {
                const tableSelect = document.getElementById('tableSelect');
                const tableName = tableSelect.value;
                
                if (!tableName) {
                    alert('请先选择一个表');
                    return;
                }
                
                await callTool('describe_table', {table: tableName});
            }
            
            async function sampleSelectedTable() {
                const sampleTableSelect = document.getElementById('sampleTableSelect');
                const sampleLimit = document.getElementById('sampleLimit');
                const tableName = sampleTableSelect.value;
                const limit = parseInt(sampleLimit.value) || 5;
                
                if (!tableName) {
                    alert('请先选择一个表');
                    return;
                }
                
                await callTool('sample_rows', {table: tableName, limit: limit});
            }
            
            // 智能对话功能
            async function startChat() {
                const chatInput = document.getElementById('chatInput');
                const chatBtn = document.getElementById('chatBtn');
                const chatResult = document.getElementById('chatResult');
                const question = chatInput.value.trim();
                
                if (!question) {
                    alert('请输入您的问题');
                    return;
                }
                
                chatBtn.disabled = true;
                chatBtn.textContent = '处理中...';
                chatResult.style.display = 'block';
                chatResult.textContent = '正在处理您的问题...';
                
                try {
                    const response = await fetch('/conversation/plan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: question})
                    });
                    const data = await response.json();
                    
                    if (data.ok) {
                        let result = `问题: ${question}\\n\\n`;
                        
                        // 处理答案数据，确保正确显示
                        let answerText = '';
                        if (data.answer && data.answer.data) {
                            if (typeof data.answer.data === 'string') {
                                answerText = data.answer.data;
                            } else if (typeof data.answer.data === 'object') {
                                answerText = JSON.stringify(data.answer.data, null, 2);
                            } else {
                                answerText = String(data.answer.data);
                            }
                        } else {
                            answerText = '无答案数据';
                        }
                        
                        result += `答案: ${answerText}\\n\\n`;
                        result += `执行步骤 (${data.steps.length}步):\\n`;
                        data.steps.forEach((step, index) => {
                            result += `${index + 1}. ${step.thought}\\n`;
                            if (step.action && step.action !== 'reasoning') {
                                result += `   动作: ${step.action}\\n`;
                            }
                        });
                        chatResult.textContent = result;
                    } else {
                        chatResult.textContent = `错误: ${data.error || '处理失败'}`;
                    }
                } catch (error) {
                    chatResult.textContent = `错误: ${error.message}`;
                } finally {
                    chatBtn.disabled = false;
                    chatBtn.textContent = '开始对话';
                }
            }
            
            // 流式对话功能
            async function startStreamChat() {
                const streamInput = document.getElementById('streamInput');
                const streamBtn = document.getElementById('streamBtn');
                const streamSteps = document.getElementById('streamSteps');
                const question = streamInput.value.trim();
                
                if (!question) {
                    alert('请输入您的问题');
                    return;
                }
                
                streamBtn.disabled = true;
                streamBtn.textContent = '处理中...';
                streamSteps.innerHTML = '<div class="loading"></div> 正在处理您的问题...';
                
                try {
                    const response = await fetch('/conversation/plan/stream', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: question})
                    });
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    streamSteps.innerHTML = '';
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\\n');
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    displayStreamStep(data, streamSteps);
                                } catch (e) {
                                    console.error('解析流数据失败:', e);
                                }
                            }
                        }
                    }
                } catch (error) {
                    streamSteps.innerHTML = `<div class="step-error">错误: ${error.message}</div>`;
                } finally {
                    streamBtn.disabled = false;
                    streamBtn.textContent = '开始流式对话';
                }
            }
            
            function displayStreamStep(data, container) {
                const stepDiv = document.createElement('div');
                stepDiv.className = 'step-item';
                
                if (data.type === 'init') {
                    stepDiv.className += ' step-thinking';
                    stepDiv.innerHTML = `
                        <div class="step-header">
                            <span class="step-index">初始化</span>
                            开始处理问题
                        </div>
                        <div class="step-content">问题: ${data.data.question}</div>
                    `;
                } else if (data.type === 'step') {
                    const stepType = data.data.step_type || 'thinking';
                    stepDiv.className += ` step-${stepType}`;
                    
                    stepDiv.innerHTML = `
                        <div class="step-header">
                            <span class="step-index">${data.data.step_number || '?'}</span>
                            ${getStepTypeLabel(stepType)}
                        </div>
                        <div class="step-content">${data.data.content || JSON.stringify(data.data, null, 2)}</div>
                    `;
                } else if (data.type === 'complete') {
                    stepDiv.className += ' step-final';
                    stepDiv.innerHTML = `
                        <div class="step-header">
                            <span class="step-index">完成</span>
                            处理完成
                        </div>
                        <div class="step-content">对话已完成</div>
                    `;
                } else if (data.type === 'error') {
                    stepDiv.className += ' step-error';
                    stepDiv.innerHTML = `
                        <div class="step-header">
                            <span class="step-index">错误</span>
                            处理失败
                        </div>
                        <div class="step-content">${data.data.error}</div>
                    `;
                }
                
                container.appendChild(stepDiv);
                container.scrollTop = container.scrollHeight;
            }
            
            function getStepTypeLabel(stepType) {
                const labels = {
                    'thinking': '🤔 思考',
                    'action': '🔧 执行',
                    'observation': '👀 观察',
                    'error': '❌ 错误',
                    'final': '✅ 完成'
                };
                return labels[stepType] || stepType;
            }
            
            // 图表工具函数
            async function testLineChart() {
                const params = {
                    title: "销售趋势图",
                    x_data: ["1月", "2月", "3月", "4月", "5月", "6月"],
                    series_data: [
                        {
                            name: "销售额",
                            data: [120, 132, 101, 134, 90, 230]
                        },
                        {
                            name: "利润",
                            data: [20, 32, 21, 34, 19, 50]
                        }
                    ],
                    x_axis_name: "月份",
                    y_axis_name: "金额(万元)"
                };
                
                await callChartTool('create_line_chart', params);
            }
            
            async function testPieChart() {
                const params = {
                    title: "市场份额分布",
                    data: [
                        {name: "产品A", value: 335},
                        {name: "产品B", value: 310},
                        {name: "产品C", value: 234},
                        {name: "产品D", value: 135},
                        {name: "产品E", value: 148}
                    ]
                };
                
                await callChartTool('create_pie_chart', params);
            }
            
            async function testFunnelChart() {
                const params = {
                    title: "销售漏斗",
                    data: [
                        {name: "访问", value: 1000},
                        {name: "咨询", value: 800},
                        {name: "意向", value: 600},
                        {name: "下单", value: 400},
                        {name: "成交", value: 200}
                    ]
                };
                
                await callChartTool('create_funnel_chart', params);
            }
            
            async function createCustomChart() {
                const chartType = document.getElementById('chartType').value;
                const chartTitle = document.getElementById('chartTitle').value;
                const chartDataText = document.getElementById('chartData').value;
                
                if (!chartTitle) {
                    alert('请输入图表标题');
                    return;
                }
                
                if (!chartDataText) {
                    alert('请输入图表数据');
                    return;
                }
                
                try {
                    const chartData = JSON.parse(chartDataText);
                    const params = {
                        title: chartTitle,
                        ...chartData
                    };
                    
                    await callChartTool(`create_${chartType}_chart`, params);
                } catch (error) {
                    alert('数据格式错误，请输入有效的JSON格式');
                }
            }
            
            async function callChartTool(toolName, params) {
                const chartResult = document.getElementById('chartResult');
                const chartDisplay = document.getElementById('chartDisplay');
                
                chartResult.style.display = 'block';
                chartResult.textContent = '创建图表中...';
                chartDisplay.innerHTML = '';
                
                // 等待页面完全加载后再检查ECharts
                if (document.readyState !== 'complete') {
                    await new Promise(resolve => {
                        if (document.readyState === 'complete') {
                            resolve();
                        } else {
                            window.addEventListener('load', resolve);
                        }
                    });
                }
                
                // 多次检查ECharts是否加载
                let echartsLoaded = false;
                for (let i = 0; i < 10; i++) {
                    if (typeof echarts !== 'undefined') {
                        echartsLoaded = true;
                        break;
                    }
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
                
                if (!echartsLoaded) {
                    chartResult.textContent = '错误: ECharts库加载失败，请检查网络连接或刷新页面重试';
                    console.error('ECharts library failed to load');
                    return;
                }
                
                console.log('ECharts库已成功加载');
                
                try {
                    const response = await fetch('/tools/call', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({tool_name: toolName, parameters: params})
                    });
                    const data = await response.json();
                    
                    console.log('API返回数据:', data);
                    chartResult.textContent = JSON.stringify(data, null, 2);
                    
                    // 如果成功创建图表，显示图表
                    if (data.status === 'success' && data.result && data.result.ok && data.result.data && data.result.data.html) {
                        console.log('准备渲染图表HTML:', data.result.data.html);
                        
                        // 解析HTML内容
                        const htmlContent = data.result.data.html;
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(htmlContent, 'text/html');
                        
                        // 提取div元素和script内容
                        const chartDiv = doc.querySelector('div[id*="chart"]');
                        const scriptElement = doc.querySelector('script');
                        
                        if (chartDiv && scriptElement) {
                            // 清空并插入图表容器
                            chartDisplay.innerHTML = '';
                            chartDisplay.appendChild(chartDiv.cloneNode(true));
                            
                            // 确保容器可见且有尺寸
                            chartDisplay.style.display = 'block';
                            chartDisplay.style.minHeight = '400px';
                            
                            console.log('图表容器已插入，ID:', chartDiv.id);
                            
                            // 等待DOM更新后执行脚本
                            setTimeout(() => {
                                try {
                                    // 执行ECharts初始化脚本
                                    const scriptContent = scriptElement.textContent || scriptElement.innerHTML;
                                    console.log('执行图表初始化脚本');
                                    eval(scriptContent);
                                    console.log('图表初始化完成');
                                } catch (error) {
                                    console.error('图表初始化失败:', error);
                                    chartDisplay.innerHTML = '<div style="padding: 20px; color: red; text-align: center;">图表初始化失败: ' + error.message + '</div>';
                                }
                            }, 200);
                        } else {
                            console.error('无法解析图表HTML结构');
                            chartDisplay.innerHTML = '<div style="padding: 20px; color: red; text-align: center;">图表HTML格式错误</div>';
                        }
                    } else {
                        console.log('数据格式不正确或缺少HTML内容');
                        chartDisplay.innerHTML = '<div style="padding: 20px; color: orange; text-align: center;">API返回数据格式错误</div>';
                    }
                } catch (error) {
                    console.error('调用图表工具失败:', error);
                    chartResult.textContent = '错误: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content