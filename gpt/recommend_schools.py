import os
from typing import List
from bson import ObjectId
from dotenv import load_dotenv

from models.evaluation import ParentEvaluationInput
from db.mongo import get_db

load_dotenv()

async def recommend_schools_for_parent(input_data: ParentEvaluationInput) -> List[str]:
    """根据家长评估输入推荐学校"""
    db = get_db()
    
    # 构建筛选条件
    filter_conditions = {}
    
    # 根据目标国家筛选
    if input_data.target_country:
        filter_conditions["country"] = input_data.target_country
    
    # 根据预算筛选学费
    if input_data.family_budget:
        budget_ranges = {
            "20-30w": 40000,
            "30-50w": 60000,
            "50-80w": 80000,
            "80w+": 100000
        }
        max_tuition = budget_ranges.get(input_data.family_budget, 100000)
        filter_conditions["tuition"] = {"$lte": max_tuition}
    
    # 根据兴趣筛选优势专业
    if input_data.interest:
        filter_conditions["strengths"] = {"$in": input_data.interest}
    
    # 根据GPA和SAT筛选排名范围
    rank_range = get_rank_range_by_scores(input_data.gpa, input_data.sat)
    if rank_range:
        filter_conditions["rank"] = rank_range
    
    # 执行查询
    universities = await db.universities.find(filter_conditions).limit(10).to_list(length=10)
    
    # 返回学校ID列表（字符串格式）
    return [str(uni["_id"]) for uni in universities]

def get_rank_range_by_scores(gpa: float, sat: int = None) -> dict:
    """根据GPA和SAT分数确定合适的排名范围"""
    if gpa >= 3.8 and (sat is None or sat >= 1450):
        return {"$lte": 20}  # Top 20
    elif gpa >= 3.5 and (sat is None or sat >= 1350):
        return {"$lte": 50}  # Top 50
    elif gpa >= 3.2 and (sat is None or sat >= 1250):
        return {"$lte": 100}  # Top 100
    else:
        return {"$lte": 200}  # Top 200 