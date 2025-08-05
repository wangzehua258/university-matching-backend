from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class StudentTestCreate(BaseModel):
    user_id: str = Field(..., description="用户ID")
    answers: List[int] = Field(..., description="测评答案")
    personality_type: str = Field(..., description="人格类型")
    recommended_universities: List[str] = Field(..., description="推荐大学")
    gpt_summary: str = Field(..., description="GPT生成的人格匹配解释")

class StudentTest(BaseModel):
    id: str = Field(default="", alias="_id")
    user_id: str
    answers: List[int]
    personality_type: str
    recommended_universities: List[str]
    gpt_summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class StudentTestResponse(BaseModel):
    id: str
    user_id: str
    answers: List[int]
    personality_type: str
    recommended_universities: List[str]
    gpt_summary: str
    created_at: datetime 