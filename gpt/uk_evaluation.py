"""
United Kingdom (UK) parent evaluation logic - 16题版本（2024新规范）

实现完整的硬过滤、评分（100分）、回退策略和解释生成。

评分字段：
1. rank (10分) - 学术水平匹配（题3权重调节±20%）
2. strengths (20分) - 专业兴趣匹配
3. tuition_usd (10分) - 预算匹配
4. ucas_route (10分) - UCAS路线匹配
5. placement_year_available (10分) - Placement Year
6. russell_group (10分) - 罗素集团偏好
7. personal_statement_weight (10分) - PS/材料就绪
8. admissions_tests (5分) - 入学测试就绪
9. region_pref (5-7分) - 地域匹配
10. intlRate (5分) - 国际环境

权重调节字段（不单独计分）：
- reputation_vs_value: 名气优先/均衡/性价比优先 → 调节rank权重±20%
- intake_preference: 入学批次偏好 → 小加分≤3（并入UCAS或地域）
- budget_tolerance: 预算容忍度（0%/10%/20%） → 用于回退放宽
- accept_foundation: 是否接受预科路线 → 与foundation_need一起用于过滤
- main_concern: 最担心点 → 用于解释排序和回退优先级

硬过滤（可开关）：
- hard_budget_must_within: 必须≤预算
- oxbridge_must_cover: 必须覆盖Oxbridge/Med
- foundation_need="必须": Foundation必须
- placement_year_pref="必须": Placement Year必须
- region_pref非"不限": 地域必须匹配
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional


def _normalize_list(value: Any) -> List[str]:
    """标准化列表字段"""
    if isinstance(value, list):
        return [str(s).strip().lower() for s in value if str(s).strip()]
    if isinstance(value, str):
        return [s.strip().lower() for s in value.split(',') if s.strip()]
    return []


def _normalize_strengths(strengths: List[str]) -> List[str]:
    """专业名称同义词归一化（UK）"""
    synonym_groups = {
        "cs": ["cs", "computer science", "it", "software", "computing"],
        "ai": ["ai", "artificial intelligence", "machine learning", "ml"],
        "engineering": ["engineering", "eng", "tech"],
        "business": ["business", "commerce", "management", "mba"],
        "economics": ["economics", "econ", "finance"],
        "design": ["design", "art", "creative"],
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


def _normalize_region(region: str) -> str:
    """地域名称归一化"""
    region_map = {
        "london": "london", "伦敦": "london",
        "england": "england", "英格兰": "england",
        "scotland": "scotland", "苏格兰": "scotland",
        "wales": "wales", "威尔士": "wales",
        "northern ireland": "northern ireland", "北爱尔兰": "northern ireland",
    }
    return region_map.get(region.strip().lower(), region.strip().lower())


def _rank_band(academic_band: str) -> Tuple[int, int]:
    """映射学术水平到排名区间"""
    if academic_band == "3.9+":
        return (1, 50)
    if academic_band == "3.8+":
        return (1, 100)
    if academic_band == "3.6+":
        return (50, 200)
    return (100, 300)


def _score_rank(rank: int, target_band: Tuple[int, int], reputation_weight: float = 1.0) -> float:
    """Q1: 学术水平匹配（10分），reputation_weight用于权重调节±20%"""
    if rank is None:
        return 0.0
    low, high = target_band
    base_score = 10.0 if low <= rank <= high else max(0.0, 10.0 - 3.0 * ((abs(rank - (low if rank < low else high)) + 49) // 50))
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
    """Q4: 预算匹配（10分）"""
    if budget_usd <= 0 or tuition_usd is None:
        return 0.0
    if tuition_usd <= budget_usd:
        return 10.0
    over_ratio = (tuition_usd - budget_usd) / budget_usd
    return max(0.0, 10.0 * (1.0 - over_ratio))


def _score_ucas(route: str, ucas_deadline_type: Optional[str], intake_pref: str) -> float:
    """Q6: UCAS路线匹配（10分）+ 入学批次小加分≤3"""
    t = str(ucas_deadline_type or "")
    base_score = 0.0
    
    if route == "Oxbridge/医学类":
        base_score = 10.0 if "Oxbridge/Med(10/15)" in t else 0.0
    elif route == "常规路线":
        base_score = 10.0 if "Main(1/31)" in t else 5.0
    else:  # 不确定
        base_score = 6.0
    
    # 入学批次小加分（≤3分）
    intake_bonus = 0.0
    if intake_pref == "尽快（下6–12个月）" and ("Main(1/31)" in t or "Oxbridge/Med(10/15)" in t):
        intake_bonus = 2.0
    elif intake_pref == "1–2年内" and t:
        intake_bonus = 1.0
    
    return min(10.0, base_score + intake_bonus)


def _score_placement(pref: str, available: bool) -> float:
    """Q7: Placement Year（10分）"""
    if pref == "必须":
        return 10.0 if available else 0.0
    if pref == "加分":
        return 7.0 if available else 4.0
    return 5.0


def _score_russell(pref: str, russell: bool) -> float:
    """Q9: 罗素集团偏好（10分）"""
    if pref == "强":
        return 10.0 if russell else 4.0
    if pref == "中":
        return 8.0 if russell else 6.0
    return 5.0


def _score_ps_readiness(level: str, ps_weight: Optional[int]) -> float:
    """Q10: PS/材料就绪（10分）"""
    weight = max(1, min(10, int(ps_weight or 1)))
    ps_norm = (weight - 1) / 9.0 * 6.0  # 1→0, 10→6
    coef = 1.0 if level == "高" else (0.6 if level == "中" else 0.3)
    return min(10.0, ps_norm * coef + 4.0)


def _score_tests(level: str, admissions_tests: Optional[str]) -> float:
    """Q11: 入学测试就绪（5分）"""
    needs = bool(admissions_tests)
    if needs:
        return 5.0 if level == "高" else (3.0 if level == "中" else 0.0)
    return 3.0


def _score_region(region_pref: str, city: str) -> float:
    """Q12: 地域匹配（5-7分，按比例缩放）"""
    region_norm = _normalize_region(region_pref)
    city_norm = (city or "").strip().lower()
    
    if region_pref == "不限":
        return 7.0
    
    if region_norm == "london":
        return 10.0 * (7.0 / 10.0) if city_norm == "london" else 5.0 * (7.0 / 10.0)  # 缩放到7分制
    
    # 其他地区：包含匹配
    if region_norm in city_norm or city_norm in region_norm:
        return 10.0 * (7.0 / 10.0)  # 缩放到约7分
    return 5.0 * (7.0 / 10.0)  # 约3.5分


def _score_intl_community(pref: str, intl_rate: Optional[float]) -> float:
    """Q13: 国际环境（5分，0.1–0.35线性映射）"""
    rate = float(intl_rate or 0.0)
    
    if pref == "重要":
        clamped = max(0.1, min(0.35, rate))
        return 5.0 * ((clamped - 0.1) / 0.25)  # 0.1→0, 0.35→5
    if pref == "一般":
        return 3.0
    return 2.0


def apply_uk_filters_and_score(
    input_data: Dict[str, Any],
    uk_docs: List[Dict[str, Any]],
    enable_fallback: bool = True
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    应用硬过滤和评分，支持回退策略。
    
    返回: (scored_universities, fallback_info)
    """
    # 提取硬过滤参数
    hard_budget = bool(input_data.get("hard_budget_must_within", False))
    budget_usd = int(input_data.get("budget_usd", 0) or 0)
    budget_tolerance = str(input_data.get("budget_tolerance", "0%"))  # 0%/10%/20%
    tolerance_pct = 0.0
    if "10%" in budget_tolerance:
        tolerance_pct = 0.1
    elif "20%" in budget_tolerance:
        tolerance_pct = 0.2
    
    oxbridge_must = bool(input_data.get("oxbridge_must_cover", False))
    foundation_need = str(input_data.get("foundation_need", "不需要"))
    placement_pref = str(input_data.get("placement_year_pref", "不重要"))
    region_pref = str(input_data.get("region_pref", "不限"))
    has_region_limit = (region_pref != "不限")
    accept_foundation = bool(input_data.get("accept_foundation", True))  # 默认接受
    main_concern = str(input_data.get("main_concern", "不确定"))
    
    fallback_info = {"applied": False, "steps": []}
    filtered = []
    
    # 初始硬过滤
    for d in uk_docs:
        if str(d.get("country")) != "United Kingdom":
            continue
        
        # 预算硬过滤
        if hard_budget and int(d.get("tuition_usd", 0) or 0) > budget_usd:
            continue
        
        # Oxbridge/Med硬过滤
        if oxbridge_must and "Oxbridge/Med(10/15)" not in (d.get("ucas_deadline_type") or ""):
            continue
        
        # Foundation硬过滤
        if foundation_need == "必须" and not bool(d.get("foundation_available", False)):
            continue
        
        # Placement Year硬过滤
        if placement_pref == "必须" and not bool(d.get("placement_year_available", False)):
            continue
        
        # 地域硬过滤
        if has_region_limit:
            city_norm = (d.get("city") or "").strip().lower()
            region_norm = _normalize_region(region_pref)
            if region_norm == "london":
                if city_norm != "london":
                    continue
            else:
                if region_norm not in city_norm and city_norm not in region_norm:
                    continue
        
        filtered.append(d)
    
    # 如果为空且启用回退，逐级放宽
    if len(filtered) == 0 and enable_fallback:
        fallback_info["applied"] = True
        
        # Step 1: 放宽地域（除非最担心=地域）
        if has_region_limit and main_concern != "地区不喜欢":
            fallback_info["steps"].append("放宽地域限制")
            filtered = [d for d in uk_docs if str(d.get("country")) == "United Kingdom"]
            if len(filtered) > 0:
                # 继续后续过滤
                pass
        
        # Step 2: 预算微放（按容忍度或默认+10%）
        if hard_budget and len(filtered) == 0:
            effective_tolerance = tolerance_pct if tolerance_pct > 0 else 0.1  # 默认10%
            fallback_info["steps"].append(f"放宽预算至 +{int(effective_tolerance * 100)}%")
            budget_expanded = int(budget_usd * (1 + effective_tolerance))
            filtered = [
                d for d in uk_docs
                if str(d.get("country")) == "United Kingdom"
                and int(d.get("tuition_usd", 0) or 0) <= budget_expanded
            ]
        
        # Step 3: 弱化Placement必须→加分
        if placement_pref == "必须" and len(filtered) == 0:
            fallback_info["steps"].append("放宽Placement Year要求（从'必须'改为'加分'）")
            filtered = [
                d for d in uk_docs
                if str(d.get("country")) == "United Kingdom"
            ]
            if hard_budget:
                effective_tolerance = tolerance_pct if tolerance_pct > 0 else 0.1
                budget_expanded = int(budget_usd * (1 + effective_tolerance))
                filtered = [d for d in filtered if int(d.get("tuition_usd", 0) or 0) <= budget_expanded]
        
        # Step 4: 取消Oxbridge必须
        if oxbridge_must and len(filtered) == 0:
            fallback_info["steps"].append("放宽Oxbridge/Med要求（不再强制排除）")
            filtered = [
                d for d in uk_docs
                if str(d.get("country")) == "United Kingdom"
            ]
        
        # Step 5: Foundation必须→可选
        if foundation_need == "必须" and len(filtered) == 0:
            fallback_info["steps"].append("放宽Foundation要求（从'必须'改为'可选'）")
            filtered = [
                d for d in uk_docs
                if str(d.get("country")) == "United Kingdom"
            ]
        
        # Step 6: 兜底池（Top 250最低学费6-10所）
        if len(filtered) == 0:
            fallback_info["steps"].append("启用兜底池（Top 250最低学费6-10所）")
            all_uk = [d for d in uk_docs if str(d.get("country")) == "United Kingdom"]
            if all_uk:
                sorted_by_rank = sorted(all_uk, key=lambda x: int(x.get("rank", 9999) or 9999))
                top250 = [d for d in sorted_by_rank if int(d.get("rank", 9999) or 9999) <= 250]
                if not top250:
                    top250 = sorted_by_rank[:250]
                sorted_by_tuition = sorted(top250, key=lambda x: int(x.get("tuition_usd", 999999) or 999999))
                filtered = sorted_by_tuition[:10]
    
    # 最终兜底：如果经过所有回退后仍为空
    if len(filtered) == 0:
        all_uk = [d for d in uk_docs if str(d.get("country")) == "United Kingdom"]
        if all_uk:
            fallback_info["steps"].append("最终兜底：返回所有可用英国学校（按排名）")
            sorted_by_rank = sorted(all_uk, key=lambda x: int(x.get("rank", 9999) or 9999))
            filtered = sorted_by_rank[:10]
    
    # 评分
    academic_band = str(input_data.get("academic_band", "3.6-"))
    target_band = _rank_band(academic_band)
    interests = _normalize_list(input_data.get("interests", []))
    reputation_vs_value = str(input_data.get("reputation_vs_value", "均衡"))
    ucas_route = str(input_data.get("ucas_route", "不确定"))
    russell_pref = str(input_data.get("russell_pref", "中"))
    prep_level = str(input_data.get("prep_level", "中"))
    intl_pref = str(input_data.get("intl_env_importance", "一般"))
    intake_pref = str(input_data.get("intake_preference", "不确定"))
    
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
        total += _score_ucas(ucas_route, d.get("ucas_deadline_type"), intake_pref)
        total += _score_placement(placement_pref, bool(d.get("placement_year_available", False)))
        total += _score_russell(russell_pref, bool(d.get("russell_group", False)))
        total += _score_ps_readiness(prep_level, d.get("personal_statement_weight"))
        total += _score_tests(prep_level, d.get("admissions_tests"))
        total += _score_region(region_pref, str(d.get("city") or ""))
        total += _score_intl_community(intl_pref, d.get("intlRate"))
        
        scored.append({
            "id": str(d.get("_id")),
            "name": str(d.get("name", "")),
            "score": round(total, 2),
            "rank": int(d.get("rank", 9999) or 9999),
            "tuition_usd": int(d.get("tuition_usd", 0) or 0),
            "city": str(d.get("city", "")),
            "strengths": strengths,
            "placement_year_available": bool(d.get("placement_year_available", False)),
            "russell_group": bool(d.get("russell_group", False)),
            "personal_statement_weight": d.get("personal_statement_weight"),
            "admissions_tests": d.get("admissions_tests"),
            "ucas_deadline_type": d.get("ucas_deadline_type", ""),
            "foundation_available": bool(d.get("foundation_available", False)),
            "intlRate": d.get("intlRate"),
        })
    
    # 排序
    scored.sort(key=lambda x: (-x["score"], x["tuition_usd"], x["rank"]))
    return scored, fallback_info


def generate_school_explanations(school: Dict[str, Any], input_data: Dict[str, Any]) -> List[str]:
    """
    为每所英国学校生成6-8行可读解释。
    
    返回格式：["🎓 学术层级：...", "📚 专业匹配：...", ...]
    """
    explanations = []
    
    # 1. 学术层级匹配
    academic_band = str(input_data.get("academic_band", "3.6-"))
    rank = int(school.get("rank", 9999) or 9999)
    band_map = {"3.9+": "1-50", "3.8+": "1-100", "3.6+": "50-200", "3.6-": "100-300"}
    target_range = band_map.get(academic_band, "100-300")
    
    if rank <= 50:
        level_desc = "与您的目标层级（Top 50）匹配"
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
    budget_tolerance = str(input_data.get("budget_tolerance", "0%"))
    
    if tuition_usd <= budget_usd:
        budget_desc = f"学费 £{tuition_usd:,}/年，在您的预算范围内"
    else:
        over_pct = int((tuition_usd - budget_usd) / budget_usd * 100)
        if hard_budget or "10%" in budget_tolerance or "20%" in budget_tolerance:
            budget_desc = f"学费 £{tuition_usd:,}/年，超出预算约{over_pct}%（因放宽策略保留）"
        else:
            budget_desc = f"学费 £{tuition_usd:,}/年，超出预算约{over_pct}%"
    
    explanations.append(f"💰 学费：{budget_desc}")
    
    # 4. UCAS路线
    ucas_route = str(input_data.get("ucas_route", "不确定"))
    ucas_type = str(school.get("ucas_deadline_type", ""))
    
    if ucas_route == "Oxbridge/医学类":
        if "Oxbridge/Med(10/15)" in ucas_type:
            explanations.append("📋 UCAS路线：Oxbridge/医学类（10/15截止） - 符合您的选择 ✓")
        else:
            explanations.append("📋 UCAS路线：常规路线（该校非Oxbridge/Med）")
    elif ucas_route == "常规路线":
        if "Main(1/31)" in ucas_type:
            explanations.append("📋 UCAS路线：常规路线（1/31截止） - 符合您的选择 ✓")
        else:
            explanations.append(f"📋 UCAS路线：{ucas_type or '未明确'}（与常规路线部分匹配）")
    else:
        explanations.append(f"📋 UCAS路线：{ucas_type or '未明确'}（您选择：不确定）")
    
    # 5. Placement Year
    placement_avail = bool(school.get("placement_year_available", False))
    placement_pref = str(input_data.get("placement_year_pref", "不重要"))
    
    if placement_avail:
        explanations.append(f"🧑‍💼 Placement Year：有（第3年企业实习，学制通常多1年）")
    else:
        if placement_pref == "必须":
            explanations.append(f"🧑‍💼 Placement Year：无（因放宽策略保留，分值较低）")
        else:
            explanations.append(f"🧑‍💼 Placement Year：无（您选择：{placement_pref}）")
    
    # 6. 罗素集团
    russell = bool(school.get("russell_group", False))
    russell_pref = str(input_data.get("russell_pref", "中"))
    
    if russell:
        explanations.append(f"🏛️ 罗素集团：是（英国名校联盟成员，与您的偏好：{russell_pref}匹配）")
    else:
        explanations.append(f"🏛️ 罗素集团：否（与您的偏好：{russell_pref}，此项未满足）")
    
    # 7. 材料就绪
    ps_weight = school.get("personal_statement_weight")
    admissions_tests = school.get("admissions_tests")
    prep_level = str(input_data.get("prep_level", "中"))
    
    test_info = ""
    if admissions_tests:
        test_info = f"需入学测试（{admissions_tests}）；"
    else:
        test_info = "无需入学测试；"
    
    explanations.append(f"📄 材料就绪：{test_info}您的准备度：{prep_level} → 评分已考虑")
    
    # 8. 地域/环境
    city = str(school.get("city", ""))
    region_pref = str(input_data.get("region_pref", "不限"))
    intl_rate = school.get("intlRate")
    intl_pref = str(input_data.get("intl_env_importance", "一般"))
    
    region_match = ""
    if region_pref == "不限":
        region_match = f"位于 {city}（您选择：不限）"
    else:
        city_norm = city.lower()
        region_norm = _normalize_region(region_pref)
        if region_norm == "london" and city_norm == "london":
            region_match = f"位于 {city}（与您的偏好：命中）"
        elif region_norm in city_norm or city_norm in region_norm:
            region_match = f"位于 {city}（与您的偏好：部分匹配）"
        else:
            region_match = f"位于 {city}（与您的偏好：未命中）"
    
    intl_info = f"国际生比例约 {int(intl_rate * 100) if intl_rate else 0}%"
    explanations.append(f"📍 地域/环境：{region_match}；{intl_info}（与您'环境{intl_pref}'偏好匹配度说明）")
    
    # 9. Foundation（如果有）
    foundation_avail = bool(school.get("foundation_available", False))
    foundation_need = str(input_data.get("foundation_need", "不需要"))
    
    if foundation_need != "不需要":
        if foundation_avail:
            explanations.append("📚 Foundation/国际大一：有（成绩不够可先读预科再衔接）")
        else:
            explanations.append("📚 Foundation/国际大一：无（此校无预科/国际大一，因放宽策略保留）")
    
    # 10. 若因放宽策略加入，标注
    fallback_applied = input_data.get("_fallback_applied", False)
    fallback_reason = input_data.get("_fallback_reason", "")
    if fallback_applied and fallback_reason:
        explanations.append(f"⚠️ 放宽说明：{fallback_reason}")
    
    return explanations
