# app/services/canonical/keyword_match.py
"""
关键词匹配模块
基于专业关键词进行匹配
"""
from typing import List, Dict


# ================================
# 专业关键词字典
# ================================
MAJOR_KEYWORDS: Dict[str, List[str]] = {
    # ================================
    # 🖥 计算机科学 Computer Science
    # ================================
    "computer_science": [
        "computer", "computing", "software", "programming", "code",
        "artificial intelligence", "ai", "machine learning", "ml",
        "deep learning", "neural", 
        "data", "data science", "database", "big data",
        "algorithm", "theory", "information", "information system",
        "cyber", "security", "网络安全",
        "机器人", "人工智能", "机器学习", "深度学习",
        "计算机", "软件", "编程", "算法"
    ],

    # ================================
    # 🧱 土木工程 Civil Engineering
    # ================================
    "civil_engineering": [
        "civil", "structural", "infrastructure",
        "geotechnical", "transportation", "bridge",
        "hydraulic", "construction",
        "土木", "结构", "岩土", "交通", "桥梁", "施工",
        "水利", "市政"
    ],

    # ================================
    # ⚗️ 化学工程 Chemical Engineering
    # ================================
    "chemical_engineering": [
        "chemical", "chemistry", "process", "reaction",
        "polymer", "bioprocess", "energy", "catalysis",
        "化工", "化学", "过程", "反应", "催化", "聚合物"
    ],

    # ================================
    # 🔬 材料科学 Materials Science
    # ================================
    "materials_science": [
        "materials", "composite", "composites",
        "nano", "nanomaterials", "polymer", "metallurgy",
        "biomaterials", 
        "材料", "复合材料", "金属", "纳米", "高分子"
    ],

    # ================================
    # ⚙️ 机械工程 Mechanical Engineering
    # ================================
    "mechanical_engineering": [
        "mechanical", "mechatronics", "robotics",
        "manufacturing", "dynamics", "thermo", "fluid",
        "机械", "机电", "动力", "流体", "热能", "制造", "机器人"
    ],

    # ================================
    # ⚡ 电气/电子 Electrical & Electronic Engineering
    # ================================
    "electrical_engineering": [
        "electrical", "electronics", "signal",
        "communication", "power", "semiconductor", 
        "电气", "电子", "信号", "通信", "半导体", "电力"
    ],

    # ================================
    # 🧬 生物医学 Biomedical Engineering
    # ================================
    "biomedical_engineering": [
        "biomedical", "bioengineering", "medical",
        "healthcare", "neuro", "neuroscience",
        "生物医学", "医工", "医疗", "神经", "生物工程"
    ],

    # ================================
    # 🌱 环境 Environmental/Sustainability
    # ================================
    "environmental_engineering": [
        "environment", "environmental", "sustainability",
        "ecology", "climate", "carbon", 
        "环境", "生态", "可持续", "碳排放", "气候"
    ],

    # ================================
    # 🔥 能源工程 Energy Engineering
    # ================================
    "energy_engineering": [
        "energy", "renewable", "nuclear", "power systems",
        "hydrogen", "battery", 
        "能源", "可再生", "核能", "电力系统", "储能", "电池"
    ],

    # ================================
    # 💰 金融 Finance
    # ================================
    "finance": [
        "finance", "financial", "investment", "market",
        "fintech", "quant", "risk", "wealth",
        "金融", "投资", "量化", "风险", "财富", "资产"
    ],

    # ================================
    # 📊 商科/管理 Management, Business, Marketing
    # ================================
    "management": [
        "management", "business", "strategy", "consulting",
        "marketing", "hr", "supply chain", "operations",
        "商业", "管理", "运营", "供应链", "市场", "战略", "咨询"
    ],

    # ================================
    # 📈 数据科学 Data Science
    # ================================
    "data_science": [
        "data science", "data analytics", "statistics",
        "machine learning", "AI", "big data",
        "数据科学", "数据分析", "统计", "人工智能"
    ],

    # ================================
    # 🧮 数学 Mathematics
    # ================================
    "mathematics": [
        "mathematics", "applied math", "statistics",
        "algebra", "calculus", "probability",
        "数学", "应用数学", "统计"
    ],

    # ================================
    # 📡 通信 Engineering (Communications)
    # ================================
    "communications_engineering": [
        "communications", "signal processing", "wireless",
        "antenna", "5g", "通信", "信号处理", "无线"
    ],

    # ================================
    # 🧪 生命科学 Life Science
    # ================================
    "life_science": [
        "biology", "biotech", "biomedical",
        "生命科学", "生物", "生物技术"
    ]
}


def keyword_overlap_score(name: str, keywords: List[str]) -> float:
    """
    计算文本与关键词列表的重叠分数
    
    Args:
        name: 要匹配的文本
        keywords: 关键词列表
        
    Returns:
        重叠分数 (0-1)
    """
    if not name or not keywords:
        return 0.0
    
    name_lower = name.lower()
    hits = sum(1 for kw in keywords if kw.lower() in name_lower)
    
    return hits / len(keywords) if len(keywords) else 0

