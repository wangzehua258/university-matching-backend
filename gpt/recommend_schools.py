import os
from typing import List, Dict, Any, Tuple, Optional
from bson import ObjectId
from dotenv import load_dotenv

from models.evaluation import ParentEvaluationInput
from db.mongo import get_db

load_dotenv()

def build_hard_filters(input_data: ParentEvaluationInput, strict_mode: bool = True) -> Dict[str, Any]:
    """构建强约束过滤规则
    
    Args:
        input_data: 家长评估输入
        strict_mode: 是否使用严格模式（True=严格，False=宽松）
    """
    
    # 中文到英文的映射
    chinese_to_english = {
        "计算机科学": "computer science",
        "人工智能": "artificial intelligence",
        "工程学": "engineering",
        "商科": "business",
        "医学": "medicine",
        "艺术设计": "arts",
        "人文社科": "humanities",
        "自然科学": "natural sciences",
        "教育学": "education",
        "法学": "law",
        "公共政策": "public policy",
        "经济学": "economics",
        "物理学": "physics",
        "化学": "chemistry",
        "心理学": "psychology",
        "生物学": "biology",
        "创业": "entrepreneurship",
        "公共健康": "public health",
        "国际关系": "international relations",
        "政治学": "political science",
        "农业": "agriculture",
        "兽医学": "veterinary",
        "传播学": "communication",
        "电影学": "film",
        "海洋学": "oceanography",
        "药学": "pharmacy",
        "神学": "theology"
    }
    
    # 将中文兴趣方向转换为英文
    english_interests = []
    for interest in input_data.interest_fields:
        if interest in chinese_to_english:
            english_interests.append(chinese_to_english[interest])
        else:
            english_interests.append(interest)
    
    filters = {
        "country": input_data.target_country
    }

    # 专业匹配：根据模式调整严格程度
    if strict_mode:
        # 严格模式：要求学校包含用户选择的至少1个专业（放宽要求）
        filters["strengths"] = {"$in": english_interests}
    else:
        # 宽松模式：不限制专业，只按其他条件筛选
        pass

    # 预算转换 (人民币转美元，汇率约7.2)
    budget_map = {
        "35万-40万": 56000,  # 40万人民币 ≈ 5.6万美元
        "40万-50万": 70000,  # 50万人民币 ≈ 7万美元
        "50万-60万": 84000,  # 60万人民币 ≈ 8.4万美元
        "60万+": 100000     # 60万以上人民币 ≈ 10万美元
    }
    max_tuition = budget_map.get(input_data.budget, 100000)
    
    if strict_mode:
        # 严格模式：按预算限制
        filters["tuition"] = {"$lte": max_tuition}
    else:
        # 宽松模式：放宽预算限制（增加50%）
        filters["tuition"] = {"$lte": max_tuition * 1.5}

    # GPA范围 → 最高可申请的学校排名
    gpa_rank_map = {
        "3.6-": 150,
        "3.6+": 100,
        "3.8+": 60,
        "3.9+": 30
    }
    max_rank = gpa_rank_map.get(input_data.gpa_range, 200)
    
    if strict_mode:
        # 严格模式：按GPA限制排名
        filters["rank"] = {"$lte": max_rank}
    else:
        # 宽松模式：放宽排名限制（增加50%）
        filters["rank"] = {"$lte": max_rank * 1.5}

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
    """学校评分算法 - 10个维度，总分100分"""
    total_score = 0.0
    
    # 1. 专业匹配度（20分）
    if input_data.interest_fields and school.get("strengths"):
        matches = sum(1 for interest in input_data.interest_fields 
                     for strength in school["strengths"] 
                     if interest.lower() in strength.lower() or strength.lower() in interest.lower())
        if len(input_data.interest_fields) > 0:
            major_match_score = min(20.0, (matches / len(input_data.interest_fields)) * 20)
            total_score += major_match_score
    
    # 2. 排名匹配度（15分）
    if input_data.reputation_important and school.get("rank"):
        rank_score = max(0.0, 15 * (1 - school["rank"] / 300))
        total_score += rank_score
    
    # 3. 实习项目支持程度（10分）
    internship_score = school.get("internship_support_score", 0.0)
    if isinstance(internship_score, (int, float)):
        total_score += min(10.0, max(0.0, float(internship_score)))
    
    # 4. 学校类型偏好匹配（10分）
    if input_data.school_type_preference and school.get("type"):
        if input_data.school_type_preference.lower() == school["type"].lower():
            total_score += 10.0
    
    # 5. 预算匹配（10分）
    if input_data.budget and school.get("tuition"):
        budget_max = parse_budget_max(input_data.budget)
        if budget_max and school["tuition"] <= budget_max:
            total_score += 10.0
        elif budget_max:
            # 线性衰减：超出预算越多扣分越多
            overshoot_ratio = (school["tuition"] - budget_max) / budget_max
            budget_score = max(0.0, 10.0 * (1 - overshoot_ratio))
            total_score += budget_score
    
    # 6. 活动经历匹配（15分）
    if input_data.activities and school.get("tags"):
        activity_score = 0.0
        activity_mappings = {
            "学术竞赛": "academic_competitions",
            "科研": "undergrad_research", 
            "学生会": "student_government_support",
            "社团活动": "student_club_support",
            "志愿服务": "community_service_opportunities",
            "实习经历": "career_center_support",
            "创业经历": "entrepreneurship_friendly",
            "推荐信准备": "recommendation_letter_support",
            "职业规划": "career_center_support",
            "社区服务": "community_service_opportunities"
        }
        
        for activity in input_data.activities:
            for activity_key, tag_value in activity_mappings.items():
                if activity_key in activity and tag_value in school["tags"]:
                    activity_score += 2.5
        
        total_score += min(15.0, activity_score)
    
    # 7. 录取率合理性（10分）
    # 录取率部分（5分）
    if school.get("acceptanceRate") is not None:
        acceptance_rate = school["acceptanceRate"]
        if acceptance_rate >= 0.15:
            total_score += 5.0
        elif acceptance_rate > 0.05:
            # 线性插值：0.05-0.15之间
            rate_score = 5.0 * (acceptance_rate - 0.05) / (0.15 - 0.05)
            total_score += rate_score
    
    # 国际生比例部分（5分）
    if school.get("intlRate") is not None:
        intl_rate = school["intlRate"]
        if intl_rate >= 0.35:
            total_score += 5.0
        elif intl_rate > 0.03:
            # 线性插值：0.03-0.35之间
            intl_score = 5.0 * (intl_rate - 0.03) / (0.35 - 0.03)
            total_score += intl_score
    
    # 8. 学校人格适配度（5分）
    if school.get("personality_types") and hasattr(input_data, 'student_type'):
        # 这里需要从学生画像中获取学生类型，暂时跳过
        # 未来可以实现更复杂的匹配逻辑
        pass
    
    # 9. 地理偏好匹配（5分）
    if hasattr(input_data, 'region_preference') and input_data.region_preference:
        region_preference = input_data.region_preference
        school_state = school.get("state", "")
        school_region = school.get("region", "")
        
        if (region_preference.lower() in school_state.lower() or 
            region_preference.lower() in school_region.lower()):
            total_score += 5.0
    
    return round(total_score, 2)

def parse_budget_max(budget_str: str) -> Optional[float]:
    """解析预算字符串，返回最大值"""
    try:
        # 处理中文万单位格式，如 "35万-40万"
        if "万" in budget_str:
            import re
            numbers = re.findall(r'\d+', budget_str)
            if len(numbers) >= 2:
                # 取最后一个数字作为最大值，转换为美元（汇率7.2）
                max_rmb = float(numbers[-1]) * 10000  # 万转换为元
                return max_rmb / 7.2  # 转换为美元
            elif len(numbers) == 1:
                # 单个数字，如 "60万+"
                max_rmb = float(numbers[0]) * 10000
                return max_rmb / 7.2
        
        # 处理各种预算格式
        elif "以上" in budget_str or "above" in budget_str.lower():
            # 提取数字部分
            import re
            numbers = re.findall(r'\d+', budget_str)
            if numbers:
                return float(numbers[0]) * 1000  # 假设单位是k
        
        elif "-" in budget_str:
            # 处理范围格式，如 "50000-70000"
            parts = budget_str.split("-")
            if len(parts) == 2:
                return float(parts[1])
        
        elif "k" in budget_str.lower():
            # 处理k单位，如 "50k-70k"
            import re
            numbers = re.findall(r'\d+', budget_str)
            if numbers:
                return float(numbers[-1]) * 1000  # 取最后一个数字作为最大值
        
        else:
            # 尝试直接解析数字
            import re
            numbers = re.findall(r'\d+', budget_str)
            if numbers:
                return float(numbers[-1])  # 取最后一个数字
        
        return None
    except:
        return None

async def recommend_schools_for_parent(input_data: ParentEvaluationInput) -> List[str]:
    """根据家长评估输入推荐学校"""
    from db.mongo import get_db
    db = get_db()
    
    if db is None:
        # 如果全局数据库连接不可用，创建新的连接
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.university_matcher
    
    # 第一步：使用严格模式筛选
    strict_filters = build_hard_filters(input_data, strict_mode=True)
    filtered_schools = await db.universities.find(strict_filters).to_list(length=None)
    
    # 如果严格筛选结果太少，使用宽松模式
    if len(filtered_schools) < 5:
        print(f"⚠️ 严格筛选只找到 {len(filtered_schools)} 所学校，切换到宽松模式...")
        
        # 使用宽松模式重新筛选
        loose_filters = build_hard_filters(input_data, strict_mode=False)
        filtered_schools = await db.universities.find(loose_filters).to_list(length=None)
        print(f"🔍 宽松模式找到 {len(filtered_schools)} 所学校")
        
        # 如果宽松模式还是太少，进一步放宽条件
        if len(filtered_schools) < 5:
            print(f"⚠️ 宽松筛选仍只找到 {len(filtered_schools)} 所学校，进一步放宽条件...")
            
            # 进一步放宽：只保留国家限制，移除其他所有限制
            basic_filters = {"country": input_data.target_country}
            filtered_schools = await db.universities.find(basic_filters).to_list(length=None)
            print(f"🔍 基础筛选找到 {len(filtered_schools)} 所学校")
    
    # 确保至少有10所学校进入评分环节
    if len(filtered_schools) < 10:
        print(f"⚠️ 筛选后学校数量不足，当前只有 {len(filtered_schools)} 所")
        
        # 如果还是太少，从数据库中随机选择一些学校补充
        if len(filtered_schools) < 5:
            # 获取所有美国学校
            all_us_schools = await db.universities.find({"country": "USA"}).to_list(length=None)
            
            # 随机选择一些学校补充（避免重复）
            existing_ids = {str(school["_id"]) for school in filtered_schools}
            additional_schools = []
            
            for school in all_us_schools:
                if str(school["_id"]) not in existing_ids and len(additional_schools) < 10:
                    additional_schools.append(school)
                    existing_ids.add(str(school["_id"]))
            
            filtered_schools.extend(additional_schools)
            print(f"🔍 补充后共有 {len(filtered_schools)} 所学校")
    
    # 为每所学校打分
    scored_schools = [(school, score_school(school, input_data)) for school in filtered_schools]
    
    # 按分数排序
    top_schools = sorted(scored_schools, key=lambda x: x[1], reverse=True)
    
    # 返回前10所学校的ID
    top_10_ids = [str(school["_id"]) for school, _ in top_schools[:10]]
    
    print(f"✅ 最终推荐 {len(top_10_ids)} 所学校")
    return top_10_ids

def classify_applications(recommended_schools: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """分类ED/EA/RD申请策略 - 智能推荐完整的申请组合
    
    策略：
    1. ED: 1所最适合的学校（支持ED且排名较高）
    2. EA: 2-3所支持EA的学校（避免与ED重复）
    3. RD: 至少3所剩余学校，确保申请策略完整
    """
    if not recommended_schools:
        return None, [], []
    
    print(f"🔍 开始分类 {len(recommended_schools)} 所学校...")
    
    # 初始化结果
    ed_suggestion = None
    ea_suggestions = []
    rd_suggestions = []
    
    # 按排名排序学校，确保选择质量
    sorted_schools = sorted(recommended_schools, key=lambda x: x.get("rank", 999))
    
    # 1. 选择ED学校：优先选择支持ED且排名较高的学校
    for school in sorted_schools:
        if school.get("supports_ed", False):  # 明确检查是否支持ED
            ed_suggestion = school
            print(f"✅ 选择ED学校: {school.get('name', 'Unknown')} (排名: {school.get('rank', 'N/A')})")
            break
    
    # 如果没有找到支持ED的学校，不强制推荐ED
    if ed_suggestion is None:
        print(f"⚠️ 未找到支持ED的学校，本次不推荐ED申请")
        ed_suggestion = None
    
    # 2. 选择EA学校：选择支持EA的学校，避免与ED重复
    ea_count = 0
    max_ea = 3  # 最多推荐3所EA学校
    
    for school in sorted_schools:
        if ea_count >= max_ea:
            break
            
        # 跳过已选为ED的学校
        if ed_suggestion and str(school.get("id", "")) == str(ed_suggestion.get("id", "")):
            continue
            
        # 选择支持EA的学校
        if school.get("supports_ea", False):
            ea_suggestions.append(school)
            ea_count += 1
            print(f"✅ 选择EA学校: {school.get('name', 'Unknown')} (排名: {school.get('rank', 'N/A')})")
    
    # 如果EA学校太少，从剩余学校中补充（只补充真正支持EA的学校）
    if len(ea_suggestions) < 2:
        remaining_for_ea = [s for s in sorted_schools 
                           if s not in ea_suggestions and 
                           (ed_suggestion is None or str(s.get("id", "")) != str(ed_suggestion.get("id", ""))) and
                           s.get("supports_ea", False)]  # 只选择支持EA的学校
        
        for school in remaining_for_ea[:2 - len(ea_suggestions)]:
            ea_suggestions.append(school)
            print(f"✅ 补充EA学校: {school.get('name', 'Unknown')} (排名: {school.get('rank', 'N/A')})")
        
        # 如果仍然不足2所EA学校，说明支持EA的学校确实不够
        if len(ea_suggestions) < 2:
            print(f"⚠️ 支持EA的学校不足2所，当前只有 {len(ea_suggestions)} 所")
    
    # 3. 选择RD学校：剩余的所有学校，确保至少3所
    for school in sorted_schools:
        # 跳过已选为ED和EA的学校
        if (ed_suggestion and str(school.get("id", "")) == str(ed_suggestion.get("id", ""))) or \
           any(str(ea.get("id", "")) == str(school.get("id", "")) for ea in ea_suggestions):
            continue
        rd_suggestions.append(school)
    
    # 如果RD学校太少，从EA学校中转移一些到RD
    if len(rd_suggestions) < 3 and len(ea_suggestions) > 2:
        transfer_count = min(3 - len(rd_suggestions), len(ea_suggestions) - 2)
        for i in range(transfer_count):
            school = ea_suggestions.pop()
            rd_suggestions.append(school)
            print(f"🔄 将 {school.get('name', 'Unknown')} 从EA转移到RD")
    
    # 最终统计
    print(f"📊 分类完成:")
    print(f"   ED: {ed_suggestion.get('name', 'None') if ed_suggestion else 'None'}")
    print(f"   EA: {len(ea_suggestions)} 所 - {[s.get('name', 'Unknown') for s in ea_suggestions]}")
    print(f"   RD: {len(rd_suggestions)} 所 - {[s.get('name', 'Unknown') for s in rd_suggestions[:3]]}")
    
    return ed_suggestion, ea_suggestions, rd_suggestions

def generate_student_profile(input_data: ParentEvaluationInput) -> Dict[str, str]:
    """生成学生画像 - 支持8种类型分类"""
    
    # 提取关键数据
    gpa_range = input_data.gpa_range
    sat_score = input_data.sat_score
    activities = input_data.activities
    interest_fields = input_data.interest_fields
    internship_important = input_data.internship_important
    target_country = input_data.target_country
    budget = input_data.budget
    family_expectation = input_data.family_expectation
    
    # 解析GPA范围获取数值
    gpa_numeric = parse_gpa_range(gpa_range)
    
    # 按优先级顺序判断学生类型
    # 1. 学术明星型（ACADEMIC_STAR）
    if (gpa_numeric >= 3.8 and sat_score and sat_score >= 1450 and 
        has_research_competition_activities(activities) and 
        len(interest_fields) >= 3):
        return {
            "type": "学术明星型（ACADEMIC_STAR）",
            "description": f"您的孩子是一位{gpa_range}的优秀学生，SAT {sat_score}分，在学术方面极为突出。{format_activities_description(activities)}，对{', '.join(interest_fields)}领域表现出浓厚兴趣。适合冲击Top 30高排名大学，建议采用积极申请策略。"
        }
    
    # 2. 全能型（BALANCED）
    if (gpa_numeric >= 3.5 and len(activities) >= 2 and 
        has_diverse_activities(activities) and len(interest_fields) >= 3):
        return {
            "type": "全能型（BALANCED）",
            "description": f"您的孩子是一位{gpa_range}的学生，{format_activities_description(activities)}，在学术和活动方面均衡发展。对{', '.join(interest_fields)}领域表现出浓厚兴趣。适合多方向平衡申请策略，建议ED+EA+RD组合申请。"
        }
    
    # 3. 探究型（RESEARCHER）
    if (has_research_activities(activities) and len(interest_fields) >= 3 and gpa_numeric >= 3.5):
        return {
            "type": "探究型（RESEARCHER）",
            "description": f"您的孩子是一位{gpa_range}的学生，{format_research_activities_description(activities)}，偏好探索与深度学习。对{', '.join(interest_fields)}领域有明确兴趣。建议关注研究资源丰富、本科研究机会多的学校。"
        }
    
    # 4. 实践型（ENTREPRENEUR）
    if (has_entrepreneurial_activities(activities) and internship_important):
        return {
            "type": "实践型（ENTREPRENEUR）",
            "description": f"您的孩子{gpa_range}，{format_entrepreneurial_activities_description(activities)}，具备实战能力。对{', '.join(interest_fields)}领域有浓厚兴趣。适合项目驱动型、就业导向型大学，建议关注实习资源丰富的学校。"
        }
    
    # 5. 创意型（ARTSY）
    if (has_artistic_activities(activities) and has_artistic_interests(interest_fields)):
        return {
            "type": "创意型（ARTSY）",
            "description": f"您的孩子{gpa_range}，{format_artistic_activities_description(activities)}，具有艺术天赋和创造力。对{', '.join(interest_fields)}领域表现出浓厚兴趣。适合自由度高、艺术氛围浓的学校环境，建议关注艺术专业强的学校。"
        }
    
    # 6. 探索型（EXPLORER）
    if (len(interest_fields) >= 3 and has_diverse_interests(interest_fields) and len(activities) >= 2):
        return {
            "type": "探索型（EXPLORER）",
            "description": f"您的孩子{gpa_range}，{format_activities_description(activities)}，兴趣广泛且跨度较大。对{', '.join(interest_fields)}等多个领域都有兴趣。尚未聚焦特定方向，适合通识教育丰富、跨学科自由度高的学校。"
        }
    
    # 7. 努力型（HARDWORKER）
    if (gpa_numeric >= 3.2 and gpa_numeric < 3.6 and 
        has_clear_goals(target_country, interest_fields) and has_budget_match(budget)):
        return {
            "type": "努力型（HARDWORKER）",
            "description": f"您的孩子{gpa_range}，{format_activities_description(activities)}，目标明确且务实。对{', '.join(interest_fields)}领域有明确规划，预算匹配合理。建议匹配型+保底策略，重点准备申请材料和动机陈述。"
        }
    
    # 8. 潜力型（POTENTIAL）
    if ((gpa_numeric < 3.2 or len(activities) < 2) and 
        (has_high_budget(budget) or has_high_expectation(family_expectation))):
        return {
            "type": "潜力型（POTENTIAL）",
            "description": f"您的孩子{gpa_range}，{format_activities_description(activities)}，虽然当前表现有待提升，但发展潜力高。家庭支持充分，期待明确。建议稳健申请策略，适当增加背景材料，关注提供学术支持项目的学校。"
        }
    
    # 默认情况 - 如果都不匹配，返回努力型
    return {
        "type": "努力型（HARDWORKER）",
        "description": f"您的孩子{gpa_range}，{format_activities_description(activities)}，对{', '.join(interest_fields)}领域有兴趣。建议采用稳健的申请策略，重点关注匹配校和保底校。"
    }

# 辅助函数
def parse_gpa_range(gpa_range: str) -> float:
    """解析GPA范围字符串，返回数值"""
    if gpa_range == "3.9+":
        return 3.9
    elif gpa_range == "3.8+":
        return 3.8
    elif gpa_range == "3.6+":
        return 3.6
    elif gpa_range == "3.6-":
        return 3.2
    else:
        return 3.0  # 默认值

def has_research_competition_activities(activities: List[str]) -> bool:
    """检查是否包含科研/竞赛活动"""
    research_keywords = ["科研", "竞赛", "论文", "夏校", "实验室", "research", "competition"]
    return any(keyword in activity for activity in activities for keyword in research_keywords)

def has_diverse_activities(activities: List[str]) -> bool:
    """检查活动是否多样化"""
    activity_categories = {
        "academic": ["科研", "竞赛", "论文", "夏校"],
        "social": ["社团活动", "学生会", "志愿服务"],
        "practical": ["实习经历", "创业经历", "项目"]
    }
    
    categories_found = 0
    for category_activities in activity_categories.values():
        if any(activity in activities for activity in category_activities):
            categories_found += 1
    
    return categories_found >= 2

def has_research_activities(activities: List[str]) -> bool:
    """检查是否包含科研活动"""
    research_keywords = ["科研", "夏校", "论文", "实验室", "research"]
    return any(keyword in activity for activity in activities for keyword in research_keywords)

def has_entrepreneurial_activities(activities: List[str]) -> bool:
    """检查是否包含创业/实践类活动"""
    entrepreneurial_keywords = ["项目", "创业", "技术比赛", "hackathon", "startup"]
    return any(keyword in activity for activity in activities for keyword in entrepreneurial_keywords)

def has_artistic_activities(activities: List[str]) -> bool:
    """检查是否包含艺术类活动"""
    artistic_keywords = ["艺术", "表演", "设计", "音乐", "绘画", "art", "performance", "design"]
    return any(keyword in activity for activity in activities for keyword in artistic_keywords)

def has_artistic_interests(interest_fields: List[str]) -> bool:
    """检查兴趣是否包含艺术类"""
    artistic_keywords = ["艺术", "设计", "音乐", "表演", "文学", "art", "design", "music"]
    return any(keyword in field for field in interest_fields for keyword in artistic_keywords)

def has_diverse_interests(interest_fields: List[str]) -> bool:
    """检查兴趣是否多样化"""
    if len(interest_fields) < 3:
        return False
    
    # 检查是否有理工+人文的组合
    stem_keywords = ["计算机", "工程", "科学", "数学", "computer", "engineering", "science"]
    humanities_keywords = ["文学", "历史", "哲学", "艺术", "literature", "history", "philosophy"]
    
    has_stem = any(keyword in field for field in interest_fields for keyword in stem_keywords)
    has_humanities = any(keyword in field for field in interest_fields for keyword in humanities_keywords)
    
    return has_stem and has_humanities

def has_clear_goals(target_country: str, interest_fields: List[str]) -> bool:
    """检查是否有明确目标"""
    return bool(target_country and len(interest_fields) >= 1)

def has_budget_match(budget: str) -> bool:
    """检查预算是否明确"""
    return bool(budget and budget != "")

def has_high_budget(budget: str) -> bool:
    """检查是否高预算"""
    high_budget_keywords = ["70000", "80000", "90000", "100000", "高"]
    return any(keyword in budget for keyword in high_budget_keywords)

def has_high_expectation(family_expectation: str) -> bool:
    """检查家长期待是否高"""
    return family_expectation in ["high", "高", "很高"]

def format_activities_description(activities: List[str]) -> str:
    """格式化活动描述"""
    if not activities:
        return "活动经历相对简单"
    
    if len(activities) == 1:
        return f"在{activities[0]}方面有丰富经验"
    elif len(activities) == 2:
        return f"在{activities[0]}和{activities[1]}方面有丰富经验"
    else:
        return f"在{', '.join(activities[:2])}等方面有丰富经验"

def format_research_activities_description(activities: List[str]) -> str:
    """格式化科研活动描述"""
    research_activities = [activity for activity in activities if "科研" in activity or "夏校" in activity or "论文" in activity]
    if research_activities:
        return f"在{', '.join(research_activities)}方面有丰富经验"
    return "在科研方面有丰富经验"

def format_entrepreneurial_activities_description(activities: List[str]) -> str:
    """格式化创业活动描述"""
    entrepreneurial_activities = [activity for activity in activities if "项目" in activity or "创业" in activity or "技术比赛" in activity]
    if entrepreneurial_activities:
        return f"在{', '.join(entrepreneurial_activities)}方面有丰富经验"
    return "在实践项目方面有丰富经验"

def format_artistic_activities_description(activities: List[str]) -> str:
    """格式化艺术活动描述"""
    artistic_activities = [activity for activity in activities if "艺术" in activity or "表演" in activity or "设计" in activity]
    if artistic_activities:
        return f"在{', '.join(artistic_activities)}方面有丰富经验"
    return "在艺术创作方面有丰富经验"

def generate_application_strategy(input_data: ParentEvaluationInput, school_count: int) -> str:
    """生成申请策略建议"""
    strategy = f"基于您孩子的背景，我们为您推荐了{school_count}所适合的大学。"
    
    if input_data.gpa_range == "3.9+" or input_data.gpa_range == "3.8+":
        strategy += " 建议采用积极申请策略，重点考虑Top 30的学校。"
    elif input_data.gpa_range == "3.6+":
        strategy += " 建议采用平衡申请策略，包括冲刺校、匹配校和保底校。"
    else:
        strategy += " 建议采用稳健申请策略，重点关注匹配校和保底校。"
    
    strategy += f" 重点关注{input_data.target_country}的优质大学，这些学校在您感兴趣的领域都有很强的实力。"
    
    return strategy 