"""
Singapore (SG) parent evaluation logic - 15题版本（2024新规范）

实现完整的硬过滤、评分（100分）、回退策略和解释生成。

评分字段（总分100）：
1. rank (10分) - 学术水平匹配（题3权重调节±20%）
2. strengths (20分) - 专业兴趣匹配
3. tuition_usd (15分) - 预算匹配
4. orientation + industry_links_score + coop (15分) - 培养导向
5. tuition_grant_available + bond_years (5分) - TG/Bond意向
6. interview/portfolio (10分) - 面试/作品集
7. tags (5分) - 双学位机会
8. exchange_opportunities_score (5分) - 交换机会
9. safety_score (5分) - 安全舒适
10. scholarship_available (10分) - 奖学金友好

权重调节字段（不单独计分）：
- reputation_vs_value: 名气优先/均衡/性价比优先 → 调节rank权重±20%
- budget_tolerance: 预算容忍度（0%/10%/20%） → 用于回退放宽
- main_concern: 最担心点 → 用于解释排序和回退优先级

硬过滤（可开关）：
- hard_budget_must_within: 必须≤预算
- tg_must: 必须可申请TG
- hard_refuse_bond: 严格拒绝Bond服务期
- hard_refuse_interview_or_portfolio: 严格拒绝面试/作品集
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
    """专业名称同义词归一化（SG）"""
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


def _score_budget15(tuition_usd: int, budget_usd: int) -> float:
    """Q4: 预算匹配（15分）"""
    if budget_usd <= 0 or tuition_usd is None:
        return 0.0
    if tuition_usd <= budget_usd:
        return 15.0
    over_ratio = (tuition_usd - budget_usd) / budget_usd
    return max(0.0, 15.0 * (1.0 - over_ratio))


def _score_orientation(orientation: str, industry_links_score: Optional[int], coop_required: bool) -> float:
    """Q8: 培养导向（15分）"""
    score = int(industry_links_score or 0)
    score = max(1, min(10, score))
    
    if orientation == "产业":
        # 0-15 by industry_links + 5 if coop required
        base = (score - 1) / 9.0 * 15.0
        bonus = 5.0 if coop_required else 0.0
        return min(15.0, base + bonus)
    elif orientation == "研究":
        # fixed 10-12
        return 12.0 if score >= 8 else 10.0
    else:  # 均衡
        # 0-12 by industry_links + 3 if coop required
        base = (score - 1) / 9.0 * 12.0
        bonus = 3.0 if coop_required else 0.0
        return min(15.0, base + bonus)


def _score_tg_bond(tg_pref: str, tg_available: bool, bond_years: Optional[float]) -> float:
    """Q5: TG/Bond意向（5分）"""
    if tg_pref == "愿意" or tg_pref == "接受":
        return 5.0 if tg_available else 3.0
    if tg_pref == "希望避免" or tg_pref == "不愿意":
        return 5.0 if (bond_years in (0, None, 0.0)) else 0.0
    return 3.0  # 视学费而定/无所谓


def _score_interview_portfolio(readiness: str, need_interview: bool, need_portfolio: bool) -> float:
    """Q9: 面试/作品集（10分）"""
    needs = need_interview or need_portfolio
    if needs:
        return 10.0 if readiness == "愿意" else (6.0 if readiness == "一般" else 0.0)
    return 7.0  # 不需要面试/作品集


def _score_double_degree(need: bool, tags: List[str]) -> float:
    """Q11: 双学位机会（5分，按比例缩放）"""
    if not need:
        return 5.0
    
    # 检查tags中是否有双学位相关
    tag_lower = [t.lower() for t in tags]
    hit = any(keyword in tag for tag in tag_lower for keyword in ["double degree", "dsa", "interdisciplinary", "dual", "joint"])
    
    return 5.0 if hit else 3.0  # 已按5分制缩放


def _score_exchange(need: bool, exchange_score: Optional[int]) -> float:
    """Q12: 交换机会（5分）"""
    if not need:
        return 2.0
    score = int(exchange_score or 0)
    score = max(0, min(10, score))
    return (score / 10.0) * 5.0


def _score_safety(pref: str, safety_score: Optional[float]) -> float:
    """Q13: 安全舒适（5分）"""
    # 缺省时给保守默认3/10
    s = float(3.0 if safety_score is None else safety_score)
    s = max(0.0, min(10.0, s))
    
    if pref == "重要":
        return (s / 10.0) * 5.0
    if pref == "一般":
        return 3.0
    return 2.0


def _score_scholarship(pref: str, has_scholarship: bool) -> float:
    """Q10: 奖学金友好（10分）"""
    if pref == "重要":
        return 10.0 if has_scholarship else 3.0
    if pref == "一般":
        return 7.0 if has_scholarship else 5.0
    return 5.0


def apply_sg_filters_and_score(
    input_data: Dict[str, Any],
    sg_docs: List[Dict[str, Any]],
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
    
    tg_must = bool(input_data.get("tg_must", False))
    refuse_bond = bool(input_data.get("hard_refuse_bond", False))
    refuse_interview = bool(input_data.get("hard_refuse_interview_or_portfolio", False))
    main_concern = str(input_data.get("main_concern", "不确定"))
    
    fallback_info = {"applied": False, "steps": []}
    filtered = []
    
    # 初始硬过滤
    for d in sg_docs:
        if str(d.get("country")) != "Singapore":
            continue
        
        # 预算硬过滤
        if hard_budget and int(d.get("tuition_usd", 0) or 0) > budget_usd:
            continue
        
        # TG必须
        if tg_must and not bool(d.get("tuition_grant_available", False)):
            continue
        
        # Bond严格拒绝
        if refuse_bond and d.get("tuition_grant_bond_years") not in (0, None, 0.0):
            continue
        
        # 面试/作品集严格拒绝
        if refuse_interview and (bool(d.get("interview_required", False)) or bool(d.get("essay_or_portfolio_required", False))):
            continue
        
        filtered.append(d)
    
    # 如果为空且启用回退，逐级放宽
    if len(filtered) == 0 and enable_fallback:
        fallback_info["applied"] = True
        
        # Step 1: 预算微放（按容忍度或默认+10%）
        if hard_budget and main_concern != "超预算":
            effective_tolerance = tolerance_pct if tolerance_pct > 0 else 0.1  # 默认10%
            fallback_info["steps"].append(f"放宽预算至 +{int(effective_tolerance * 100)}%（临时放宽，仅为给出参考备选）")
            budget_expanded = int(budget_usd * (1 + effective_tolerance))
            filtered = [
                d for d in sg_docs
                if str(d.get("country")) == "Singapore"
                and int(d.get("tuition_usd", 0) or 0) <= budget_expanded
            ]
            if tg_must:
                filtered = [d for d in filtered if bool(d.get("tuition_grant_available", False))]
            if refuse_bond:
                filtered = [d for d in filtered if d.get("tuition_grant_bond_years") in (0, None, 0.0)]
            if refuse_interview:
                filtered = [d for d in filtered if not (bool(d.get("interview_required", False)) or bool(d.get("essay_or_portfolio_required", False)))]
        
        # Step 2: 取消面试/作品集严格拒绝（除非最担心=面试）
        if refuse_interview and len(filtered) == 0 and main_concern != "需要面试":
            fallback_info["steps"].append("放宽面试/作品集要求（保留但低分，标注需要面试/作品集）")
            filtered = [
                d for d in sg_docs
                if str(d.get("country")) == "Singapore"
            ]
            if hard_budget:
                effective_tolerance = tolerance_pct if tolerance_pct > 0 else 0.1
                budget_expanded = int(budget_usd * (1 + effective_tolerance))
                filtered = [d for d in filtered if int(d.get("tuition_usd", 0) or 0) <= budget_expanded]
            if tg_must:
                filtered = [d for d in filtered if bool(d.get("tuition_grant_available", False))]
            if refuse_bond:
                filtered = [d for d in filtered if d.get("tuition_grant_bond_years") in (0, None, 0.0)]
        
        # Step 3: 取消Bond严格拒绝
        if refuse_bond and len(filtered) == 0 and main_concern != "TG服务期":
            fallback_info["steps"].append("放宽Bond要求（保留有Bond的TG方案，但标红需签约服务期）")
            filtered = [
                d for d in sg_docs
                if str(d.get("country")) == "Singapore"
            ]
            if hard_budget:
                effective_tolerance = tolerance_pct if tolerance_pct > 0 else 0.1
                budget_expanded = int(budget_usd * (1 + effective_tolerance))
                filtered = [d for d in filtered if int(d.get("tuition_usd", 0) or 0) <= budget_expanded]
            if tg_must:
                filtered = [d for d in filtered if bool(d.get("tuition_grant_available", False))]
        
        # Step 4: 取消TG必须（除非用户明确不愿意TG）
        if tg_must and len(filtered) == 0:
            bond_pref = str(input_data.get("bond_acceptance", "无所谓"))
            if bond_pref != "不愿意":
                fallback_info["steps"].append("放宽TG要求（从'必须'改为'可选'）")
                filtered = [
                    d for d in sg_docs
                    if str(d.get("country")) == "Singapore"
                ]
                if hard_budget:
                    effective_tolerance = tolerance_pct if tolerance_pct > 0 else 0.1
                    budget_expanded = int(budget_usd * (1 + effective_tolerance))
                    filtered = [d for d in filtered if int(d.get("tuition_usd", 0) or 0) <= budget_expanded]
        
        # Step 5: 放宽学术层级（目标带外惩罚减半）
        if len(filtered) == 0:
            fallback_info["steps"].append("放宽学术层级要求（目标带外惩罚减半）")
            filtered = [
                d for d in sg_docs
                if str(d.get("country")) == "Singapore"
            ]
        
        # Step 6: 兜底池（Top 300最低学费5-8所）
        if len(filtered) == 0:
            fallback_info["steps"].append("启用兜底池（Top 300最低学费5-8所）")
            all_sg = [d for d in sg_docs if str(d.get("country")) == "Singapore"]
            if all_sg:
                sorted_by_rank = sorted(all_sg, key=lambda x: int(x.get("rank", 9999) or 9999))
                top300 = [d for d in sorted_by_rank if int(d.get("rank", 9999) or 9999) <= 300]
                if not top300:
                    top300 = sorted_by_rank[:min(300, len(sorted_by_rank))]
                sorted_by_tuition = sorted(top300, key=lambda x: int(x.get("tuition_usd", 999999) or 999999))
                filtered = sorted_by_tuition[:8]
    
    # 最终兜底：如果经过所有回退后仍为空
    if len(filtered) == 0:
        all_sg = [d for d in sg_docs if str(d.get("country")) == "Singapore"]
        if all_sg:
            fallback_info["steps"].append("最终兜底：返回所有可用新加坡学校（按排名）")
            sorted_by_rank = sorted(all_sg, key=lambda x: int(x.get("rank", 9999) or 9999))
            filtered = sorted_by_rank[:10]
    
    # 评分
    academic_band = str(input_data.get("academic_band", "3.6-"))
    target_band = _rank_band(academic_band)
    interests = _normalize_list(input_data.get("interests", []))
    reputation_vs_value = str(input_data.get("reputation_vs_value", "均衡"))
    orientation = str(input_data.get("orientation", "均衡"))
    tg_bond_pref = str(input_data.get("bond_acceptance", "无所谓"))
    interview_pref = str(input_data.get("interview_portfolio", "一般"))
    need_double = bool(input_data.get("want_double_degree", False))
    need_exchange = bool(input_data.get("want_exchange", False))
    safety_pref = str(input_data.get("safety_importance", "一般"))
    scholarship_pref = str(input_data.get("scholarship_importance", "不重要"))
    
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
        tags = _normalize_list(d.get("tags", []))
        total = 0.0
        
        total += _score_rank(int(d.get("rank", 9999) or 9999), target_band, rank_weight)
        total += _score_interests(interests, strengths)
        total += _score_budget15(int(d.get("tuition_usd", 0) or 0), budget_usd)
        total += _score_orientation(orientation, d.get("industry_links_score"), bool(d.get("coop_or_internship_required", False)))
        total += _score_tg_bond(tg_bond_pref, bool(d.get("tuition_grant_available", False)), d.get("tuition_grant_bond_years"))
        total += _score_interview_portfolio(interview_pref, bool(d.get("interview_required", False)), bool(d.get("essay_or_portfolio_required", False)))
        total += _score_double_degree(need_double, tags)
        total += _score_exchange(need_exchange, d.get("exchange_opportunities_score"))
        total += _score_safety(safety_pref, d.get("safety_score"))
        total += _score_scholarship(scholarship_pref, bool(d.get("scholarship_available", False)))
        
        scored.append({
            "id": str(d.get("_id")),
            "name": str(d.get("name", "")),
            "score": round(total, 2),
            "rank": int(d.get("rank", 9999) or 9999),
            "tuition_usd": int(d.get("tuition_usd", 0) or 0),
            "city": str(d.get("city", "")),
            "strengths": strengths,
            "tags": tags,
            "tuition_grant_available": bool(d.get("tuition_grant_available", False)),
            "tuition_grant_bond_years": d.get("tuition_grant_bond_years"),
            "interview_required": bool(d.get("interview_required", False)),
            "essay_or_portfolio_required": bool(d.get("essay_or_portfolio_required", False)),
            "industry_links_score": d.get("industry_links_score"),
            "coop_or_internship_required": bool(d.get("coop_or_internship_required", False)),
            "exchange_opportunities_score": d.get("exchange_opportunities_score"),
            "safety_score": d.get("safety_score"),
            "scholarship_available": bool(d.get("scholarship_available", False)),
        })
    
    # 排序
    scored.sort(key=lambda x: (-x["score"], x["tuition_usd"], x["rank"]))
    return scored, fallback_info


def generate_school_explanations(school: Dict[str, Any], input_data: Dict[str, Any]) -> List[str]:
    """
    为每所新加坡学校生成6-8行可读解释。
    
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
        explanations.append(f"📚 专业匹配：命中您的兴趣 {len(matched)}/{len(interests) if interests else 1} 个方向（{', '.join(matched[:3])}{'...' if len(matched) > 3 else ''}）")
    else:
        explanations.append("📚 专业匹配：部分匹配您选择的专业方向")
    
    # 3. 预算匹配
    budget_usd = int(input_data.get("budget_usd", 0) or 0)
    tuition_usd = int(school.get("tuition_usd", 0) or 0)
    hard_budget = bool(input_data.get("hard_budget_must_within", False))
    budget_tolerance = str(input_data.get("budget_tolerance", "0%"))
    fallback_applied = input_data.get("_fallback_applied", False)
    
    # 计算容忍度百分比
    tolerance_pct = 0.0
    if "10%" in budget_tolerance:
        tolerance_pct = 0.1
    elif "20%" in budget_tolerance:
        tolerance_pct = 0.2
    
    if tuition_usd <= budget_usd:
        budget_desc = f"学费约 ${tuition_usd:,}/年，在您的预算范围内"
    else:
        over_pct = int((tuition_usd - budget_usd) / budget_usd * 100)
        if hard_budget and fallback_applied:
            tolerance_pct_used = tolerance_pct if tolerance_pct > 0 else 0.1  # 默认10%
            budget_desc = f"学费约 ${tuition_usd:,}/年，超出预算约{over_pct}%（已放宽预算至 +{int(tolerance_pct_used * 100)}%，为给出更多备选）"
        else:
            budget_desc = f"学费约 ${tuition_usd:,}/年，超出预算约{over_pct}%"
    
    explanations.append(f"💰 学费：{budget_desc}")
    
    # 4. 培养与实践
    industry_score = school.get("industry_links_score")
    coop_required = bool(school.get("coop_or_internship_required", False))
    orientation = str(input_data.get("orientation", "均衡"))
    
    industry_desc = f"企业合作/实践强度：{industry_score}/10" if industry_score else "企业合作/实践强度：数据缺省"
    coop_desc = "含合作/实习课（Co-op）：有" if coop_required else "含合作/实习课（Co-op）：无"
    
    explanations.append(f"🧑‍💼 培养与实践：{industry_desc}；{coop_desc}")
    
    # 5. TG/Bond
    tg_available = bool(school.get("tuition_grant_available", False))
    bond_years = school.get("tuition_grant_bond_years")
    tg_pref = str(input_data.get("bond_acceptance", "无所谓"))
    
    tg_desc = "可申请TG" if tg_available else "不可申请TG"
    if bond_years and bond_years > 0:
        tg_desc += f"；需服务期约 {bond_years} 年"
    else:
        tg_desc += "；无需服务期"
    
    tg_desc += f"。您的意愿：{tg_pref} → 评分已考虑"
    
    explanations.append(f"🧾 TG/Bond：{tg_desc}")
    
    # 6. 选拔要求
    need_interview = bool(school.get("interview_required", False))
    need_portfolio = bool(school.get("essay_or_portfolio_required", False))
    interview_pref = str(input_data.get("interview_portfolio", "一般"))
    
    needs = need_interview or need_portfolio
    if needs:
        req_desc = "需" + ("面试" if need_interview else "") + ("、" if need_interview and need_portfolio else "") + ("作品集/小论文" if need_portfolio else "")
    else:
        req_desc = "不需"
    
    explanations.append(f"🗣️ 选拔要求：{req_desc} 面试/作品集/小论文；您的意愿：{interview_pref} → 分数说明")
    
    # 7. 双学位/交换
    want_double = bool(input_data.get("want_double_degree", False))
    want_exchange = bool(input_data.get("want_exchange", False))
    tags = _normalize_list(school.get("tags", []))
    exchange_score = school.get("exchange_opportunities_score")
    
    if want_double:
        tag_lower = [t.lower() for t in tags]
        has_double = any(keyword in tag for tag in tag_lower for keyword in ["double degree", "dsa", "interdisciplinary", "dual", "joint"])
        double_desc = "有" if has_double else "无（此项未满足）"
        explanations.append(f"🔁 双学位/跨学科：{double_desc}")
    
    if want_exchange:
        if exchange_score:
            exchange_desc = f"交换机会评分：{exchange_score}/10"
        else:
            exchange_desc = "交换机会：数据缺省"
        explanations.append(f"🔁 交换/海外：{exchange_desc}")
    
    # 8. 安全/舒适
    safety_score = school.get("safety_score")
    safety_pref = str(input_data.get("safety_importance", "一般"))
    
    if safety_score is not None:
        safety_desc = f"安全评分：{safety_score}/10"
    else:
        safety_desc = "安全评分：无公开数据（缺省采用保守估计3/10计分）"
    
    explanations.append(f"🛡️ 安全/舒适：{safety_desc}，与您的重视程度：{safety_pref} → 分数说明")
    
    # 9. 若因放宽策略加入，标注
    if fallback_applied:
        fallback_reason = input_data.get("_fallback_reason", "")
        if fallback_reason:
            explanations.append(f"⚠️ 放宽说明：因 {fallback_reason} 已临时纳入备选")
    
    return explanations
