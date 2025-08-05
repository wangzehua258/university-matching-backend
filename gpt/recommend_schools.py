import os
from typing import List, Dict, Any, Tuple
from bson import ObjectId
from dotenv import load_dotenv

from models.evaluation import ParentEvaluationInput
from db.mongo import get_db

load_dotenv()

def build_hard_filters(input_data: ParentEvaluationInput) -> Dict[str, Any]:
    """构建强约束过滤规则"""
    
    # 中文到英文的映射
    chinese_to_english = {
        "计算机科学": "computer science",
        "人工智能": "artificial intelligence", 
        "工程学": "engineering",
        "商科": "business",
        "医学": "medicine",
        "艺术设计": "art",
        "人文社科": "humanities",
        "自然科学": "science",
        "教育学": "education",
        "法学": "law"
    }
    
    # 将中文兴趣方向转换为英文
    english_interests = []
    for interest in input_data.interest_fields:
        if interest in chinese_to_english:
            english_interests.append(chinese_to_english[interest])
        else:
            english_interests.append(interest)
    
    filters = {
        "country": input_data.target_country,
        "strengths": {"$in": english_interests}
    }

    # 预算转换
    budget_map = {
        "<20w": 30000,
        "20-40w": 50000,
        "30-50w": 60000,
        "40-60w": 70000,
        "不设限": 100000
    }
    max_tuition = budget_map.get(input_data.budget, 100000)
    filters["tuition"] = {"$lte": max_tuition}

    # GPA范围 → 最高可申请的学校排名
    gpa_rank_map = {
        "2.5-3.0": 150,
        "3.0-3.5": 100,
        "3.5-3.8": 60,
        "3.8以上": 30
    }
    max_rank = gpa_rank_map.get(input_data.gpa_range, 200)
    filters["rank"] = {"$lte": max_rank}

    return filters

def parse_size(text: str) -> str:
    """解析学校规模"""
    if "小" in text: 
        return "small"
    if "中" in text: 
        return "medium"
    if "大" in text: 
        return "large"
    return "medium"

def score_school(school: Dict[str, Any], input_data: ParentEvaluationInput) -> float:
    """为学校打分"""
    score = 0.0

    # 专业匹配分数 (35分)
    matched_fields = set(school["strengths"]).intersection(set(input_data.interest_fields))
    score += 35 * len(matched_fields) / max(len(input_data.interest_fields), 1)

    # 声誉匹配：家长重视时，根据排名加分 (20分)
    if input_data.reputation_important:
        score += 20 * (1 - school["rank"] / 300)

    # 实习匹配 (15分)
    if input_data.internship_important and school.get("has_internship_program"):
        score += 15

    # 类型匹配 (15分)
    if school.get("schoolSize") == parse_size(input_data.school_type_preference):
        score += 15

    # 活动匹配 (15分)
    if "科研" in input_data.activities and "undergrad_research" in school.get("tags", []):
        score += 7.5
    if "竞赛" in input_data.activities and "academic_competitions" in school.get("tags", []):
        score += 7.5

    return round(score, 2)

async def recommend_schools_for_parent(input_data: ParentEvaluationInput) -> List[str]:
    """根据家长评估输入推荐学校"""
    from db.mongo import get_db
    db = get_db()
    
    if db is None:
        # 如果全局数据库连接不可用，创建新的连接
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.university_matcher
    
    # 构建强约束过滤条件
    filters = build_hard_filters(input_data)
    
    # 执行过滤查询
    filtered_schools = await db.universities.find(filters).to_list(length=None)
    
    # 为每所学校打分
    scored_schools = [(school, score_school(school, input_data)) for school in filtered_schools]
    
    # 按分数排序
    top_schools = sorted(scored_schools, key=lambda x: x[1], reverse=True)
    
    # 返回前10所学校的ID
    top_10_ids = [str(school["_id"]) for school, _ in top_schools[:10]]
    
    return top_10_ids

def classify_applications(recommended_schools: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """分类ED/EA/RD申请策略"""
    if not recommended_schools:
        return None, [], []
    
    ed_suggestion = recommended_schools[0] if len(recommended_schools) > 0 else None
    ea_suggestions = recommended_schools[1:3] if len(recommended_schools) > 1 else []
    rd_suggestions = recommended_schools[3:] if len(recommended_schools) > 3 else []
    
    return ed_suggestion, ea_suggestions, rd_suggestions

def generate_student_profile(input_data: ParentEvaluationInput) -> Dict[str, str]:
    """生成学生画像"""
    # 根据GPA范围和活动判断学生类型
    if "3.8以上" in input_data.gpa_range:
        student_type = "学术优秀型"
        description = f"您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，在学术方面表现优秀。"
    elif "3.5-3.8" in input_data.gpa_range:
        student_type = "全面发展型"
        description = f"您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，在学术和活动方面都有不错的表现。"
    else:
        student_type = "潜力发展型"
        description = f"您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，有很大的发展潜力。"
    
    description += f" 在{', '.join(input_data.activities)}方面有丰富经验，对{', '.join(input_data.interest_fields)}领域表现出浓厚兴趣。"
    
    return {
        "type": student_type,
        "description": description
    }

def generate_application_strategy(input_data: ParentEvaluationInput, school_count: int) -> str:
    """生成申请策略建议"""
    strategy = f"基于您孩子的背景，我们为您推荐了{school_count}所适合的大学。"
    
    if "3.8以上" in input_data.gpa_range:
        strategy += " 建议采用积极申请策略，重点考虑Top 30的学校。"
    elif "3.5-3.8" in input_data.gpa_range:
        strategy += " 建议采用平衡申请策略，包括冲刺校、匹配校和保底校。"
    else:
        strategy += " 建议采用稳健申请策略，重点关注匹配校和保底校。"
    
    strategy += f" 重点关注{input_data.target_country}的优质大学，这些学校在您感兴趣的领域都有很强的实力。"
    
    return strategy 