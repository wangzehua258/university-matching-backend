"""
United Kingdom (UK) parent evaluation logic.

Implements hard filters and 10-question scoring EXACTLY as specified, using
the university_uk collection only.

Key UK fields used:
- country == "United Kingdom"
- rank (int), tuition_usd (int), city (str)
- ucas_deadline_type (str)  → e.g., "Oxbridge/Med(10/15)" or "Main(1/31)"
- foundation_available (bool), placement_year_available (bool)
- russell_group (bool)
- personal_statement_weight (int 1–10)
- admissions_tests (str)    → presence => school requires tests
- intlRate (float 0–1)
- strengths (list[str]|csv)

Input answer fields (minimal expected):
- academic_band: "3.9+"/"3.8+"/"3.6+"/"3.6-"
- interests: list[str]
- budget_usd: int
- ucas_route: ["Oxbridge/医学类", "常规路线", "不确定"]
- foundation_need: ["必须", "可选", "不需要"]
- placement_year_pref: ["必须", "加分", "不重要"]
- russell_pref: ["强", "中", "弱"]
- prep_level: ["高", "中", "低"]  # PS/学术拓展/入学考试总体就绪
- region_pref: one of ["London","England","Scotland","Wales","Northern Ireland","不限"]
- intl_env_importance: ["重要", "一般", "不重要"]
- hard_budget_must_within: bool
- oxbridge_must_cover: Optional[bool]  # 若需要强制覆盖 Oxbridge/Med 路线

Scoring total 100, tie-break: lower tuition_usd; then higher rank.
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
    # 带内 10；带外每超过50名扣3分
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
    s_lower = [s.lower() for s in strengths]
    hits = 0
    for c in selected:
        cc = c.lower()
        if any(cc in s for s in s_lower):
            hits += 1
    return min(20.0, 20.0 * (hits / max(1, len(selected))))


def _score_budget(tuition_usd: int, budget_usd: int) -> float:
    if budget_usd <= 0:
        return 0.0
    if tuition_usd <= budget_usd:
        return 10.0
    over = (tuition_usd - budget_usd) / budget_usd
    return max(0.0, 10.0 * (1.0 - over))


def _score_ucas(route: str, ucas_deadline_type: str) -> float:
    # 选 Oxbridge/医学类且学校类型匹配 →10，否则0
    # 选 常规路线 且 Main(1/31) →10，其他→5；不确定→6
    t = ucas_deadline_type or ""
    if route == "Oxbridge/医学类":
        return 10.0 if "Oxbridge/Med(10/15)" in t else 0.0
    if route == "常规路线":
        return 10.0 if "Main(1/31)" in t else 5.0
    return 6.0


def _score_placement(pref: str, available: bool) -> float:
    if pref == "必须":
        return 10.0 if available else 0.0
    if pref == "加分":
        return 7.0 if available else 4.0
    return 5.0


def _score_russell(pref: str, russell: bool) -> float:
    if pref == "强":
        return 10.0 if russell else 4.0
    if pref == "中":
        return 8.0 if russell else 6.0
    return 5.0


def _score_ps_readiness(level: str, ps_weight: int | None) -> float:
    # 分 = (PS权重归一 0–6) × 系数 + 4；系数 高1.0/中0.6/低0.3；封顶10
    weight = max(1, min(10, int(ps_weight or 1)))
    ps_norm = (weight - 1) / 9.0 * 6.0  # 1→0, 10→6
    coef = 1.0 if level == "高" else (0.6 if level == "中" else 0.3)
    return min(10.0, ps_norm * coef + 4.0)


def _score_tests(level: str, admissions_tests: str) -> float:
    # 学校要求测试：高5/中3/低0；无要求：3
    needs = bool(admissions_tests)
    if needs:
        return 5.0 if level == "高" else (3.0 if level == "中" else 0.0)
    return 3.0


def _score_region(region_pref: str, city: str) -> float:
    if region_pref == "不限":
        return 7.0
    # 简单归类：London 命中 London；其他按 city 包含判断
    if region_pref == "London":
        return 10.0 if (city or "").lower() == "london" else 5.0
    return 10.0 if region_pref.lower() in (city or "").lower() else 5.0


def _linear_map(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    if in_max == in_min:
        return out_min
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def _score_intl(pref: str, rate: float | None) -> float:
    if pref == "重要":
        r = max(0.1, min(0.35, float(rate or 0.0)))
        return _linear_map(r, 0.1, 0.35, 0.0, 5.0)
    if pref == "一般":
        return 3.0
    return 2.0


def apply_uk_filters_and_score(input_data: Dict[str, Any], uk_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply UK hard filters and score; return sorted list with id/score/rank/tuition_usd.
    """
    hard_budget = bool(input_data.get("hard_budget_must_within"))
    budget_usd = int(input_data.get("budget_usd", 0) or 0)
    oxbridge_must = bool(input_data.get("oxbridge_must_cover", False))
    foundation_need = str(input_data.get("foundation_need", "不需要"))
    placement_pref = str(input_data.get("placement_year_pref", "不重要"))
    region_pref = str(input_data.get("region_pref", "不限"))

    filtered: List[Dict[str, Any]] = []
    for d in uk_docs:
        if str(d.get("country")) != "United Kingdom":
            continue
        if hard_budget and int(d.get("tuition_usd", 0) or 0) > budget_usd:
            continue
        # Oxbridge/Med must cover
        if oxbridge_must and "Oxbridge/Med(10/15)" not in (d.get("ucas_deadline_type") or ""):
            continue
        # Foundation must
        if foundation_need == "必须" and not bool(d.get("foundation_available", False)):
            continue
        # Placement year must
        if placement_pref == "必须" and not bool(d.get("placement_year_available", False)):
            continue
        # Region must (basic contains logic; London exact)
        if region_pref != "不限":
            city = (d.get("city") or "").lower()
            if region_pref == "London":
                if city != "london":
                    continue
            else:
                if region_pref.lower() not in city:
                    continue
        filtered.append(d)

    # scoring
    band = _rank_band(str(input_data.get("academic_band", "3.6-")))
    interests = _normalize_list(input_data.get("interests", []))
    ucas_route = str(input_data.get("ucas_route", "不确定"))
    russell_pref = str(input_data.get("russell_pref", "中"))
    prep_level = str(input_data.get("prep_level", "中"))
    intl_pref = str(input_data.get("intl_env_importance", "一般"))

    scored: List[Dict[str, Any]] = []
    for d in filtered:
        strengths = _normalize_list(d.get("strengths", []))
        total = 0.0
        total += _score_rank(int(d.get("rank", 9999) or 9999), band)
        total += _score_interests(interests, strengths)
        total += _score_budget(int(d.get("tuition_usd", 0) or 0), budget_usd)
        total += _score_ucas(ucas_route, str(d.get("ucas_deadline_type") or ""))
        total += _score_placement(placement_pref, bool(d.get("placement_year_available", False)))
        total += _score_russell(russell_pref, bool(d.get("russell_group", False)))
        total += _score_ps_readiness(prep_level, d.get("personal_statement_weight"))
        total += _score_tests(prep_level, str(d.get("admissions_tests") or ""))
        total += _score_region(region_pref, str(d.get("city") or ""))
        total += _score_intl(intl_pref, d.get("intlRate"))

        scored.append({
            "id": str(d.get("_id")),
            "name": d.get("name"),
            "score": round(total, 2),
            "rank": int(d.get("rank", 9999) or 9999),
            "tuition_usd": int(d.get("tuition_usd", 0) or 0),
        })

    scored.sort(key=lambda x: (-x["score"], x["tuition_usd"], x["rank"]))
    return scored


