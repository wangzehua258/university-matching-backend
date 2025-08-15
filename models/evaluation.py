from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ParentEvaluationInput(BaseModel):
    grade: str = Field(..., description="年级")
    gpa_range: str = Field(..., description="GPA范围")
    sat_score: Optional[int] = Field(None, description="SAT分数")
    activities: List[str] = Field(..., description="活动经历")
    interest_fields: List[str] = Field(..., description="兴趣方向")
    target_country: str = Field(..., description="目标国家")
    school_type_preference: str = Field(..., description="学校类型偏好")
    reputation_important: bool = Field(..., description="是否重视学校声誉")
    budget: str = Field(..., description="预算范围")
    family_expectation: str = Field(..., description="家长期望")
    internship_important: bool = Field(..., description="是否重视实习机会")
    region_preference: Optional[str] = Field(None, description="地理偏好（如：California、东海岸等）")

class ParentEvaluationCreate(BaseModel):
    user_id: str = Field(..., description="用户ID")
    input: ParentEvaluationInput

class ParentEvaluation(BaseModel):
    id: Optional[str] = Field(None, alias="_id", exclude=True)  # Exclude from dict by default
    user_id: str
    input: ParentEvaluationInput
    recommended_schools: List[str] = Field(default_factory=list)
    ed_suggestion: Optional[str] = None
    ea_suggestions: List[str] = Field(default_factory=list)
    rd_suggestions: List[str] = Field(default_factory=list)
    gpt_summary: str = Field(..., description="GPT生成的评估总结")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class ParentEvaluationResponse(BaseModel):
    id: str
    user_id: str
    input: ParentEvaluationInput
    recommended_schools: List[str]
    ed_suggestion: Optional[str] = None
    ea_suggestions: List[str]
    rd_suggestions: List[str]
    gpt_summary: str
    created_at: datetime 