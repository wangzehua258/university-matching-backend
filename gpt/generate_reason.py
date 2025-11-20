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
    """构建GPT提示词（美国大学）"""
    if school_list is None:
        school_list = []
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
   - 引导填写我们的详细评估表格
   - 提供30分钟免费诊断服务作为行动号召

5. **避免**：
   - 不要过于销售化，保持专业顾问的语调
   - 不要直接说"联系我们"，而是引导填写表格
   - 尽量不要超过400字

请生成符合以上要求的专业建议。
"""

def build_au_gpt_prompt(input_data: Dict[str, Any], school_list: List[Dict[str, Any]]) -> str:
    """构建GPT提示词（澳洲大学）"""
    if school_list is None:
        school_list = []
    
    # 提取关键信息
    academic_band = input_data.get("academic_band", "未提供")
    interests = input_data.get("interests", [])
    budget_usd = input_data.get("budget_usd", 0)
    wil_preference = input_data.get("wil_preference", "不重要")
    go8_preference = input_data.get("go8_preference", "没有明确偏好")
    psw_importance = input_data.get("psw_importance", "一般")
    city_preferences = input_data.get("city_preferences", [])
    english_readiness = input_data.get("english_readiness", "未提供")
    main_concern = input_data.get("main_concern", "")
    
    # 推荐学校信息
    school_names = [f"{s.get('name', '')}（排名#{s.get('rank', 'N/A')}）" for s in school_list[:5]]
    
    return f"""
你是澳洲留学顾问，基于以下学生资料生成500字的专业建议：

学生资料：
- 学术水平：{academic_band}
- 专业兴趣：{', '.join(interests) if interests else '未提供'}
- 预算：${budget_usd:,}/年
- WIL实习需求：{wil_preference}
- Go8偏好：{go8_preference}
- PSW工签重视度：{psw_importance}
- 意向城市：{', '.join(city_preferences) if city_preferences else '不限'}
- 英语准备度：{english_readiness}
- 主要顾虑：{main_concern if main_concern else '未明确'}

推荐学校：{', '.join(school_names) if school_names else '暂无'}

要求：
1. 前350字：专业分析学生资料，给出针对澳洲留学的具体建议
   - 分析学术竞争力（基于学术水平）
   - 分析专业兴趣与推荐学校的匹配度
   - 分析预算情况
   - 给出具体的选校策略（冲刺/匹配/保底）
   - 针对澳洲申请特点给出建议（2月/7月入学、英语成绩、WIL/PSW等）

2. 后150字：吸引家长填写评估表格（必须包含以下要素）
   - 开头：说明当前快速评估的局限性
   - 核心价值：强调填写表格后能获得一对一专业顾问30分钟免费诊断服务（不是机器人，是真人顾问），包括定制化选校策略、详细申请时间表、材料准备清单、奖学金申请指导等
   - 时间紧迫性：强调申请窗口有限（2月/7月入学），现在不行动可能错过最佳申请时机
   - 情感共鸣：填写表格是孩子留学成功的重要起点
   - 行动号召：立即填写详细评估表格，获得专属留学方案

总字数：严格控制在500字。前350字专业分析，后150字吸引填写表格。语气专业可信，最后150字要有说服力，能吸引家长立即行动。不要添加任何额外内容，不要超过500字。
"""

def build_uk_gpt_prompt(input_data: Dict[str, Any], school_list: List[Dict[str, Any]]) -> str:
    """构建GPT提示词（英国大学）"""
    if school_list is None:
        school_list = []
    
    # 提取关键信息
    academic_band = input_data.get("academic_band", "未提供")
    interests = input_data.get("interests", [])
    budget_usd = input_data.get("budget_usd", 0)
    ucas_route = input_data.get("ucas_route", "常规路线")
    oxbridge_must_cover = input_data.get("oxbridge_must_cover", False)
    placement_year_pref = input_data.get("placement_year_pref", "不重要")
    russell_pref = input_data.get("russell_pref", "没有明确偏好")
    region_pref = input_data.get("region_pref", "不限")
    foundation_need = input_data.get("foundation_need", "不需要")
    prep_level = input_data.get("prep_level", "未准备好")
    main_concern = input_data.get("main_concern", "")
    
    # 推荐学校信息
    school_names = [f"{s.get('name', '')}（排名#{s.get('rank', 'N/A')}）" for s in school_list[:5]]
    
    return f"""
你是英国留学顾问，基于以下学生资料生成500字的专业建议：

学生资料：
- 学术水平：{academic_band}
- 专业兴趣：{', '.join(interests) if interests else '未提供'}
- 预算：${budget_usd:,}/年
- UCAS路线：{ucas_route}{'（必须覆盖Oxbridge/医学）' if oxbridge_must_cover else ''}
- Placement Year偏好：{placement_year_pref}
- 罗素集团偏好：{russell_pref}
- 地域偏好：{region_pref}
- Foundation需求：{foundation_need}
- 材料准备度：{prep_level}
- 主要顾虑：{main_concern if main_concern else '未明确'}

推荐学校：{', '.join(school_names) if school_names else '暂无'}

要求：
1. 前350字：专业分析学生资料，给出针对英国留学的具体建议
   - 分析学术竞争力（基于学术水平，评估Oxbridge/罗素集团/其他大学）
   - 分析专业兴趣与推荐学校的匹配度
   - 分析预算情况
   - 给出具体的选校策略
   - 针对英国申请特点给出建议（UCAS时间、Personal Statement、入学测试、Foundation路径等）

2. 后150字：吸引家长填写评估表格
   - 说明当前评估的局限性
   - 强调填写表格后能获得：一对一专业顾问30分钟免费诊断、定制化选校策略、UCAS申请时间表、Personal Statement写作指导等
   - 强调时间紧迫性（UCAS截止时间临近）
   - 给出强烈的行动号召

总字数：500字。语气专业可信，最后150字要有说服力。
"""

def build_sg_gpt_prompt(input_data: Dict[str, Any], school_list: List[Dict[str, Any]]) -> str:
    """构建GPT提示词（新加坡大学）"""
    if school_list is None:
        school_list = []
    
    # 提取关键信息
    academic_band = input_data.get("academic_band", "未提供")
    interests = input_data.get("interests", [])
    budget_usd = input_data.get("budget_usd", 0)
    bond_acceptance = input_data.get("bond_acceptance", "不愿意")
    tg_must = input_data.get("tg_must", False)
    orientation = input_data.get("orientation", "均衡")
    interview_portfolio = input_data.get("interview_portfolio", "不愿意")
    want_double_degree = input_data.get("want_double_degree", False)
    want_exchange = input_data.get("want_exchange", False)
    safety_importance = input_data.get("safety_importance", "一般")
    main_concern = input_data.get("main_concern", "")
    
    # 推荐学校信息
    school_names = [f"{s.get('name', '')}（排名#{s.get('rank', 'N/A')}）" for s in school_list[:5]]
    
    return f"""
你是新加坡留学顾问，基于以下学生资料生成500字的专业建议：

学生资料：
- 学术水平：{academic_band}
- 专业兴趣：{', '.join(interests) if interests else '未提供'}
- 预算：${budget_usd:,}/年
- TG/服务期接受度：{bond_acceptance}{'（必须可申请TG）' if tg_must else ''}
- 培养导向：{orientation}
- 面试/作品集接受度：{interview_portfolio}
- 希望双学位：{'是' if want_double_degree else '否'}
- 希望交换项目：{'是' if want_exchange else '否'}
- 安全重要性：{safety_importance}
- 主要顾虑：{main_concern if main_concern else '未明确'}

推荐学校：{', '.join(school_names) if school_names else '暂无'}

要求：
1. 前350字：专业分析学生资料，给出针对新加坡留学的具体建议
   - 分析学术竞争力（基于学术水平，评估NUS/NTU/SMU等）
   - 分析专业兴趣与推荐学校的匹配度
   - 分析预算情况和TG申请建议
   - 给出具体的选校策略
   - 针对新加坡申请特点给出建议（申请时间、TG申请、面试/作品集、双学位/交换等）

2. 后150字：吸引家长填写评估表格
   - 说明当前评估的局限性
   - 强调填写表格后能获得：一对一专业顾问30分钟免费诊断、定制化选校策略、申请时间表、TG申请指导、面试准备建议等
   - 强调时间紧迫性（申请窗口有限）
   - 给出强烈的行动号召

总字数：500字。语气专业可信，最后150字要有说服力。
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
    if recommended_schools is None:
        recommended_schools = []
    
    # 根据国家选择不同的集合
    country = input_data.target_country if hasattr(input_data, 'target_country') else None
    if country == "Australia":
        collection = db.university_au
    elif country == "United Kingdom":
        collection = db.university_uk
    elif country == "Singapore":
        collection = db.university_sg
    else:
        collection = db.universities
    
    school_ids = [ObjectId(school_id) for school_id in recommended_schools if school_id]
    if school_ids:
        schools = await collection.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
        if schools is None:
            schools = []
    else:
        schools = []
    
    # 根据国家构建不同的提示词
    if country == "Australia":
        # 澳洲大学使用专门的提示词构建函数
        from typing import Dict, Any
        input_dict = input_data.dict() if hasattr(input_data, 'dict') else input_data
        prompt = build_au_gpt_prompt(input_dict, schools)
    elif country == "United Kingdom":
        # 英国大学使用专门的提示词构建函数
        from typing import Dict, Any
        input_dict = input_data.dict() if hasattr(input_data, 'dict') else input_data
        prompt = build_uk_gpt_prompt(input_dict, schools)
    elif country == "Singapore":
        # 新加坡大学使用专门的提示词构建函数
        from typing import Dict, Any
        input_dict = input_data.dict() if hasattr(input_data, 'dict') else input_data
        prompt = build_sg_gpt_prompt(input_dict, schools)
    else:
        # 其他国家使用原有提示词
        prompt = build_gpt_prompt(input_data, schools)
    
    # 检查API密钥是否设置
    if not api_key or api_key == "your-openai-api-key-here":
        print("⚠️  使用默认建议（API Key 未配置）")
        # 返回默认建议（根据国家不同）
        country = input_data.target_country if hasattr(input_data, 'target_country') else None
        if country == "Australia":
            input_dict = input_data.dict() if hasattr(input_data, 'dict') else input_data
            academic_band = input_dict.get("academic_band", "未提供")
            interests = input_dict.get("interests", [])
            return f"""
根据您孩子的学术背景和兴趣，我们为您推荐了{len(schools)}所适合的澳洲大学。

学生画像：您的孩子学术水平为{academic_band}，对{', '.join(interests) if interests else '多个'}领域表现出浓厚兴趣。

选校策略：建议根据学术水平、专业兴趣、预算和城市偏好，选择最适合的澳洲大学。这些推荐学校在您感兴趣的领域都有很强的实力，并且符合您的预算和偏好。

申请建议：澳洲大学申请通常需要提前3-6个月准备。建议尽早准备英语成绩（IELTS/TOEFL/PTE）、高中成绩单等材料，关注各校的入学时间（2月和7月），合理安排申请时间。
            """
        else:
            return f"""
根据您孩子的学术背景和兴趣，我们为您推荐了{len(schools)}所适合的大学。

学生画像：您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，在{', '.join(input_data.activities) if input_data.activities else '多个'}方面有丰富经验，对{', '.join(input_data.interest_fields) if input_data.interest_fields else '多个'}领域表现出浓厚兴趣。

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
                    {"role": "system", "content": "你是留学顾问，生成500字的专业建议。前350字专业分析学生资料，给出针对具体国家的建议。后150字吸引家长填写评估表格，强调一对一专业顾问30分钟免费诊断服务的价值、时间紧迫性，给出行动号召。不要添加额外内容。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=700,  # 限制在500字左右（约700 tokens，确保最后一段完整）
                temperature=0.7
            )
            result = response.choices[0].message.content.strip()
        elif not OPENAI_NEW_API:
            # 使用旧版本 OpenAI API (<1.0.0)
            import openai
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一位经验丰富的留学顾问，擅长为学生提供个性化的选校建议。你特别擅长在建议结尾用有说服力的语言吸引家长填写评估表格，这是你的核心目标。"},
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
        # 如果GPT调用失败，返回默认建议（根据国家不同）
        country = input_data.target_country if hasattr(input_data, 'target_country') else None
        if country == "Australia":
            input_dict = input_data.dict() if hasattr(input_data, 'dict') else input_data
            academic_band = input_dict.get("academic_band", "未提供")
            interests = input_dict.get("interests", [])
            return f"""
根据您孩子的学术背景和兴趣，我们为您推荐了{len(schools)}所适合的澳洲大学。

学生画像：您的孩子学术水平为{academic_band}，对{', '.join(interests) if interests else '多个'}领域表现出浓厚兴趣。

选校策略：建议根据学术水平、专业兴趣、预算和城市偏好，选择最适合的澳洲大学。这些推荐学校在您感兴趣的领域都有很强的实力，并且符合您的预算和偏好。

申请建议：澳洲大学申请通常需要提前3-6个月准备。建议尽早准备英语成绩（IELTS/TOEFL/PTE）、高中成绩单等材料，关注各校的入学时间（2月和7月），合理安排申请时间。
            """
        else:
            return f"""
根据您孩子的学术背景和兴趣，我们为您推荐了{len(schools)}所适合的大学。

学生画像：您的孩子是一位{input_data.grade}学生，GPA {input_data.gpa_range}，在{', '.join(input_data.activities) if input_data.activities else '多个'}方面有丰富经验，对{', '.join(input_data.interest_fields) if input_data.interest_fields else '多个'}领域表现出浓厚兴趣。

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
