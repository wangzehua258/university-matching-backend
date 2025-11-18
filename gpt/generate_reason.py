import os
from typing import List, Dict, Any
from bson import ObjectId
from dotenv import load_dotenv

from models.evaluation import ParentEvaluationInput
from db.mongo import get_db

load_dotenv()

# 配置OpenAI - 使用新版本API
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your-openai-api-key-here":
        openai_client = OpenAI(api_key=api_key)
        OPENAI_NEW_API = True
    else:
        openai_client = None
        OPENAI_NEW_API = True  # 即使没有key也使用新API格式
except ImportError:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai_client = None
    OPENAI_NEW_API = False

def build_gpt_prompt(input_data: ParentEvaluationInput, school_list: List[Dict[str, Any]]) -> str:
    """构建GPT提示词"""
    school_names = [f"{school['name']}（排名#{school['rank']}）" for school in school_list]
    
    return f"""
你是一位经验丰富的留学顾问，需要为家长生成一段专业且具有紧迫感的择校建议。

家长填写的学生背景：
- 年级：{input_data.grade}
- GPA范围：{input_data.gpa_range}
- SAT成绩：{input_data.sat_score if input_data.sat_score else '未提供'}
- 兴趣方向：{", ".join(input_data.interest_fields) if input_data.interest_fields else '未提供'}
- 目标国家：{input_data.target_country}
- 学校类型偏好：{input_data.school_type_preference}
- 预算：{input_data.budget}
- 是否重视学校声誉：{'是' if input_data.reputation_important else '否'}
- 是否重视实习机会：{'是' if input_data.internship_important else '否'}
- 家长期望：{input_data.family_expectation}
- 活动经历：{", ".join(input_data.activities) if input_data.activities else '未提供'}

推荐学校：{", ".join(school_names)}

请生成一段专业建议，要求：

1. **总字数控制在400字以内，你是一个专业的留学中介**

2. **内容结构**：
   - 首先分析学生的具体情况和优势（基于GPA、SAT、活动等）
   - 指出大学申请中必须准备的内容
   - 指出申请过程中的关键挑战和时间紧迫性
   - 强调专业指导的重要性
   - 引导家长填写详细评估表格获取免费诊断

3. **语气要求**：
   - 专业、可信赖
   - 带有适度的紧迫感，让家长意识到申请准备需要尽早开始
   - 强调留学申请是一个复杂的过程，需要专业机构的帮助
   - 温和但坚定地引导家长采取行动

4. **关键信息必须包含**：
   - 强调申请准备时间紧迫，需要尽早规划
   - 提到申请材料准备、时间规划、策略制定等都需要专业指导
   - 引导填写我们的详细评估表格（Typeform）
   - 提供30分钟免费诊断服务作为行动号召

5. **避免**：
   - 不要过于销售化，保持专业顾问的语调
   - 不要直接说"联系我们"，而是引导填写表格
   - 尽量不要超过400字

请生成符合以上要求的专业建议。
"""

async def generate_parent_evaluation_summary(
    input_data: ParentEvaluationInput, 
    recommended_schools: List[str]
) -> str:
    """生成家长评估的GPT总结"""
    # 重新加载环境变量，确保获取最新的 API Key
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    
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
    if not api_key or api_key == "your-openai-api-key-here":
        print("⚠️  使用默认建议（API Key 未配置）")
        # 返回默认建议
        return f"""
根据您孩子的学术背景和兴趣，我们为您推荐了{len(schools)}所适合的大学。

学生画像：您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，在{', '.join(input_data.activities)}方面有丰富经验，对{', '.join(input_data.interest_fields)}领域表现出浓厚兴趣。

选校策略：建议采用分层申请策略，包括冲刺校、匹配校和保底校。重点关注{input_data.target_country}的优质大学，这些学校在您感兴趣的领域都有很强的实力。

申请建议：建议提前准备申请材料，关注各校的申请截止日期，合理安排ED/EA/RD申请时间。
        """
    
    # 重新初始化客户端（如果API Key已更新）
    try:
        if OPENAI_NEW_API:
            if api_key and api_key != "your-openai-api-key-here":
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
            else:
                client = openai_client
        else:
            client = None
    except Exception:
        client = openai_client
    
    try:
        print("✅ 尝试调用 GPT API...")
        if OPENAI_NEW_API and client:
            # 使用新版本 OpenAI API (>=1.0.0)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一位经验丰富的留学顾问，擅长为学生提供个性化的选校建议。你的建议专业、可信赖，同时能够引导家长采取行动。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,  # 限制在400字左右（约500 tokens）
                temperature=0.7
            )
            result = response.choices[0].message.content.strip()
        elif not OPENAI_NEW_API:
            # 使用旧版本 OpenAI API (<1.0.0)
            import openai
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一位经验丰富的留学顾问，擅长为学生提供个性化的选校建议。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            result = response.choices[0].message.content.strip()
        else:
            raise Exception("OpenAI client not initialized")
        
        print(f"✅ GPT API 调用成功，返回长度: {len(result)} 字符")
        return result
    
    except Exception as e:
        print(f"❌ GPT API 调用失败: {e}")
        import traceback
        traceback.print_exc()
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
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        return f"{university_name}在您感兴趣的领域具有很强实力，非常适合您的学术发展需求。"
    
    try:
        if OPENAI_NEW_API and openai_client:
            # 使用新版本 OpenAI API (>=1.0.0)
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是留学顾问，擅长分析学校与学生的匹配度。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        elif not OPENAI_NEW_API:
            # 使用旧版本 OpenAI API (<1.0.0)
            import openai
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
        else:
            return f"{university_name}在您感兴趣的领域具有很强实力，非常适合您的学术发展需求。"
    
    except Exception as e:
        return f"{university_name}在您感兴趣的领域具有很强实力，非常适合您的学术发展需求。"
