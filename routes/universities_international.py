from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId

from db.mongo import get_db
from models.university_au import UniversityAUResponse
from models.university_uk import UniversityUKResponse
from models.university_sg import UniversitySGResponse


router = APIRouter()


def _parse_strengths(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


@router.get("/au", response_model=List[UniversityAUResponse])
async def list_au_universities(
    city: Optional[str] = None,
    rank_max: Optional[int] = None,
    wil_required: Optional[bool] = Query(None, description="是否必须WIL"),
    group_of_eight: Optional[bool] = None,
    strength: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    db = get_db()
    filter_conditions = {"country": "Australia"}
    if city:
        filter_conditions["city"] = city
    if rank_max is not None:
        filter_conditions["rank"] = {"$lte": rank_max}
    if wil_required is not None:
        filter_conditions["work_integrated_learning"] = wil_required
    if group_of_eight is not None:
        filter_conditions["group_of_eight"] = group_of_eight
    if strength:
        filter_conditions["strengths"] = {"$in": [strength]}

    cursor = db.university_au.find(filter_conditions).skip((page - 1) * page_size).limit(page_size).sort("rank", 1)
    docs = await cursor.to_list(length=page_size)
    return [UniversityAUResponse(id=str(d["_id"]), **{**d, "strengths": _parse_strengths(d.get("strengths", [])), "tags": _parse_strengths(d.get("tags", []))}) for d in docs]


@router.get("/au/{id}", response_model=UniversityAUResponse)
async def get_au_university(id: str):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="数据库未连接")
    
    try:
        oid = ObjectId(id)
    except Exception as e:
        print(f"❌ 无效的ID格式: {id}, 错误: {e}")
        raise HTTPException(status_code=400, detail=f"无效的ID格式: {id}")
    
    try:
        d = await db.university_au.find_one({"_id": oid})
        if not d:
            print(f"❌ 未找到大学: ID={id}")
            raise HTTPException(status_code=404, detail="未找到大学")
        
        # 确保返回的数据包含所有必需字段
        # 处理数值类型转换
        tuition_usd_val = d.get("tuition_usd", 0)
        if isinstance(tuition_usd_val, float):
            tuition_usd_val = int(tuition_usd_val)
        
        rank_val = d.get("rank", 9999)
        if isinstance(rank_val, float):
            rank_val = int(rank_val)
        
        result_data = {
            "id": str(d["_id"]),
            "name": d.get("name", ""),
            "country": d.get("country", "Australia"),
            "city": d.get("city", ""),
            "rank": rank_val,
            "tuition_local": int(d.get("tuition_local", 0)),
            "currency": d.get("currency", "AUD"),
            "tuition_usd": tuition_usd_val,
            "study_length_years": float(d.get("study_length_years", 3.0)),
            "intakes": d.get("intakes", ""),
            "english_requirements": d.get("english_requirements", ""),
            "requires_english_test": bool(d.get("requires_english_test", False)),
            "group_of_eight": bool(d.get("group_of_eight", False)),
            "work_integrated_learning": bool(d.get("work_integrated_learning", False)),
            "placement_rate": d.get("placement_rate"),
            "post_study_visa_years": float(d.get("post_study_visa_years", 2.0)),
            "scholarship_available": bool(d.get("scholarship_available", False)),
            "strengths": _parse_strengths(d.get("strengths", [])),
            "tags": _parse_strengths(d.get("tags", [])),
            "intlRate": float(d.get("intlRate", 0.0)),
            "website": d.get("website", "")
        }
        
        return UniversityAUResponse(**result_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取澳大利亚大学详情失败: ID={id}, 错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.get("/uk", response_model=List[UniversityUKResponse])
async def list_uk_universities(
    city: Optional[str] = None,
    rank_max: Optional[int] = None,
    foundation_available: Optional[bool] = None,
    placement_year_available: Optional[bool] = None,
    russell_group: Optional[bool] = None,
    strength: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    db = get_db()
    filter_conditions = {"country": "United Kingdom"}
    if city:
        filter_conditions["city"] = city
    if rank_max is not None:
        filter_conditions["rank"] = {"$lte": rank_max}
    if foundation_available is not None:
        filter_conditions["foundation_available"] = foundation_available
    if placement_year_available is not None:
        filter_conditions["placement_year_available"] = placement_year_available
    if russell_group is not None:
        filter_conditions["russell_group"] = russell_group
    if strength:
        filter_conditions["strengths"] = {"$in": [strength]}

    cursor = db.university_uk.find(filter_conditions).skip((page - 1) * page_size).limit(page_size).sort("rank", 1)
    docs = await cursor.to_list(length=page_size)
    return [UniversityUKResponse(id=str(d["_id"]), **{**d, "strengths": _parse_strengths(d.get("strengths", [])), "tags": _parse_strengths(d.get("tags", []))}) for d in docs]


@router.get("/uk/{id}", response_model=UniversityUKResponse)
async def get_uk_university(id: str):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="数据库未连接")
    
    try:
        oid = ObjectId(id)
    except Exception as e:
        print(f"❌ 无效的ID格式: {id}, 错误: {e}")
        raise HTTPException(status_code=400, detail=f"无效的ID格式: {id}")
    
    try:
        d = await db.university_uk.find_one({"_id": oid})
        if not d:
            print(f"❌ 未找到大学: ID={id}")
            raise HTTPException(status_code=404, detail="未找到大学")
        
        # 确保返回的数据包含所有必需字段，处理数据类型转换
        tuition_usd_val = d.get("tuition_usd", 0)
        if isinstance(tuition_usd_val, float):
            tuition_usd_val = int(tuition_usd_val)
        
        rank_val = d.get("rank", 9999)
        if isinstance(rank_val, float):
            rank_val = int(rank_val)
        
        personal_statement_weight_val = d.get("personal_statement_weight", 0)
        if isinstance(personal_statement_weight_val, float):
            personal_statement_weight_val = int(personal_statement_weight_val)
        
        intl_rate = d.get("intlRate")
        if intl_rate is not None:
            intl_rate = float(intl_rate)
        else:
            intl_rate = None
        
        result_data = {
            "id": str(d["_id"]),
            "name": d.get("name", ""),
            "country": d.get("country", "United Kingdom"),
            "city": d.get("city", ""),
            "rank": rank_val,
            "tuition_local": int(d.get("tuition_local", 0)),
            "currency": d.get("currency", "GBP"),
            "tuition_usd": tuition_usd_val,
            "study_length_years": float(d.get("study_length_years", 3.0)),
            "ucas_deadline_type": d.get("ucas_deadline_type", ""),
            "typical_offer_alevel": d.get("typical_offer_alevel", ""),
            "typical_offer_ib": d.get("typical_offer_ib", ""),
            "foundation_available": bool(d.get("foundation_available", False)),
            "russell_group": bool(d.get("russell_group", False)),
            "placement_year_available": bool(d.get("placement_year_available", False)),
            "interview_required": bool(d.get("interview_required", False)),
            "admissions_tests": d.get("admissions_tests", "None"),
            "personal_statement_weight": personal_statement_weight_val,
            "strengths": _parse_strengths(d.get("strengths", [])),
            "tags": _parse_strengths(d.get("tags", [])),
            "intlRate": intl_rate,
            "website": d.get("website", ""),
            "scholarship_available": bool(d.get("scholarship_available", False))
        }
        
        return UniversityUKResponse(**result_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取英国大学详情失败: ID={id}, 错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.get("/sg", response_model=List[UniversitySGResponse])
async def list_sg_universities(
    rank_max: Optional[int] = None,
    tuition_grant_available: Optional[bool] = None,
    strength: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    db = get_db()
    filter_conditions = {"country": "Singapore"}
    if rank_max is not None:
        filter_conditions["rank"] = {"$lte": rank_max}
    if tuition_grant_available is not None:
        filter_conditions["tuition_grant_available"] = tuition_grant_available
    if strength:
        filter_conditions["strengths"] = {"$in": [strength]}

    cursor = db.university_sg.find(filter_conditions).skip((page - 1) * page_size).limit(page_size).sort("rank", 1)
    docs = await cursor.to_list(length=page_size)
    return [UniversitySGResponse(id=str(d["_id"]), **{**d, "strengths": _parse_strengths(d.get("strengths", [])), "tags": _parse_strengths(d.get("tags", []))}) for d in docs]


@router.get("/sg/{id}", response_model=UniversitySGResponse)
async def get_sg_university(id: str):
    db = get_db()
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的ID")
    d = await db.university_sg.find_one({"_id": oid})
    if not d:
        raise HTTPException(status_code=404, detail="未找到大学")
    return UniversitySGResponse(id=str(d["_id"]), **{**d, "strengths": _parse_strengths(d.get("strengths", [])), "tags": _parse_strengths(d.get("tags", []))})



