"""图表工具提供者"""

from typing import Dict, Any, List
from core.tool_registry import BaseToolProvider, ToolInfo, ToolCategory
from .chart_tools import create_line_chart, create_pie_chart, create_funnel_chart


class ChartToolProvider(BaseToolProvider):
    """图表工具提供者"""
    
    def get_category(self) -> str:
        """获取工具类别"""
        return ToolCategory.VISUALIZATION
    
    def get_tools(self) -> List[ToolInfo]:
        """获取工具列表"""
        return [
            ToolInfo(
                name="create_line_chart",
                description="创建折线图，用于展示数据趋势",
                category=self.get_category(),
                parameters={
                    "title": {"type": "string", "description": "图表标题"},
                    "x_data": {"type": "array", "description": "X轴数据"},
                    "series_data": {"type": "array", "description": "系列数据，格式为 [{'name': '系列名', 'data': [数据列表]}]"},
                    "x_axis_name": {"type": "string", "description": "X轴名称", "default": ""},
                    "y_axis_name": {"type": "string", "description": "Y轴名称", "default": ""},
                    "width": {"type": "integer", "description": "图表宽度", "default": 800},
                    "height": {"type": "integer", "description": "图表高度", "default": 400}
                },
                handler=create_line_chart
            ),
            ToolInfo(
                name="create_pie_chart",
                description="创建饼图，用于展示数据占比",
                category=self.get_category(),
                parameters={
                    "title": {"type": "string", "description": "图表标题"},
                    "data": {"type": "array", "description": "数据，格式为 [{'name': '名称', 'value': 数值}]"},
                    "width": {"type": "integer", "description": "图表宽度", "default": 800},
                    "height": {"type": "integer", "description": "图表高度", "default": 400},
                    "radius": {"type": "string", "description": "饼图半径", "default": "50%"}
                },
                handler=create_pie_chart
            ),
            ToolInfo(
                name="create_funnel_chart",
                description="创建漏斗图（扇形图），用于展示流程转化",
                category=self.get_category(),
                parameters={
                    "title": {"type": "string", "description": "图表标题"},
                    "data": {"type": "array", "description": "数据，格式为 [{'name': '名称', 'value': 数值}]"},
                    "width": {"type": "integer", "description": "图表宽度", "default": 800},
                    "height": {"type": "integer", "description": "图表高度", "default": 400},
                    "sort_order": {"type": "string", "description": "排序方式，'ascending'或'descending'", "default": "descending"}
                },
                handler=create_funnel_chart
            )
        ]
    
    def get_system_prompt(self) -> str:
        """获取该类别工具的系统提示词"""
        return """
图表可视化工具：
- create_line_chart: 创建折线图，适用于展示时间序列数据或趋势变化
- create_pie_chart: 创建饼图，适用于展示数据的占比关系
- create_funnel_chart: 创建漏斗图，适用于展示流程转化或层级数据

所有图表工具都会返回包含ECharts配置和可直接渲染的HTML代码，前端可以直接使用返回的HTML代码进行渲染。
使用时请确保数据格式正确，图表标题清晰明确。
"""
    
    def get_domain_context(self, state: Any) -> List[Dict[str, str]]:
        """获取领域特定上下文"""
        return [
            {
                "role": "system",
                "content": "当需要将查询结果可视化时，优先考虑使用图表工具。根据数据特点选择合适的图表类型：时间序列用折线图，占比关系用饼图，流程转化用漏斗图。"
            }
        ]


def register_chart_tools(registry):
    """注册图表工具到工具注册表"""
    provider = ChartToolProvider()
    registry.register_provider(provider)
    return provider