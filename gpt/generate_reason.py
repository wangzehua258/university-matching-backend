import os
import openai
from typing import List, Dict, Any
from bson import ObjectId
from dotenv import load_dotenv

from models.evaluation import ParentEvaluationInput
from db.mongo import get_db

load_dotenv()

# 配置OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def build_gpt_prompt(input_data: ParentEvaluationInput, school_list: List[Dict[str, Any]]) -> str:
    """构建GPT提示词"""
    school_names = [f"{school['name']}（排名#{school['rank']}）" for school in school_list]
    
    return f"""
家长填写的学生背景如下：

年级：{input_data.grade}
GPA范围：{input_data.gpa_range}
SAT成绩：{input_data.sat_score if input_data.sat_score else '未提供'}
兴趣方向：{", ".join(input_data.interest_fields)}
目标国家：{input_data.target_country}
学校类型偏好：{input_data.school_type_preference}
预算：{input_data.budget}
是否重视学校声誉：{'是' if input_data.reputation_important else '否'}
是否重视实习机会：{'是' if input_data.internship_important else '否'}
家长期望方向：{input_data.family_expectation}
活动经历：{", ".join(input_data.activities)}

推荐学校如下：
{", ".join(school_names)}

请基于以上信息，为家长生成一段专业、可信赖的择校建议，包括：

1. 孩子属于哪种类型的申请者
2. ED/EA/RD策略推荐的原因
3. 推荐学校匹配的逻辑
4. 家长接下来重点关注方向

字数建议：300-500字，语气专业、尊重、具有洞察力。
"""

async def generate_parent_evaluation_summary(
    input_data: ParentEvaluationInput, 
    recommended_schools: List[str]
) -> str:
    """生成家长评估的GPT总结"""
    db = get_db()
    
    if db is None:
        # 如果全局数据库连接不可用，创建新的连接
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.university_matcher
    
    # 获取推荐学校的详细信息
    school_ids = [ObjectId(school_id) for school_id in recommended_schools]
    schools = await db.universities.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
    
    # 构建提示词
    prompt = build_gpt_prompt(input_data, schools)
    
    # 检查API密钥是否设置
    if not openai.api_key or openai.api_key == "your-openai-api-key-here":
        # 返回默认建议
        return f"""
根据您孩子的学术背景和兴趣，我们为您推荐了{len(schools)}所适合的大学。

学生画像：您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，在{', '.join(input_data.activities)}方面有丰富经验，对{', '.join(input_data.interest_fields)}领域表现出浓厚兴趣。

选校策略：建议采用分层申请策略，包括冲刺校、匹配校和保底校。重点关注{input_data.target_country}的优质大学，这些学校在您感兴趣的领域都有很强的实力。

申请建议：建议提前准备申请材料，关注各校的申请截止日期，合理安排ED/EA/RD申请时间。
        """
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位经验丰富的留学顾问，擅长为学生提供个性化的选校建议。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        # 如果GPT调用失败，返回默认建议
        return f"""
根据您孩子的学术背景和兴趣，我们为您推荐了{len(schools)}所适合的大学。

学生画像：您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，在{', '.join(input_data.activities)}方面有丰富经验，对{', '.join(input_data.interest_fields)}领域表现出浓厚兴趣。

选校策略：建议采用分层申请策略，包括冲刺校、匹配校和保底校。重点关注{input_data.target_country}的优质大学，这些学校在您感兴趣的领域都有很强的实力。

申请建议：建议提前准备申请材料，关注各校的申请截止日期，合理安排ED/EA/RD申请时间。
        """

async def generate_university_recommendation_reason(
    university_name: str,
    student_interests: List[str],
    student_profile: str
) -> str:
    """为特定大学生成推荐理由"""
    prompt = f"""
    请为{university_name}生成一段个性化的推荐理由。

    学生兴趣：{', '.join(student_interests)}
    学生背景：{student_profile}

    请从以下角度分析：
    1. 学校在该学生兴趣领域的优势
    2. 学校文化与学生的匹配度
    3. 具体的申请建议

    请控制在200字以内，语言专业且具有说服力。
    """
    
    # 检查API密钥是否设置
    if not openai.api_key or openai.api_key == "your-openai-api-key-here":
        return f"{university_name}在您感兴趣的领域具有很强实力，非常适合您的学术发展需求。"
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是留学顾问，擅长分析学校与学生的匹配度。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"{university_name}在您感兴趣的领域具有很强实力，非常适合您的学术发展需求。" 