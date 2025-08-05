import os
import openai
from typing import List
from bson import ObjectId
from dotenv import load_dotenv

from models.evaluation import ParentEvaluationInput
from db.mongo import get_db

load_dotenv()

# 配置OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

async def generate_parent_evaluation_summary(
    input_data: ParentEvaluationInput, 
    recommended_schools: List[str]
) -> str:
    """生成家长评估的GPT总结"""
    db = get_db()
    
    # 获取推荐学校的详细信息
    school_ids = [ObjectId(school_id) for school_id in recommended_schools]
    schools = await db.universities.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
    
    # 构建提示词
    prompt = f"""
    作为一位专业的留学顾问，请根据以下学生信息生成个性化的选校建议：

    学生背景：
    - 年级：{input_data.grade}
    - GPA：{input_data.gpa}
    - SAT：{input_data.sat if input_data.sat else '未提供'}
    - 托福：{input_data.toefl if input_data.toefl else '未提供'}
    - 活动经历：{', '.join(input_data.activities)}
    - 目标国家：{input_data.target_country}
    - 兴趣方向：{', '.join(input_data.interest)}
    - 家庭预算：{input_data.family_budget}
    - 家长期望：{input_data.family_expectation}
    - 重视实习机会：{'是' if input_data.internship_importance else '否'}

    推荐学校：
    {chr(10).join([f"- {school['name']} (排名#{school['rank']}, 学费${school['tuition']:,})" for school in schools])}

    请生成一段300-500字的个性化建议，包括：
    1. 学生画像分析
    2. 选校策略建议
    3. 对推荐学校的匹配理由
    4. 申请时间规划建议

    请用专业、理性的语气，避免过度营销化。
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

        学生画像：您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa}，在{', '.join(input_data.activities)}方面有丰富经验，对{', '.join(input_data.interest)}领域表现出浓厚兴趣。

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