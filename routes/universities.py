from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId

from models.university import University, UniversityResponse
from db.mongo import get_db

router = APIRouter()

@router.get("/", response_model=List[UniversityResponse])
async def get_universities(
    country: Optional[str] = Query(None, description="国家筛选"),
    rank_min: Optional[int] = Query(None, description="最低排名"),
    rank_max: Optional[int] = Query(None, description="最高排名"),
    tuition_max: Optional[int] = Query(None, description="最高学费"),
    type: Optional[str] = Query(None, description="学校类型"),
    strength: Optional[str] = Query(None, description="优势专业"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, description="返回数量限制"),
    skip: int = Query(0, description="跳过数量")
):
    """获取大学列表，支持多种筛选条件"""
    db = get_db()
    
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
    
    # 执行查询
    cursor = db.universities.find(filter_conditions).skip(skip).limit(limit)
    universities = await cursor.to_list(length=limit)
    
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
    
    return result

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
        logo_url=university.get("logoUrl")
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
    
    strengths = await db.universities.distinct("strengths")
    return {"strengths": sorted(strengths)} 