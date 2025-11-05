"""智能字段选择器 - 根据问题内容智能选择相关字段"""

import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass


@dataclass
class FieldRelevance:
    """字段相关性评分"""
    field_name: str
    score: float
    reasons: List[str]


class SmartFieldSelector:
    """智能字段选择器"""
    
    def __init__(self):
        # 定义关键词映射规则
        self.keyword_mappings = {
            # 身份标识相关
            "姓名|名字|名称|称呼": ["name", "username", "full_name", "display_name", "title", "publicity_name"],
            "编号|代号|ID|标识|序号": ["id", "code", "number", "serial", "identifier", "aircraft_id"],
            "电话|手机|联系方式|联系电话": ["phone", "mobile", "contact", "telephone", "tel"],
            "邮箱|邮件|email": ["email", "mail", "e_mail"],
            
            # 时间相关
            "时间|日期|创建|更新|修改": ["time", "date", "created", "updated", "modified", "timestamp", "create_time", "update_time"],
            "年|月|日|小时|分钟|秒": ["year", "month", "day", "hour", "minute", "second", "datetime"],
            
            # 状态相关
            "状态|情况|条件|模式": ["status", "state", "condition", "mode", "flag"],
            "类型|种类|分类|类别": ["type", "category", "class", "kind", "classification"],
            
            # 数值相关
            "数量|个数|总数|计数": ["count", "number", "quantity", "total", "amount"],
            "价格|金额|费用|成本": ["price", "amount", "cost", "fee", "money", "value"],
            "温度|压力|电压|功率": ["temperature", "pressure", "voltage", "power", "temp"],
            
            # 位置相关
            "位置|地址|坐标|经纬度": ["location", "address", "position", "coordinate", "latitude", "longitude"],
            "国家|省份|城市|地区": ["country", "province", "city", "region", "area"],
            
            # 组织相关
            "部门|团队|组织|公司": ["department", "team", "organization", "company", "group"],
            "负责人|联系人|管理员": ["manager", "contact", "admin", "leader", "manage_leader", "overall_contact", "center_contact"],
            
            # 卫星航天相关
            "卫星|航天器|飞行器": ["satellite", "spacecraft", "aircraft", "vehicle"],
            "轨道|在轨|飞行": ["orbit", "flight", "trajectory", "path"],
            "遥感|传感器|设备": ["sensor", "device", "equipment", "hardware", "component"],
            "健康|状态|异常|故障": ["health", "status", "anomaly", "fault", "error", "incident"],
            "功率|电源|能源": ["power", "energy", "battery", "electrical"],
            "姿态|控制|导航": ["attitude", "control", "navigation", "guidance"],
            "数据|信息|记录": ["data", "info", "record", "log", "history"],
        }
        
        # 常见无关字段（通常不需要在查询结果中显示）
        # 注意：不包含ID和时间字段，因为这些通常是重要的
        self.irrelevant_fields = {
            "metadata", "raw_data", "hash", "checksum",
            "blob", "binary_data", "large_text", "description_long",
            "config", "settings", "preferences", "cache"
        }
        
        # 核心字段（通常应该包含）
        self.core_fields = {
            "id", "name", "title", "status", "type", "created_at", "updated_at", 
            "create_time", "update_time", "time", "date", "timestamp"
        }
    
    def select_relevant_fields(self, question: str, available_fields: List[str], 
                             max_fields: int = 8) -> List[str]:
        """
        根据问题内容选择相关字段
        
        Args:
            question: 用户问题
            available_fields: 可用字段列表
            max_fields: 最大字段数量
            
        Returns:
            选择的字段列表
        """
        if not available_fields:
            return []
        
        # 计算每个字段的相关性评分
        field_scores = self._calculate_field_relevance(question, available_fields)
        
        # 按评分排序
        sorted_fields = sorted(field_scores, key=lambda x: x.score, reverse=True)
        
        # 选择最相关的字段
        selected_fields = []
        
        # 首先添加核心字段（如果存在且相关）
        for field_info in sorted_fields:
            if field_info.field_name.lower() in self.core_fields and field_info.score > 0:
                selected_fields.append(field_info.field_name)
                if len(selected_fields) >= max_fields:
                    break
        
        # 然后添加其他高分字段
        for field_info in sorted_fields:
            if (field_info.field_name not in selected_fields and 
                field_info.score > 0 and 
                len(selected_fields) < max_fields):
                selected_fields.append(field_info.field_name)
        
        # 如果没有找到相关字段，返回前几个核心字段
        if not selected_fields:
            for field in available_fields:
                if field.lower() in self.core_fields:
                    selected_fields.append(field)
                    if len(selected_fields) >= min(3, max_fields):
                        break
            
            # 如果还是没有，返回前几个字段
            if not selected_fields:
                selected_fields = available_fields[:min(3, max_fields)]
        
        return selected_fields[:max_fields]
    
    def _calculate_field_relevance(self, question: str, available_fields: List[str]) -> List[FieldRelevance]:
        """计算字段相关性评分"""
        field_scores = []
        question_lower = question.lower()
        
        for field in available_fields:
            score = 0.0
            reasons = []
            field_lower = field.lower()
            
            # 检查是否为无关字段
            if field_lower in self.irrelevant_fields:
                score -= 2.0
                reasons.append("常见无关字段")
            
            # 检查是否为核心字段
            if field_lower in self.core_fields:
                score += 1.0
                reasons.append("核心字段")
            
            # 直接匹配字段名
            if field_lower in question_lower:
                score += 3.0
                reasons.append("字段名直接匹配")
            
            # 关键词映射匹配
            for pattern, related_fields in self.keyword_mappings.items():
                if re.search(pattern, question_lower):
                    for related_field in related_fields:
                        if related_field.lower() in field_lower or field_lower in related_field.lower():
                            score += 2.0
                            reasons.append(f"关键词匹配: {pattern}")
                            break
            
            # 部分匹配
            question_words = set(re.findall(r'\w+', question_lower))
            field_words = set(re.findall(r'\w+', field_lower))
            common_words = question_words.intersection(field_words)
            if common_words:
                score += len(common_words) * 0.5
                reasons.append(f"部分词汇匹配: {common_words}")
            
            field_scores.append(FieldRelevance(field, score, reasons))
        
        return field_scores
    
    def explain_selection(self, question: str, available_fields: List[str], 
                         selected_fields: List[str]) -> Dict[str, any]:
        """解释字段选择的原因"""
        field_scores = self._calculate_field_relevance(question, available_fields)
        
        explanation = {
            "question": question,
            "total_fields": len(available_fields),
            "selected_fields": len(selected_fields),
            "selection_details": []
        }
        
        for field_info in field_scores:
            if field_info.field_name in selected_fields:
                explanation["selection_details"].append({
                    "field": field_info.field_name,
                    "score": field_info.score,
                    "reasons": field_info.reasons,
                    "selected": True
                })
        
        return explanation


def create_smart_columns_parameter(question: str, available_fields: List[str], 
                                 max_fields: int = 8) -> str:
    """
    创建智能列参数字符串
    
    Args:
        question: 用户问题
        available_fields: 可用字段列表
        max_fields: 最大字段数量
        
    Returns:
        逗号分隔的字段名字符串
    """
    selector = SmartFieldSelector()
    selected_fields = selector.select_relevant_fields(question, available_fields, max_fields)
    return ",".join(selected_fields)


# 便捷函数
def smart_field_selection(question: str, available_fields: List[str], 
                         max_fields: int = 8) -> Tuple[List[str], Dict[str, any]]:
    """
    智能字段选择的便捷函数
    
    Returns:
        (selected_fields, explanation)
    """
    selector = SmartFieldSelector()
    selected_fields = selector.select_relevant_fields(question, available_fields, max_fields)
    explanation = selector.explain_selection(question, available_fields, selected_fields)
    return selected_fields, explanation