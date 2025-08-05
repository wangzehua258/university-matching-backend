from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from gpt.generate_reason import generate_university_recommendation_reason

router = APIRouter()

class RecommendationRequest(BaseModel):
    university_name: str
    student_interests: List[str]
    student_profile: str

@router.post("/recommendation")
async def generate_recommendation(request: RecommendationRequest):
    """生成大学推荐理由"""
    try:
        reason = await generate_university_recommendation_reason(
            request.university_name,
            request.student_interests,
            request.student_profile
        )
        return {"reason": reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成推荐理由失败: {str(e)}") 