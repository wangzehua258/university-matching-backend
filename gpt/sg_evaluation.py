"""
Singapore (SG) parent evaluation logic.

Hard filters and scoring per spec, using university_sg collection only.

Key SG fields:
- rank (int), tuition_usd (int)
- tuition_grant_available (bool), tuition_grant_bond_years (float|None)
- interview_required (bool), essay_or_portfolio_required (bool)
- coop_or_internship_required (bool)
- industry_links_score (int 1–10)
- exchange_opportunities_score (int|None)
- safety_score (float|None)
- intlRate (float), scholarship_available (bool), strengths (list|csv), tags (list|csv)

Input fields:
- academic_band, interests, budget_usd
- tg_willingness: ["愿意","不愿意","视学费而定"]
- interview_portfolio: ["愿意","一般","不愿"]
- orientation: ["产业","研究","均衡"]
- want_double_degree: bool
- want_exchange: bool
- english_confidence: ["高","中","低"]
- bond_acceptance: ["接受","希望避免","无所谓"]
- hard_budget_must_within: bool
- hard_refuse_bond: bool (严格模式拒绝服务期)
- hard_refuse_interview_or_portfolio: bool
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _normalize_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(',') if s.strip()]
    return []


def _rank_band(academic_band: str) -> Tuple[int, int]:
    if academic_band == "3.9+":
        return (1, 50)
    if academic_band == "3.8+":
        return (1, 100)
    if academic_band == "3.6+":
        return (50, 200)
    return (100, 300)


def _score_rank(rank: int, band: Tuple[int, int]) -> float:
    low, high = band
    if rank is None:
        return 0.0
    if low <= rank <= high:
        return 10.0
    dist = 0
    if rank < low:
        dist = low - rank
    elif rank > high:
        dist = rank - high
    steps = (dist + 49) // 50
    return max(0.0, 10.0 - 3.0 * steps)


def _score_interests(selected: List[str], strengths: List[str]) -> float:
    if not selected:
        return 0.0
    hits = 0
    s_lower = [s.lower() for s in strengths]
    for c in selected:
        cc = c.lower()
        if any(cc in s for s in s_lower):
            hits += 1
    return min(20.0, 20.0 * (hits / max(1, len(selected))))


def _score_budget15(tuition_usd: int, budget_usd: int) -> float:
    if budget_usd <= 0:
        return 0.0
    if tuition_usd <= budget_usd:
        return 15.0
    over = (tuition_usd - budget_usd) / budget_usd
    return max(0.0, 15.0 * (1.0 - over))


def _score_orientation(orientation: str, industry_links_score: int | None, coop_required: bool) -> float:
    score = int(industry_links_score or 0)
    score = max(1, min(10, score))
    if orientation == "产业":
        # 0–15 by industry_links +5 if coop required
        base = (score - 1) / 9.0 * 15.0
        bonus = 5.0 if coop_required else 0.0
        return min(20.0, base + bonus)
    if orientation == "研究":
        # fixed 10; +2 if industry_links >=8
        return 12.0 if score >= 8 else 10.0
    # 均衡：0–12 by industry_links +3 if coop required
    base = (score - 1) / 9.0 * 12.0
    bonus = 3.0 if coop_required else 0.0
    return min(15.0, base + bonus)


def _score_tg_bond(pref: str, tg_available: bool, bond_years: float | None) -> float:
    if pref == "接受":
        return 5.0 if tg_available else 3.0
    if pref == "希望避免":
        return 5.0 if (bond_years in (0, None)) else 0.0
    return 3.0


def _score_interview(readiness: str, need_interview: bool) -> float:
    if need_interview:
        return 10.0 if readiness == "愿意" else (6.0 if readiness == "一般" else 0.0)
    return 7.0


def _score_double_degree(need: bool, tags: List[str]) -> float:
    if not need:
        return 5.0
    hit = any(t.lower() in {"double degree", "dsa", "interdisciplinary"} for t in [s.lower() for s in tags])
    return 10.0 if hit else 3.0


def _score_exchange(need: bool, score: int | None) -> float:
    if not need:
        return 2.0
    s = int(score or 0)
    s = max(0, min(10, s))
    return (s / 10.0) * 5.0


def _score_safety(pref: str, safety_score: float | None) -> float:
    if pref == "重要":
        s = float(3.0 if safety_score is None else safety_score)
        s = max(0.0, min(10.0, s))
        return (s / 10.0) * 5.0
    if pref == "一般":
        return 3.0
    return 2.0


def _score_scholarship(pref: str, has_scholarship: bool) -> float:
    if pref == "重要":
        return 10.0 if has_scholarship else 3.0
    if pref == "一般":
        return 7.0 if has_scholarship else 5.0
    return 5.0


def apply_sg_filters_and_score(input_data: Dict[str, Any], sg_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hard_budget = bool(input_data.get("hard_budget_must_within"))
    budget_usd = int(input_data.get("budget_usd", 0) or 0)
    tg_must = bool(input_data.get("tg_must", False))
    refuse_bond = bool(input_data.get("hard_refuse_bond", False))
    refuse_interview_portfolio = bool(input_data.get("hard_refuse_interview_or_portfolio", False))

    filtered: List[Dict[str, Any]] = []
    for d in sg_docs:
        if str(d.get("country")) != "Singapore":
            continue
        if hard_budget and int(d.get("tuition_usd", 0) or 0) > budget_usd:
            continue
        if tg_must and not bool(d.get("tuition_grant_available", False)):
            continue
        if refuse_bond and d.get("tuition_grant_bond_years") not in (0, None, 0.0):
            continue
        if refuse_interview_portfolio and (bool(d.get("interview_required", False)) or bool(d.get("essay_or_portfolio_required", False))):
            continue
        filtered.append(d)

    # Scoring
    band = _rank_band(str(input_data.get("academic_band", "3.6-")))
    interests = _normalize_list(input_data.get("interests", []))
    orientation = str(input_data.get("orientation", "均衡"))
    tg_bond_pref = str(input_data.get("bond_acceptance", "无所谓"))
    interview_pref = str(input_data.get("interview_portfolio", "一般"))
    need_double = bool(input_data.get("want_double_degree", False))
    need_exchange = bool(input_data.get("want_exchange", False))
    safety_pref = str(input_data.get("safety_importance", "一般"))
    scholarship_pref = str(input_data.get("scholarship_importance", "不重要"))

    scored: List[Dict[str, Any]] = []
    for d in filtered:
        strengths = _normalize_list(d.get("strengths", []))
        tags = _normalize_list(d.get("tags", []))
        total = 0.0
        # Q1
        total += _score_rank(int(d.get("rank", 9999) or 9999), band)
        # Q2
        total += _score_interests(interests, strengths)
        # Q3
        total += _score_budget15(int(d.get("tuition_usd", 0) or 0), budget_usd)
        # Q4
        total += _score_orientation(orientation, d.get("industry_links_score"), bool(d.get("coop_or_internship_required", False)))
        # Q5
        total += _score_tg_bond(tg_bond_pref, bool(d.get("tuition_grant_available", False)), d.get("tuition_grant_bond_years"))
        # Q6
        need_int = bool(d.get("interview_required", False) or d.get("essay_or_portfolio_required", False))
        total += _score_interview(interview_pref, need_int)
        # Q7
        total += _score_double_degree(need_double, tags)
        # Q8
        total += _score_exchange(need_exchange, d.get("exchange_opportunities_score"))
        # Q9
        total += _score_safety(safety_pref, d.get("safety_score"))
        # Q10
        total += _score_scholarship(scholarship_pref, bool(d.get("scholarship_available", False)))

        scored.append({
            "id": str(d.get("_id")),
            "name": d.get("name"),
            "score": round(total, 2),
            "rank": int(d.get("rank", 9999) or 9999),
            "tuition_usd": int(d.get("tuition_usd", 0) or 0),
        })

    scored.sort(key=lambda x: (-x["score"], x["tuition_usd"], x["rank"]))
    return scored


