from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel

from models.university import University, UniversityResponse
from db.mongo import get_db

router = APIRouter()
def _parse_list_or_csv(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [s.strip() for s in value.split(',') if s.strip()]
    return []

@router.get("/international/au")
async def list_international_au(page: int = 1, page_size: int = 50):
    db = get_db()
    cursor = db.university_au.find({}).skip((page-1)*page_size).limit(page_size).sort("rank", 1)
    docs = await cursor.to_list(length=page_size)
    for d in docs:
        d["_id"] = str(d["_id"])  # stringify id
        d["strengths"] = _parse_list_or_csv(d.get("strengths", []))
        d["tags"] = _parse_list_or_csv(d.get("tags", []))
    return docs

@router.get("/international/au/{id}")
async def get_international_au(id: str):
    from bson import ObjectId
    db = get_db()
    doc = await db.university_au.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="未找到大学")
    doc["_id"] = str(doc["_id"])  # stringify id
    doc["strengths"] = _parse_list_or_csv(doc.get("strengths", []))
    doc["tags"] = _parse_list_or_csv(doc.get("tags", []))
    return doc

@router.get("/international/uk")
async def list_international_uk(page: int = 1, page_size: int = 50):
    db = get_db()
    cursor = db.university_uk.find({}).skip((page-1)*page_size).limit(page_size).sort("rank", 1)
    docs = await cursor.to_list(length=page_size)
    for d in docs:
        d["_id"] = str(d["_id"])  # stringify id
        d["strengths"] = _parse_list_or_csv(d.get("strengths", []))
        d["tags"] = _parse_list_or_csv(d.get("tags", []))
    return docs

@router.get("/international/uk/{id}")
async def get_international_uk(id: str):
    from bson import ObjectId
    db = get_db()
    doc = await db.university_uk.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="未找到大学")
    doc["_id"] = str(doc["_id"])  # stringify id
    doc["strengths"] = _parse_list_or_csv(doc.get("strengths", []))
    doc["tags"] = _parse_list_or_csv(doc.get("tags", []))
    return doc

@router.get("/international/sg")
async def list_international_sg(page: int = 1, page_size: int = 50):
    db = get_db()
    cursor = db.university_sg.find({}).skip((page-1)*page_size).limit(page_size).sort("rank", 1)
    docs = await cursor.to_list(length=page_size)
    for d in docs:
        d["_id"] = str(d["_id"])  # stringify id
        d["strengths"] = _parse_list_or_csv(d.get("strengths", []))
        d["tags"] = _parse_list_or_csv(d.get("tags", []))
    return docs

@router.get("/international/sg/{id}")
async def get_international_sg(id: str):
    from bson import ObjectId
    db = get_db()
    doc = await db.university_sg.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="未找到大学")
    doc["_id"] = str(doc["_id"])  # stringify id
    doc["strengths"] = _parse_list_or_csv(doc.get("strengths", []))
    doc["tags"] = _parse_list_or_csv(doc.get("tags", []))
    return doc

class PaginatedUniversityResponse(BaseModel):
    """分页大学响应模型"""
    universities: List[UniversityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

# --- International collections compatibility layer (AU/UK/SG) ---
INTERNATIONAL_COUNTRIES = {"Australia", "United Kingdom", "Singapore"}

def _parse_list_or_csv(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [s.strip() for s in value.split(',') if s.strip()]
    return []

async def _query_international(country: str, page: int, page_size: int, filter_conditions: dict):
    """Query AU/UK/SG collections and map to UniversityResponse compatible dicts."""
    db = get_db()
    coll_name = {
        "Australia": "university_au",
        "United Kingdom": "university_uk",
        "Singapore": "university_sg",
    }[country]
    # Remove filters not applicable in intl collections except rank and strength
    intl_filter = {}
    if "rank" in filter_conditions:
        intl_filter["rank"] = filter_conditions["rank"]
    if "strengths" in filter_conditions:
        intl_filter["strengths"] = filter_conditions["strengths"]
    cursor = getattr(db, coll_name).find(intl_filter).skip((page - 1) * page_size).limit(page_size).sort("rank", 1)
    docs = await cursor.to_list(length=page_size)
    results = []
    for d in docs:
        strengths = _parse_list_or_csv(d.get("strengths", []))
        results.append({
            "id": str(d.get("_id")),
            "name": d.get("name"),
            "country": d.get("country", country),
            "state": d.get("city", ""),
            "rank": d.get("rank", 9999),
            "tuition": int(d.get("tuition_usd", 0) or 0),
            "intl_rate": float(d.get("intlRate", 0) or 0.0),
            # reuse "type" to carry currency to avoid breaking UI
            "type": d.get("currency", "public"),
            "strengths": strengths,
            # reuse gpt_summary slot to show website as placeholder
            "gpt_summary": d.get("website", ""),
            "logo_url": None,
        })
    # Count total (fallback if not supported)
    try:
        total = await getattr(db, coll_name).count_documents(intl_filter)
    except Exception:
        total = len(results)
    return results, total

@router.get("/", response_model=List[UniversityResponse])
async def get_universities(
    country: Optional[str] = Query(None, description="国家筛选"),
    rank_min: Optional[int] = Query(None, description="最低排名"),
    rank_max: Optional[int] = Query(None, description="最高排名"),
    tuition_max: Optional[int] = Query(None, description="最高学费"),
    type: Optional[str] = Query(None, description="学校类型"),
    strength: Optional[str] = Query(None, description="优势专业"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, description="页码，从1开始", ge=1),
    page_size: int = Query(9, description="每页显示数量，默认9所")  # 改为9，支持3×3网格
):
    """获取大学列表，支持多种筛选条件和分页"""
    db = get_db()
    
    # 计算skip值
    skip = (page - 1) * page_size
    
    # 构建查询条件
    filter_conditions = {}
    
    if country:
        filter_conditions["country"] = country
    
    if rank_min is not None or rank_max is not None:
        rank_filter = {}
        if rank_min is not None:
            rank_filter["$gte"] = rank_min
        if rank_max is not None:
            rank_filter["$lte"] = rank_max
        filter_conditions["rank"] = rank_filter
    
    if tuition_max:
        filter_conditions["tuition"] = {"$lte": tuition_max}
    
    if type:
        filter_conditions["type"] = type
    
    if strength:
        filter_conditions["strengths"] = {"$in": [strength]}
    
    if search:
        filter_conditions["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"strengths": {"$regex": search, "$options": "i"}}
        ]
    # International collections handling
    if country in INTERNATIONAL_COUNTRIES:
        intl_results, _ = await _query_international(country, page, page_size, filter_conditions)
        return [UniversityResponse(**r) for r in intl_results]
    
    # 执行分页查询
    try:
        cursor = db.universities.find(filter_conditions).skip(skip).limit(page_size).sort("rank", 1)
        universities = await cursor.to_list(length=page_size)
    except Exception as e:
        print(f"查询失败: {e}")
        universities = []
    
    # 转换为响应格式 - 保持向后兼容，返回数组
    result = []
    for uni in universities:
        result.append(UniversityResponse(
            id=str(uni["_id"]),
            name=uni["name"],
            country=uni["country"],
            state=uni["state"],
            rank=uni["rank"],
            tuition=uni["tuition"],
            intl_rate=uni["intlRate"],
            type=uni["type"],
            strengths=uni["strengths"],
            gpt_summary=uni["gptSummary"],
            logo_url=uni.get("logoUrl")
        ))
    
    return result

@router.get("/paginated", response_model=PaginatedUniversityResponse)
async def get_universities_paginated(
    country: Optional[str] = Query(None, description="国家筛选"),
    rank_min: Optional[int] = Query(None, description="最低排名"),
    rank_max: Optional[int] = Query(None, description="最高排名"),
    tuition_max: Optional[int] = Query(None, description="最高学费"),
    type: Optional[str] = Query(None, description="学校类型"),
    strength: Optional[str] = Query(None, description="优势专业"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, description="页码，从1开始", ge=1),
    page_size: int = Query(9, description="每页显示数量，默认9所")
):
    """获取大学列表（分页版本），支持多种筛选条件和分页信息"""
    db = get_db()
    
    # 计算skip值
    skip = (page - 1) * page_size
    
    # 构建查询条件
    filter_conditions = {}
    
    if country:
        filter_conditions["country"] = country
    
    if rank_min is not None or rank_max is not None:
        rank_filter = {}
        if rank_min is not None:
            rank_filter["$gte"] = rank_min
        if rank_max is not None:
            rank_filter["$lte"] = rank_max
        filter_conditions["rank"] = rank_filter
    
    if tuition_max:
        filter_conditions["tuition"] = {"$lte": tuition_max}
    
    if type:
        filter_conditions["type"] = type
    
    if strength:
        filter_conditions["strengths"] = {"$in": [strength]}
    
    if search:
        filter_conditions["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"strengths": {"$regex": search, "$options": "i"}}
        ]
    # International collections handling
    if country in INTERNATIONAL_COUNTRIES:
        intl_results, total = await _query_international(country, page, page_size, filter_conditions)
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        return PaginatedUniversityResponse(
            universities=[UniversityResponse(**r) for r in intl_results],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
    
    # 获取总数
    try:
        if hasattr(db.universities, 'count_documents'):
            total = await db.universities.count_documents(filter_conditions)
        else:
            total = 50  # 默认值
    except Exception as e:
        print(f"获取总数失败: {e}")
        total = 50  # 默认值
    
    # 执行分页查询
    try:
        cursor = db.universities.find(filter_conditions).skip(skip).limit(page_size).sort("rank", 1)
        universities = await cursor.to_list(length=page_size)
    except Exception as e:
        print(f"查询失败: {e}")
        universities = []
    
    # 计算分页信息
    total_pages = (total + page_size - 1) // page_size
    has_next = page < total_pages
    has_prev = page > 1
    
    # 转换为响应格式
    result = []
    for uni in universities:
        result.append(UniversityResponse(
            id=str(uni["_id"]),
            name=uni["name"],
            country=uni["country"],
            state=uni["state"],
            rank=uni["rank"],
            tuition=uni["tuition"],
            intl_rate=uni["intlRate"],
            type=uni["type"],
            strengths=uni["strengths"],
            gpt_summary=uni["gptSummary"],
            logo_url=uni.get("logoUrl")
        ))
    
    return PaginatedUniversityResponse(
        universities=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )

@router.get("/{university_id}", response_model=UniversityResponse)
async def get_university(university_id: str):
    """获取特定大学详情"""
    db = get_db()
    
    try:
        uni_id = ObjectId(university_id)
    except:
        raise HTTPException(status_code=400, detail="无效的大学ID")
    
    university = await db.universities.find_one({"_id": uni_id})
    if not university:
        raise HTTPException(status_code=404, detail="大学不存在")
    
    return UniversityResponse(
        id=str(university["_id"]),
        name=university["name"],
        country=university["country"],
        state=university["state"],
        rank=university["rank"],
        tuition=university["tuition"],
        intl_rate=university["intlRate"],
        type=university["type"],
        strengths=university["strengths"],
        gpt_summary=university["gptSummary"],
        logo_url=university.get("logoUrl"),
        location=university.get("location"),
        personality_types=university.get("personality_types"),
        school_size=university.get("schoolSize"),
        description=university.get("description"),
        supports_ed=university.get("supports_ed"),
        supports_ea=university.get("supports_ea"),
        supports_rd=university.get("supports_rd"),
        internship_support_score=university.get("internship_support_score"),
        acceptance_rate=university.get("acceptanceRate"),
        sat_range=university.get("satRange"),
        act_range=university.get("actRange"),
        gpa_range=university.get("gpaRange"),
        application_deadline=university.get("applicationDeadline"),
        website=university.get("website"),
        has_internship_program=university.get("has_internship_program"),
        has_research_program=university.get("has_research_program"),
        tags=university.get("tags")
    )

@router.get("/countries/list")
async def get_countries():
    """获取所有国家列表"""
    db = get_db()
    
    countries = await db.universities.distinct("country")
    return {"countries": sorted(countries)}

@router.get("/strengths/list")
async def get_strengths():
    """获取所有优势专业列表"""
    db = get_db()
    
    try:
        # 获取所有大学的strengths字段
        universities = await db.universities.find({}, {"strengths": 1}).to_list(None)
        
        # 提取所有strengths并去重
        all_strengths = set()
        for uni in universities:
            if "strengths" in uni and isinstance(uni["strengths"], list):
                for strength in uni["strengths"]:
                    if strength and isinstance(strength, str):
                        all_strengths.add(strength.strip())
        
        return {"strengths": sorted(list(all_strengths))}
    except Exception as e:
        print(f"获取strengths失败: {e}")
        return {"strengths": []} 