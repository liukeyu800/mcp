"""ECharts图表工具函数模块"""

import json
from typing import Dict, Any, List, Union, Optional


def _format_success(data: Any) -> Dict[str, Any]:
    """格式化成功结果"""
    return {"ok": True, "data": data}


def _format_error(code: str, message: str) -> Dict[str, Any]:
    """格式化错误结果"""
    return {"ok": False, "error": {"code": code, "message": message}}


def create_line_chart(
    title: str,
    x_data: List[Union[str, int, float]],
    series_data: List[Dict[str, Any]],
    x_axis_name: str = "",
    y_axis_name: str = "",
    width: int = 800,
    height: int = 400
) -> Dict[str, Any]:
    """
    创建折线图
    
    Args:
        title: 图表标题
        x_data: X轴数据
        series_data: 系列数据，格式为 [{"name": "系列名", "data": [数据列表]}]
        x_axis_name: X轴名称
        y_axis_name: Y轴名称
        width: 图表宽度
        height: 图表高度
    
    Returns:
        包含ECharts配置和HTML代码的字典
    """
    try:
        # 验证输入数据
        if not title:
            return _format_error("INVALID_TITLE", "图表标题不能为空")
        
        if not x_data:
            return _format_error("INVALID_X_DATA", "X轴数据不能为空")
        
        if not series_data or not isinstance(series_data, list):
            return _format_error("INVALID_SERIES_DATA", "系列数据必须是非空列表")
        
        for series in series_data:
            if not isinstance(series, dict) or "name" not in series or "data" not in series:
                return _format_error("INVALID_SERIES_FORMAT", "系列数据格式错误，必须包含name和data字段")
        
        # 构建ECharts配置
        option = {
            "title": {
                "text": title,
                "left": "center"
            },
            "tooltip": {
                "trigger": "axis"
            },
            "legend": {
                "data": [series["name"] for series in series_data],
                "top": "30px"
            },
            "grid": {
                "left": "3%",
                "right": "4%",
                "bottom": "3%",
                "containLabel": True
            },
            "toolbox": {
                "feature": {
                    "saveAsImage": {}
                }
            },
            "xAxis": {
                "type": "category",
                "boundaryGap": False,
                "data": x_data,
                "name": x_axis_name
            },
            "yAxis": {
                "type": "value",
                "name": y_axis_name
            },
            "series": []
        }
        
        # 添加系列数据
        for series in series_data:
            option["series"].append({
                "name": series["name"],
                "type": "line",
                "data": series["data"],
                "smooth": True
            })
        
        # 生成HTML代码
        chart_id = f"line_chart_{abs(hash(title)) % 10000}"
        # 使用更安全的JSON序列化方式
        option_json = json.dumps(option, ensure_ascii=False, indent=None, separators=(',', ':'))
        html_code = f"""<div id="{chart_id}" style="width: {width}px; height: {height}px;"></div>
<script>
var {chart_id}_chart = echarts.init(document.getElementById('{chart_id}'));
var {chart_id}_option = {option_json};
{chart_id}_chart.setOption({chart_id}_option);
</script>"""
        
        return _format_success({
            "chart_type": "line",
            "chart_id": chart_id,
            "option": option,
            "html": html_code.strip()
        })
        
    except Exception as e:
        return _format_error("CHART_CREATION_ERROR", f"创建折线图时发生错误: {str(e)}")


def create_pie_chart(
    title: str,
    data: List[Dict[str, Union[str, int, float]]],
    width: int = 800,
    height: int = 400,
    radius: Union[str, List[str]] = "50%"
) -> Dict[str, Any]:
    """
    创建饼图
    
    Args:
        title: 图表标题
        data: 数据，格式为 [{"name": "名称", "value": 数值}]
        width: 图表宽度
        height: 图表高度
        radius: 饼图半径，可以是字符串或列表（用于环形图）
    
    Returns:
        包含ECharts配置和HTML代码的字典
    """
    try:
        # 验证输入数据
        if not title:
            return _format_error("INVALID_TITLE", "图表标题不能为空")
        
        if not data or not isinstance(data, list):
            return _format_error("INVALID_DATA", "数据必须是非空列表")
        
        for item in data:
            if not isinstance(item, dict) or "name" not in item or "value" not in item:
                return _format_error("INVALID_DATA_FORMAT", "数据格式错误，必须包含name和value字段")
        
        # 构建ECharts配置
        option = {
            "title": {
                "text": title,
                "left": "center"
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "{a} <br/>{b}: {c} ({d}%)"
            },
            "legend": {
                "orient": "vertical",
                "left": "left",
                "data": [item["name"] for item in data]
            },
            "toolbox": {
                "feature": {
                    "saveAsImage": {}
                }
            },
            "series": [
                {
                    "name": title,
                    "type": "pie",
                    "radius": radius,
                    "center": ["50%", "60%"],
                    "data": data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    }
                }
            ]
        }
        
        # 生成HTML代码
        chart_id = f"pie_chart_{abs(hash(title)) % 10000}"
        # 使用更安全的JSON序列化方式
        option_json = json.dumps(option, ensure_ascii=False, indent=None, separators=(',', ':'))
        html_code = f"""<div id="{chart_id}" style="width: {width}px; height: {height}px;"></div>
<script>
var {chart_id}_chart = echarts.init(document.getElementById('{chart_id}'));
var {chart_id}_option = {option_json};
{chart_id}_chart.setOption({chart_id}_option);
</script>"""
        
        return _format_success({
            "chart_type": "pie",
            "chart_id": chart_id,
            "option": option,
            "html": html_code.strip()
        })
        
    except Exception as e:
        return _format_error("CHART_CREATION_ERROR", f"创建饼图时发生错误: {str(e)}")


def create_funnel_chart(
    title: str,
    data: List[Dict[str, Union[str, int, float]]],
    width: int = 800,
    height: int = 400,
    sort_order: str = "descending"
) -> Dict[str, Any]:
    """
    创建漏斗图（扇形图）
    
    Args:
        title: 图表标题
        data: 数据，格式为 [{"name": "名称", "value": 数值}]
        width: 图表宽度
        height: 图表高度
        sort_order: 排序方式，"ascending"或"descending"
    
    Returns:
        包含ECharts配置和HTML代码的字典
    """
    try:
        # 验证输入数据
        if not title:
            return _format_error("INVALID_TITLE", "图表标题不能为空")
        
        if not data or not isinstance(data, list):
            return _format_error("INVALID_DATA", "数据必须是非空列表")
        
        for item in data:
            if not isinstance(item, dict) or "name" not in item or "value" not in item:
                return _format_error("INVALID_DATA_FORMAT", "数据格式错误，必须包含name和value字段")
        
        if sort_order not in ["ascending", "descending"]:
            return _format_error("INVALID_SORT_ORDER", "排序方式必须是'ascending'或'descending'")
        
        # 构建ECharts配置
        option = {
            "title": {
                "text": title,
                "left": "center"
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "{a} <br/>{b}: {c}"
            },
            "toolbox": {
                "feature": {
                    "saveAsImage": {}
                }
            },
            "legend": {
                "data": [item["name"] for item in data],
                "bottom": "10px"
            },
            "series": [
                {
                    "name": title,
                    "type": "funnel",
                    "left": "10%",
                    "top": 60,
                    "width": "80%",
                    "height": "60%",
                    "sort": sort_order,
                    "gap": 2,
                    "label": {
                        "show": True,
                        "position": "inside"
                    },
                    "labelLine": {
                        "length": 10,
                        "lineStyle": {
                            "width": 1,
                            "type": "solid"
                        }
                    },
                    "itemStyle": {
                        "borderColor": "#fff",
                        "borderWidth": 1
                    },
                    "emphasis": {
                        "label": {
                            "fontSize": 20
                        }
                    },
                    "data": data
                }
            ]
        }
        
        # 生成HTML代码
        chart_id = f"funnel_chart_{abs(hash(title)) % 10000}"
        # 使用更安全的JSON序列化方式
        option_json = json.dumps(option, ensure_ascii=False, indent=None, separators=(',', ':'))
        html_code = f"""<div id="{chart_id}" style="width: {width}px; height: {height}px;"></div>
<script>
var {chart_id}_chart = echarts.init(document.getElementById('{chart_id}'));
var {chart_id}_option = {option_json};
{chart_id}_chart.setOption({chart_id}_option);
</script>"""
        
        return _format_success({
            "chart_type": "funnel",
            "chart_id": chart_id,
            "option": option,
            "html": html_code.strip()
        })
        
    except Exception as e:
        return _format_error("CHART_CREATION_ERROR", f"创建漏斗图时发生错误: {str(e)}")