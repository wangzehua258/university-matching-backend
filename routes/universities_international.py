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
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的ID")
    d = await db.university_au.find_one({"_id": oid})
    if not d:
        raise HTTPException(status_code=404, detail="未找到大学")
    return UniversityAUResponse(id=str(d["_id"]), **{**d, "strengths": _parse_strengths(d.get("strengths", [])), "tags": _parse_strengths(d.get("tags", []))})


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
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的ID")
    d = await db.university_uk.find_one({"_id": oid})
    if not d:
        raise HTTPException(status_code=404, detail="未找到大学")
    return UniversityUKResponse(id=str(d["_id"]), **{**d, "strengths": _parse_strengths(d.get("strengths", [])), "tags": _parse_strengths(d.get("tags", []))})


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



