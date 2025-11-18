"""
Australia (AU) parent evaluation logic - 16题版本（2024新规范）

实现完整的硬过滤、评分（100分）、回退策略和解释生成。

评分字段：
1. rank (10分) - 学术水平匹配
2. strengths (20分) - 专业兴趣匹配
3. tuition_usd (10分) - 预算匹配
4. work_integrated_learning + placement_rate (10分) - WIL/实习
5. group_of_eight (8分) - Go8偏好
6. city (6分) - 城市匹配
7. post_study_visa_years (8分) - PSW年限
8. requires_english_test (6分) - 英语准备
9. intlRate (6分) - 国际社区
10. scholarship_available (6分) - 奖学金
11. study_length_years (5分) - 学制偏好
12. intakes (5分) - 入学时间匹配

权重调节字段（不单独计分）：
- reputation_vs_value: 名气优先/均衡/性价比优先 → 调节rank权重
- career_focus: 就业口碑/带实习标签 → 调节WIL内部配重
- main_concern: 最担心点 → 用于解释排序和回退优先级

硬过滤（可开关）：
- hard_budget_must_within: 必须≤预算
- hard_english_required_exclude: 不接受语言/过渡课（反向：接受则保留但低分）
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional


def _rank_band_for_academic(band: str) -> Tuple[int, int]:
    """映射学术水平到排名区间"""
    if band == "3.9+":
        return (1, 60)
    if band == "3.8+":
        return (1, 100)
    if band == "3.6+":
        return (60, 200)
    return (100, 300)


def _normalize_list(value: Any) -> List[str]:
    """标准化列表字段"""
    if isinstance(value, list):
        return [str(s).strip().lower() for s in value if str(s).strip()]
    if isinstance(value, str):
        return [s.strip().lower() for s in value.split(',') if s.strip()]
    return []


def _normalize_city(city: str) -> str:
    """城市名称归一化（大小写/别名）"""
    city_map = {
        "sydney": "sydney", "悉尼": "sydney",
        "melbourne": "melbourne", "墨尔本": "melbourne",
        "brisbane": "brisbane", "布里斯班": "brisbane",
        "adelaide": "adelaide", "阿德莱德": "adelaide",
        "perth": "perth", "珀斯": "perth",
    }
    c = city.strip().lower()
    return city_map.get(c, c)


def _normalize_strengths(strengths: List[str]) -> List[str]:
    """专业名称同义词归一化"""
    synonym_groups = {
        "cs": ["cs", "computer science", "it", "software", "computing", "information technology"],
        "ai": ["ai", "artificial intelligence", "machine learning", "ml", "data science"],
        "engineering": ["engineering", "eng", "tech", "mechanical", "civil", "electrical", "chemical"],
        "business": ["business", "commerce", "management", "mba", "marketing", "accounting"],
        "economics": ["economics", "econ", "finance", "financial"],
        "design": ["design", "art", "creative", "graphic design", "fashion"],
        "medicine": ["medicine", "medical", "health", "biomedical"],
        "law": ["law", "legal", "jurisprudence"],
        "education": ["education", "teaching", "pedagogy"],
        "architecture": ["architecture", "architectural", "urban planning"],
        "nursing": ["nursing", "nurse", "healthcare"],
        "psychology": ["psychology", "psych", "counseling"],
        "pharmacy": ["pharmacy", "pharmaceutical"],
        "veterinary": ["veterinary", "vet", "animal science"],
        "agriculture": ["agriculture", "agricultural", "agronomy"],
        "arts": ["arts", "fine arts", "visual arts"],
        "humanities": ["humanities", "history", "philosophy", "literature"],
        "natural sciences": ["natural sciences", "biology", "chemistry", "physics", "mathematics"],
        "public health": ["public health", "epidemiology", "health policy"],
        "communication": ["communication", "media", "journalism", "public relations"],
        "film": ["film", "cinema", "film studies", "media production"],
        "marine science": ["marine science", "oceanography", "marine biology"],
        "social work": ["social work", "social services"],
        "tourism": ["tourism", "hospitality", "tourism management"],
        "sports science": ["sports science", "exercise science", "kinesiology", "sports"],
    }
    normalized = []
    for s in strengths:
        s_lower = s.lower()
        matched = False
        for key, synonyms in synonym_groups.items():
            if any(syn in s_lower for syn in synonyms):
                normalized.append(key)
                matched = True
                break
        if not matched:
            normalized.append(s_lower)
    return normalized


def _score_rank(rank: int, target_band: Tuple[int, int], reputation_weight: float = 1.0) -> float:
    """Q1: 学术水平匹配（10分），reputation_weight 用于权重调节"""
    if rank is None:
        return 0.0
    low, high = target_band
    base_score = 10.0 if low <= rank <= high else max(0.0, 10.0 - 5.0 * ((abs(rank - (low if rank < low else high)) + 49) // 50))
    return base_score * reputation_weight


def _score_interests(selected: List[str], strengths: List[str]) -> float:
    """Q2: 专业兴趣匹配（20分）"""
    if not selected:
        return 0.0
    selected_norm = _normalize_strengths(selected)
    strengths_norm = _normalize_strengths(strengths)
    hits = sum(1 for s in selected_norm if any(s in st for st in strengths_norm) or any(st in s for st in strengths_norm))
    return min(20.0, 20.0 * (hits / max(1, len(selected_norm))))


def _score_budget(tuition_usd: int, budget_usd: int) -> float:
    """Q3: 预算匹配（10分）"""
    if budget_usd <= 0 or tuition_usd is None:
        return 0.0
    if tuition_usd <= budget_usd:
        return 10.0
    over_ratio = (tuition_usd - budget_usd) / budget_usd
    return max(0.0, 10.0 * (1.0 - over_ratio))


def _score_wil(wil_pref: str, wil: bool, placement_rate: Optional[float], career_focus: str) -> float:
    """Q4: WIL/实习（10分），career_focus 用于内部配重"""
    rate = float(placement_rate or 0.0)
    
    # 根据career_focus调整placement_rate权重
    if career_focus == "就业口碑" and rate > 0:
        placement_weight = 1.2
    elif career_focus == "带实习标签" and wil:
        placement_weight = 1.3
    else:
        placement_weight = 1.0
    
    if wil_pref == "必须":
        return (7.0 + min(3.0, rate * 3.0 * placement_weight)) if wil else 0.0
    if wil_pref == "加分":
        return (5.0 + min(2.0, rate * 2.0 * placement_weight)) if wil else 4.0
    return 3.0


def _score_study_length(pref: str, length_years: Optional[float]) -> float:
    """Q11: 学制偏好（5分）"""
    if length_years is None:
        return 3.0  # 中性分
    length = float(length_years)
    standard = 3.5  # 标准学制约3.5年
    
    if pref == "越短越好":
        return 5.0 if length <= standard else max(2.0, 5.0 - (length - standard) * 2.0)
    if pref == "可接受标准学制":
        return 5.0 if abs(length - standard) <= 0.5 else 3.0
    return 3.0  # 不在意


def _score_intakes(pref: str, intakes: Optional[str]) -> float:
    """Q12: 入学时间匹配（5分）"""
    if not intakes:
        return 3.0  # 中性分
    
    intake_str = str(intakes).lower()
    has_feb = "feb" in intake_str or "2月" in intake_str or "february" in intake_str
    has_jul = "jul" in intake_str or "7月" in intake_str or "july" in intake_str
    has_recent_intake = has_feb or has_jul
    
    if pref == "越快越好（6–12个月内）":
        return 5.0 if has_recent_intake else 3.0
    if pref == "1–2年内":
        return 4.0 if has_recent_intake else 3.0
    return 3.0  # 不确定


def _score_go8(pref: str, go8: bool) -> float:
    """Q5: Go8偏好（8分）"""
    if pref == "强烈偏好":
        return 8.0 if go8 else 3.0
    if pref == "可以考虑":
        return 6.0 if go8 else 5.0
    return 5.0  # 没有明确偏好


def _score_city(pref_cities: List[str], city: str) -> float:
    """Q6: 城市匹配（6分，原逻辑按比例缩放）"""
    city_norm = _normalize_city(city)
    pref_norm = [_normalize_city(c) for c in pref_cities]
    
    if not pref_cities or "不限" in pref_cities or any("不限" in c for c in pref_cities):
        return 7.0 * (6.0 / 10.0)  # 不限→7分，缩放到6分制
    
    if city_norm in pref_norm:
        return 6.0  # 命中满分
    
    return 5.0 * (6.0 / 10.0)  # 不命中→5分，缩放到6分制


def _score_psw(importance: str, psw_years: Optional[float]) -> float:
    """Q7: PSW年限（8分）"""
    if psw_years is None:
        psw_years = 2.0
    psw = max(2.0, min(4.0, float(psw_years)))
    
    if importance == "非常在意":
        return 8.0 * ((psw - 2.0) / 2.0)  # 2年→0分，4年→8分
    if importance == "一般":
        return 6.0 * (8.0 / 10.0)  # 约4.8分
    return 4.0 * (8.0 / 10.0)  # 约3.2分


def _score_english(readiness: str, requires_english_test: bool, accept_language_course: bool) -> float:
    """Q8: 英语准备（6分）"""
    if not requires_english_test:
        return 4.0 * (6.0 / 5.0)  # 不要求给约4.8分
    
    if readiness == "已达标":
        return 6.0
    if readiness == "3个月内可达":
        return 3.0 * (6.0 / 5.0)  # 约3.6分
    # 需更长
    if accept_language_course:
        return 1.0 * (6.0 / 5.0)  # 接受语言班给低保底约1.2分
    return 0.0  # 不接受语言班，且需更长，给0分


def _score_intl_community(pref: str, intl_rate: Optional[float]) -> float:
    """Q9: 国际社区（6分，区间0.1–0.6线性映射）"""
    rate = float(intl_rate or 0.0)
    
    if pref == "重要":
        clamped = max(0.1, min(0.6, rate))
        return 6.0 * ((clamped - 0.1) / 0.5)  # 0.1→0分，0.6→6分
    if pref == "一般":
        return 3.0 * (6.0 / 5.0)  # 约3.6分
    return 2.0 * (6.0 / 5.0)  # 约2.4分


def _score_scholarship(pref: str, has_scholarship: bool) -> float:
    """Q10: 奖学金（6分，原逻辑按比例缩放）"""
    if pref == "很重要":
        return 6.0 if has_scholarship else 3.0 * (6.0 / 10.0)  # 约1.8分
    if pref == "一般":
        return 7.0 * (6.0 / 10.0) if has_scholarship else 5.0 * (6.0 / 10.0)  # 约4.2/3.0分
    return 5.0 * (6.0 / 10.0)  # 约3.0分


def apply_au_filters_and_score(
    input_data: Dict[str, Any],
    au_docs: List[Dict[str, Any]],
    enable_fallback: bool = True
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    应用硬过滤和评分，支持回退策略。
    
    返回: (scored_universities, fallback_info)
    fallback_info 包含: {"applied": bool, "steps": List[str]}
    """
    # 确保au_docs不为None
    if au_docs is None:
        au_docs = []
    
    # 提取硬过滤参数
    hard_budget = bool(input_data.get("hard_budget_must_within", False))
    budget_usd = int(input_data.get("budget_usd", 0) or 0)
    wil_pref = str(input_data.get("wil_preference", "不重要"))
    must_wil = (wil_pref == "必须")
    pref_cities = _normalize_list(input_data.get("city_preferences", []))
    has_city_limit = pref_cities and "不限" not in [c.lower() for c in pref_cities]
    accept_language = bool(input_data.get("accept_language_course", True))  # 默认接受
    hard_english_exclude = bool(input_data.get("hard_english_required_exclude", False))  # 默认False，即接受语言班
    
    fallback_info = {"applied": False, "steps": []}
    filtered = []
    
    # 初始硬过滤
    for d in au_docs:
        if str(d.get("country")) != "Australia":
            continue
        
        # 预算硬过滤
        if hard_budget and int(d.get("tuition_usd", 0) or 0) > budget_usd:
            continue
        
        # WIL硬过滤
        if must_wil and not bool(d.get("work_integrated_learning", False)):
            continue
        
        # 城市硬过滤
        if has_city_limit:
            city_norm = _normalize_city(str(d.get("city") or ""))
            pref_norm = [_normalize_city(c) for c in pref_cities]
            if city_norm not in pref_norm:
                continue
        
        # 英语硬过滤（只有明确"不接受语言班"且需更长才排除）
        if hard_english_exclude and bool(d.get("requires_english_test", False)):
            english_ready = str(input_data.get("english_readiness", ""))
            if english_ready == "需更长":
                continue
        
        filtered.append(d)
    
    # 如果为空且启用回退，逐级放宽
    if len(filtered) == 0 and enable_fallback:
        fallback_info["applied"] = True
        
        # Step 1: 放宽城市
        if has_city_limit:
            fallback_info["steps"].append("放宽城市限制")
            filtered = [d for d in au_docs if str(d.get("country")) == "Australia"]
            if len(filtered) > 0:
                # 继续后续过滤
                pass
        
        # Step 2: 放宽预算（+10%）
        if hard_budget and len(filtered) == 0:
            fallback_info["steps"].append("放宽预算至 +10%")
            budget_expanded = int(budget_usd * 1.1)
            filtered = [
                d for d in au_docs
                if str(d.get("country")) == "Australia"
                and int(d.get("tuition_usd", 0) or 0) <= budget_expanded
            ]
        
        # Step 3: 放宽英语（解除一刀切）
        if hard_english_exclude and len(filtered) == 0:
            fallback_info["steps"].append("放宽英语要求（保留需语言班学校）")
            filtered = [
                d for d in au_docs
                if str(d.get("country")) == "Australia"
            ]
            if hard_budget:
                filtered = [d for d in filtered if int(d.get("tuition_usd", 0) or 0) <= int(budget_usd * 1.1)]
        
        # Step 4: 放宽WIL"必须"到"优先"
        if must_wil and len(filtered) == 0:
            fallback_info["steps"].append("放宽WIL要求（从'必须'改为'优先'）")
            filtered = [
                d for d in au_docs
                if str(d.get("country")) == "Australia"
            ]
        
        # Step 5: 兜底池（Top 200最低学费10所，如果仍为空则取所有AU学校）
        if len(filtered) == 0:
            fallback_info["steps"].append("启用兜底池（Top 200最低学费10所）")
            all_au = [d for d in au_docs if str(d.get("country")) == "Australia"]
            if all_au:
                sorted_by_rank = sorted(all_au, key=lambda x: int(x.get("rank", 9999) or 9999))
                top200 = sorted_by_rank[:200] if len(sorted_by_rank) > 200 else sorted_by_rank
                sorted_by_tuition = sorted(top200, key=lambda x: int(x.get("tuition_usd", 999999) or 999999))
                filtered = sorted_by_tuition[:10]
            else:
                # 如果数据库里没有任何AU学校，至少返回空列表（这种情况不应该发生）
                filtered = []
        
        # 最终兜底：如果经过所有回退步骤后仍为空，至少返回排名前10的AU学校
        if len(filtered) == 0:
            all_au = [d for d in au_docs if str(d.get("country")) == "Australia"]
            if all_au:
                fallback_info["steps"].append("最终兜底：返回所有可用澳洲学校（按排名）")
                sorted_by_rank = sorted(all_au, key=lambda x: int(x.get("rank", 9999) or 9999))
                filtered = sorted_by_rank[:10]
    
    # 评分
    academic_band = str(input_data.get("academic_band", "3.6-"))
    target_band = _rank_band_for_academic(academic_band)
    interests = _normalize_list(input_data.get("interests", []))
    reputation_vs_value = str(input_data.get("reputation_vs_value", "均衡"))
    wil_pref = str(input_data.get("wil_preference", "不重要"))
    go8_pref = str(input_data.get("go8_preference", "没有明确偏好"))
    psw_importance = str(input_data.get("psw_importance", "一般"))
    english_ready = str(input_data.get("english_readiness", "3个月内可达"))
    intl_pref = str(input_data.get("intl_community_importance", "一般"))
    scholarship_pref = str(input_data.get("scholarship_importance", "不重要"))
    study_length_pref = str(input_data.get("study_length_preference", "不在意"))
    intake_pref = str(input_data.get("intake_preference", "不确定"))
    career_focus = str(input_data.get("career_focus", "均衡"))
    accept_language = bool(input_data.get("accept_language_course", True))
    
    # 权重调节
    if reputation_vs_value == "名气优先":
        rank_weight = 1.2
    elif reputation_vs_value == "性价比优先":
        rank_weight = 0.8
    else:
        rank_weight = 1.0
    
    scored = []
    for d in filtered:
        strengths = _normalize_list(d.get("strengths", []))
        total = 0.0
        
        total += _score_rank(int(d.get("rank", 9999) or 9999), target_band, rank_weight)
        total += _score_interests(interests, strengths)
        total += _score_budget(int(d.get("tuition_usd", 0) or 0), budget_usd)
        total += _score_wil(wil_pref, bool(d.get("work_integrated_learning", False)), d.get("placement_rate"), career_focus)
        total += _score_go8(go8_pref, bool(d.get("group_of_eight", False)))
        total += _score_city(pref_cities, str(d.get("city") or ""))
        total += _score_psw(psw_importance, d.get("post_study_visa_years"))
        total += _score_english(english_ready, bool(d.get("requires_english_test", False)), accept_language)
        total += _score_intl_community(intl_pref, d.get("intlRate"))
        total += _score_scholarship(scholarship_pref, bool(d.get("scholarship_available", False)))
        total += _score_study_length(study_length_pref, d.get("study_length_years"))
        total += _score_intakes(intake_pref, d.get("intakes"))
        
        scored.append({
            "id": str(d.get("_id")),
            "name": str(d.get("name", "")),
            "score": round(total, 2),
            "rank": int(d.get("rank", 9999) or 9999),
            "tuition_usd": int(d.get("tuition_usd", 0) or 0),
            "city": str(d.get("city", "")),
            "strengths": strengths,
            "work_integrated_learning": bool(d.get("work_integrated_learning", False)),
            "placement_rate": d.get("placement_rate"),
            "post_study_visa_years": d.get("post_study_visa_years"),
            "requires_english_test": bool(d.get("requires_english_test", False)),
            "english_requirements": d.get("english_requirements", ""),
            "intlRate": d.get("intlRate"),
            "scholarship_available": bool(d.get("scholarship_available", False)),
            "study_length_years": d.get("study_length_years"),
            "intakes": d.get("intakes", ""),
        })
    
    # 排序
    scored.sort(key=lambda x: (-x["score"], x["tuition_usd"], x["rank"]))
    return scored, fallback_info


def generate_school_explanations(school: Dict[str, Any], input_data: Dict[str, Any]) -> List[str]:
    """
    为每所学校生成6-8行可读解释，让家长清楚理解为什么推荐这所学校。
    
    返回格式：["🎓 学术层级：...", "📚 专业匹配：...", ...]
    """
    try:
        explanations = []
        
        # 1. 学术层级匹配
        academic_band = str(input_data.get("academic_band", "3.6-") or "3.6-")
        rank = int(school.get("rank", 9999) or 9999)
        band_map = {"3.9+": "1-60", "3.8+": "1-100", "3.6+": "60-200", "3.6-": "100-300"}
        target_range = band_map.get(academic_band, "100-300")
        
        if rank <= 60:
            level_desc = "与您的目标层级（Top 60）匹配"
        elif rank <= 100:
            level_desc = "接近您的目标层级（Top 100）"
        elif rank <= 200:
            level_desc = f"略超您的目标层级（目标{target_range}，该校排名{rank}）"
        else:
            level_desc = f"超出目标范围（目标{target_range}，该校排名{rank}）"
        
        explanations.append(f"🎓 学术层级：{level_desc}（全球排名 #{rank}）")
        
        # 2. 专业匹配
        interests = _normalize_list(input_data.get("interests", []))
        strengths = _normalize_list(school.get("strengths", []))
        matched = []
        for interest in interests:
            interest_norm = _normalize_strengths([interest])
            for strength in strengths:
                strength_norm = _normalize_strengths([strength])
                if any(i in s for i in interest_norm for s in strength_norm) or any(s in i for i in interest_norm for s in strength_norm):
                    matched.append(interest)
                    break
        
        if matched:
            explanations.append(f"📚 专业匹配：与您选择的 {len(matched)}/{len(interests) if interests else 1} 个方向匹配（{', '.join(matched[:3])}{'...' if len(matched) > 3 else ''}）")
        else:
            explanations.append("📚 专业匹配：部分匹配您选择的专业方向")
        
        # 3. 预算匹配
        budget_usd = int(input_data.get("budget_usd", 0) or 0)
        tuition_usd = int(school.get("tuition_usd", 0) or 0)
        hard_budget = bool(input_data.get("hard_budget_must_within", False))
        
        if budget_usd <= 0:
            budget_desc = f"学费 ${tuition_usd:,}/年（未设置预算）"
        elif tuition_usd <= budget_usd:
            budget_desc = f"学费 ${tuition_usd:,}/年，在您的预算范围内"
        else:
            over_pct = int((tuition_usd - budget_usd) / budget_usd * 100) if budget_usd > 0 else 0
            if hard_budget:
                budget_desc = f"学费 ${tuition_usd:,}/年，超出预算约{over_pct}%（需放宽预算限制）"
            else:
                budget_desc = f"学费 ${tuition_usd:,}/年，超出预算约{over_pct}%"
        
        explanations.append(f"💰 预算：{budget_desc}")
        
        # 4. 实习/WIL
        wil = bool(school.get("work_integrated_learning", False))
        placement_rate = school.get("placement_rate")
        wil_pref = str(input_data.get("wil_preference", "不重要"))
        
        if wil:
            if placement_rate:
                explanations.append(f"🧑‍🏫 实习/WIL：有带实习项目，实习成功率参考：{int(placement_rate * 100)}%")
            else:
                explanations.append("🧑‍🏫 实习/WIL：有带实习项目（WIL），提供产业项目/实习机会")
        else:
            explanations.append(f"🧑‍🏫 实习/WIL：无明确WIL项目（您选择：{wil_pref}）")
        
        # 5. 城市匹配
        city = str(school.get("city", ""))
        pref_cities = _normalize_list(input_data.get("city_preferences", []))
        has_limit = pref_cities and "不限" not in [c.lower() for c in pref_cities]
        
        if has_limit:
            city_norm = _normalize_city(city)
            pref_norm = [_normalize_city(c) for c in pref_cities]
            if city_norm in pref_norm:
                city_desc = f"位于 {city}（与您的偏好：命中）"
            else:
                city_desc = f"位于 {city}（与您的偏好：未命中）"
        else:
            city_desc = f"位于 {city}（您选择：不限）"
        
        explanations.append(f"🏙️ 城市：{city_desc}")
        
        # 6. PSW工签
        psw_years = school.get("post_study_visa_years")
        psw_importance = str(input_data.get("psw_importance", "一般"))
        
        if psw_years:
            psw_desc = f"毕业工签约 {psw_years} 年"
            if psw_importance == "非常在意":
                if psw_years >= 3:
                    psw_desc += "（符合您非常在意的需求）"
                else:
                    psw_desc += "（略低于理想年限）"
            explanations.append(f"🛂 PSW：{psw_desc}")
        else:
            explanations.append("🛂 PSW：工签年限信息未提供")
        
        # 7. 英语要求
        requires_english = bool(school.get("requires_english_test", False))
        english_ready = str(input_data.get("english_readiness", ""))
        accept_language = bool(input_data.get("accept_language_course", True))
        english_req_text = school.get("english_requirements", "")
        
        if requires_english:
            if english_ready == "已达标":
                eng_desc = f"学校要求英语成绩；您的准备度：已达标 ✓"
            elif english_ready == "3个月内可达":
                eng_desc = f"学校要求英语成绩；您的准备度：3个月内可达"
            else:
                if accept_language:
                    eng_desc = f"学校要求英语成绩；您需更长时间，可走'语言/过渡课程'方案 → 已保留但分数偏低"
                else:
                    eng_desc = f"学校要求英语成绩；您需更长时间且不接受语言班，需尽快准备"
            
            if english_req_text:
                eng_desc += f"（常见要求：{english_req_text}）"
        else:
            eng_desc = "学校不要求标化英语成绩 ✓"
        
        explanations.append(f"🗣️ 英语：{eng_desc}")
        
        # 8. 奖学金
        has_scholarship = bool(school.get("scholarship_available", False))
        scholarship_pref = str(input_data.get("scholarship_importance", "不重要"))
        
        if has_scholarship:
            explanations.append(f"🎖️ 奖学金：有（您选择：{scholarship_pref}）")
        else:
            if scholarship_pref == "很重要":
                explanations.append(f"🎖️ 奖学金：无（您选择：{scholarship_pref}，此项未满足）")
            else:
                explanations.append(f"🎖️ 奖学金：无")
        
        # 9. Go8标识（如果有）
        if bool(school.get("group_of_eight", False)):
            explanations.append("⭐ 澳八校（Go8）成员：是 - 澳洲顶级研究型大学联盟成员")
        
        # 10. 学制和入学时间
        study_length = school.get("study_length_years")
        intakes = school.get("intakes", "")
        
        if study_length:
            explanations.append(f"📅 学制：{study_length} 年")
        if intakes:
            explanations.append(f"📅 入学时间：{intakes}")
        
        return explanations
    except Exception as e:
        # 如果生成解释时出错，返回基本错误信息
        import traceback
        print(f"生成学校解释时出错: {e}")
        traceback.print_exc()
        return [f"⚠️ 生成解释时出错: {str(e)}"]

