"""
Australia (AU) parent evaluation logic.

This module implements BOTH the hard filters and the 10-question scoring rubric
EXACTLY as specified, against the university_au collection only.

Key AU collection fields used (from data model):
- name (str)                     → university name
- country (str)                  → should be "Australia"
- city (str)                     → e.g., Sydney/Melbourne/...
- rank (int)                     → unified/global rank used by rubric
- tuition_usd (int)              → yearly tuition normalized to USD
- work_integrated_learning (bool)
- placement_rate (float|None)    → 0-1 (if None, treated as 0)
- requires_english_test (bool)
- group_of_eight (bool)
- post_study_visa_years (float)  → 2-4 range
- strengths (list[str]|csv)      → normalized to list by caller
- intlRate (float)               → 0-1
- scholarship_available (bool)

Input answer fields (expected minimal structure from frontend):
- target_country: "Australia"
- academic_band: one of ["3.9+", "3.8+", "3.6+", "3.6-"]
- interests: list[str]           → selected areas (match against strengths)
- budget_usd: int                → parent yearly budget in USD
- wil_preference: ["必须", "加分", "不重要"]
- go8_preference: ["强", "一般", "无"]
- psw_importance: ["非常在意", "一般", "不在意"]
- english_readiness: ["已达标", "3个月内可达", "需更长"]
- city_preferences: list[str] or ["不限"]
- intl_community_importance: ["重要", "一般", "不重要"]
- hard_english_required_exclude: bool (是否开启“英语必须排除”开关)
- hard_budget_must_within: bool (“必须 ≤ 预算”开关)

Scoring total: 100. Tie-break: lower tuition_usd first, then higher rank.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _rank_band_for_academic(band: str) -> Tuple[int, int]:
    """Map academic band to rank band inclusive.
    3.9+ → 1–60; 3.8+ → 1–100; 3.6+ → 60–200; 3.6- → 100–300
    """
    if band == "3.9+":
        return (1, 60)
    if band == "3.8+":
        return (1, 100)
    if band == "3.6+":
        return (60, 200)
    # default to 3.6-
    return (100, 300)


def _score_rank(rank: int, target_band: Tuple[int, int]) -> float:
    """Q1: 10 points if inside band; outside band subtract 5 per 50 beyond to min 0.
    """
    low, high = target_band
    if rank is None:
        return 0.0
    if low <= rank <= high:
        return 10.0
    # distance from nearest band edge
    dist = 0
    if rank < low:
        dist = low - rank
    elif rank > high:
        dist = rank - high
    # each 50 → -5 points
    steps = (dist + 49) // 50
    return max(0.0, 10.0 - 5.0 * steps)


def _normalize_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(',') if s.strip()]
    return []


def _score_interests(selected: List[str], strengths: List[str]) -> float:
    """Q2: (hits / selected) * 20, cap 20. Allow substring match."""
    if not selected:
        return 0.0
    hits = 0
    strengths_l = [s.lower() for s in strengths]
    for choice in selected:
        c = choice.lower()
        if any(c in s for s in strengths_l):
            hits += 1
    return min(20.0, 20.0 * (hits / max(1, len(selected))))


def _score_budget(tuition_usd: int, budget_usd: int) -> float:
    """Q3: ≤ budget → 10, else linear down to 0 by over ratio."""
    if budget_usd <= 0 or tuition_usd is None:
        return 0.0
    if tuition_usd <= budget_usd:
        return 10.0
    over = (tuition_usd - budget_usd) / budget_usd
    return max(0.0, 10.0 * (1.0 - over))


def _score_wil(wil_pref: str, wil: bool, placement_rate: float | None) -> float:
    """Q4 scoring by preference and fields.
    必须: WIL True → 7 + rate*3; 否则由过滤淘汰。
    加分: WIL True → 5 + rate*2; 不重要: 3 固定。
    """
    rate = float(placement_rate or 0.0)
    if wil_pref == "必须":
        return 7.0 + rate * 3.0 if wil else 0.0
    if wil_pref == "加分":
        return (5.0 + rate * 2.0) if wil else 4.0  # 给非WIL一点中性分
    return 3.0


def _score_go8(pref: str, go8: bool) -> float:
    """Q5 Go8 preference mapping."""
    if pref == "强":
        return 10.0 if go8 else 4.0
    if pref == "一般":
        return 6.0 if go8 else 5.0
    return 5.0


def _score_city(pref_cities: List[str], city: str) -> float:
    """Q6 city matching.
    命中→10；否则5；不限→7。
    """
    if not pref_cities or "不限" in pref_cities:
        return 7.0
    return 10.0 if (city or "").strip() in pref_cities else 5.0


def _score_psw(importance: str, psw_years: float | None) -> float:
    """Q7 PSW importance curve.
    非常在意：10 × ((PSW−2)/(4−2))；一般：6；不在意：4
    """
    if importance == "非常在意":
        psw = float(psw_years or 2.0)
        psw = max(2.0, min(4.0, psw))
        return 10.0 * ((psw - 2.0) / 2.0)
    if importance == "一般":
        return 6.0
    return 4.0


def _score_english(readiness: str, requires_english_test: bool) -> float:
    """Q8 English readiness vs requirement.
    要求英语：已达标5/3个月内3/需更长0；不要求：4
    """
    if requires_english_test:
        if readiness == "已达标":
            return 5.0
        if readiness == "3个月内可达":
            return 3.0
        return 0.0
    return 4.0


def _linear_map(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    if in_max == in_min:
        return out_min
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def _score_intl_community(pref: str, intl_rate: float | None) -> float:
    """Q9 intl community weight.
    重要：intlRate 在 0.1–0.4 映射到 0–5；一般：3；不重要：2
    """
    rate = float(intl_rate or 0.0)
    if pref == "重要":
        clamped = max(0.1, min(0.4, rate))
        return _linear_map(clamped, 0.1, 0.4, 0.0, 5.0)
    if pref == "一般":
        return 3.0
    return 2.0


def _score_scholarship(pref: str, has_scholarship: bool) -> float:
    """Q10 scholarship friendliness."""
    if pref == "重要":
        return 10.0 if has_scholarship else 3.0
    if pref == "一般":
        return 7.0 if has_scholarship else 5.0
    return 5.0


def apply_au_filters_and_score(input_data: Dict[str, Any], au_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply AU hard filters then score remaining universities.

    Returns a list of dicts with fields: id, score, and any additional metadata
    useful for frontend (e.g., tuition_usd, rank, name). Sorting is applied
    by score desc, then tuition_usd asc, then rank asc.
    """
    # 1) Hard filters
    hard_budget = bool(input_data.get("hard_budget_must_within"))
    budget_usd = int(input_data.get("budget_usd", 0) or 0)
    wil_pref = str(input_data.get("wil_preference", "不重要"))
    must_wil = (wil_pref == "必须")
    pref_cities = _normalize_list(input_data.get("city_preferences", []))
    english_exclude = bool(input_data.get("hard_english_required_exclude", False))

    filtered: List[Dict[str, Any]] = []
    for d in au_docs:
        if str(d.get("country")) != "Australia":
            continue
        # Budget must within
        if hard_budget and int(d.get("tuition_usd", 0) or 0) > budget_usd:
            continue
        # WIL must
        if must_wil and not bool(d.get("work_integrated_learning", False)):
            continue
        # City must
        if pref_cities and "不限" not in pref_cities:
            if (d.get("city") or "").strip() not in pref_cities:
                continue
        # English exclude
        if english_exclude and bool(d.get("requires_english_test", False)):
            continue
        filtered.append(d)

    # 2) Scoring
    academic_band = str(input_data.get("academic_band", "3.6-") )
    target_band = _rank_band_for_academic(academic_band)
    interests = _normalize_list(input_data.get("interests", []))
    go8_pref = str(input_data.get("go8_preference", "无"))
    psw_importance = str(input_data.get("psw_importance", "一般"))
    english_ready = str(input_data.get("english_readiness", "3个月内可达"))
    intl_pref = str(input_data.get("intl_community_importance", "一般"))
    scholarship_pref = str(input_data.get("scholarship_importance", "不重要"))

    scored: List[Dict[str, Any]] = []
    for d in filtered:
        strengths = _normalize_list(d.get("strengths", []))
        total = 0.0
        total += _score_rank(int(d.get("rank", 9999) or 9999), target_band)
        total += _score_interests(interests, strengths)
        total += _score_budget(int(d.get("tuition_usd", 0) or 0), budget_usd)
        total += _score_wil(wil_pref, bool(d.get("work_integrated_learning", False)), d.get("placement_rate"))
        total += _score_go8(go8_pref, bool(d.get("group_of_eight", False)))
        total += _score_city(pref_cities, str(d.get("city") or ""))
        total += _score_psw(psw_importance, d.get("post_study_visa_years"))
        total += _score_english(english_ready, bool(d.get("requires_english_test", False)))
        total += _score_intl_community(intl_pref, d.get("intlRate"))
        total += _score_scholarship(scholarship_pref, bool(d.get("scholarship_available", False)))

        scored.append({
            "id": str(d.get("_id")),
            "name": d.get("name"),
            "score": round(total, 2),
            "rank": int(d.get("rank", 9999) or 9999),
            "tuition_usd": int(d.get("tuition_usd", 0) or 0),
        })

    # Sort: score desc, tuition_usd asc, rank asc
    scored.sort(key=lambda x: (-x["score"], x["tuition_usd"], x["rank"]))
    return scored


