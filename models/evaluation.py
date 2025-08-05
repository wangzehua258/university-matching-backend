from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ParentEvaluationInput(BaseModel):
    grade: str = Field(..., description="年级")
    gpa: float = Field(..., description="GPA")
    sat: Optional[int] = Field(None, description="SAT分数")
    act: Optional[int] = Field(None, description="ACT分数")
    toefl: Optional[int] = Field(None, description="托福分数")
    activities: List[str] = Field(..., description="活动经历")
    target_country: str = Field(..., description="目标国家")
    interest: List[str] = Field(..., description="兴趣方向")
    family_budget: str = Field(..., description="家庭预算")
    family_expectation: str = Field(..., description="家长期望")
    internship_importance: bool = Field(..., description="是否重视实习机会")

class ParentEvaluationCreate(BaseModel):
    user_id: str = Field(..., description="用户ID")
    input: ParentEvaluationInput

class ParentEvaluation(BaseModel):
    id: str = Field(default="", alias="_id")
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