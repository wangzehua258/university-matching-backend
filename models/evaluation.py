from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ParentEvaluationInput(BaseModel):
    """
    统一的家长评估输入模型：
    - 为兼容多国家（USA/AU/UK/SG）问题集，将美国字段改为可选；
    - 新增 AU/UK/SG 专用可选字段；
    - 后端根据 target_country 分流并只读取对应字段。
    """

    # 通用
    target_country: str = Field(..., description="目标国家")

    # 美国（沿用旧表单；均改为可选，避免 422）
    grade: Optional[str] = Field(None, description="年级")
    gpa_range: Optional[str] = Field(None, description="GPA范围")
    sat_score: Optional[int] = Field(None, description="SAT分数")
    activities: Optional[List[str]] = Field(default=None, description="活动经历")
    interest_fields: Optional[List[str]] = Field(default=None, description="兴趣方向")
    school_type_preference: Optional[str] = Field(None, description="学校类型偏好")
    reputation_important: Optional[bool] = Field(None, description="是否重视学校声誉")
    budget: Optional[str] = Field(None, description="预算范围")
    family_expectation: Optional[str] = Field(None, description="家长期望")
    internship_important: Optional[bool] = Field(None, description="是否重视实习机会")
    region_preference: Optional[str] = Field(None, description="地理偏好（如：California、东海岸等）")

    # Australia 专用（16题版本）
    academic_band: Optional[str] = None
    interests: Optional[List[str]] = None
    reputation_vs_value: Optional[str] = None  # Q3: 名气/性价比（权重调节）
    budget_usd: Optional[int] = None
    hard_budget_must_within: Optional[bool] = None
    study_length_preference: Optional[str] = None  # Q11: 学制偏好
    intake_preference: Optional[str] = None  # Q12: 入学时间偏好
    wil_preference: Optional[str] = None
    psw_importance: Optional[str] = None
    city_preferences: Optional[List[str]] = None
    intl_community_importance: Optional[str] = None
    english_readiness: Optional[str] = None
    accept_language_course: Optional[bool] = None  # Q14: 是否接受语言/过渡课
    hard_english_required_exclude: Optional[bool] = None
    go8_preference: Optional[str] = None
    scholarship_importance: Optional[str] = None
    career_focus: Optional[str] = None  # Q15: 就业口碑/带实习标签（权重调节）
    main_concern: Optional[str] = None  # Q16: 最担心点（用于解释排序，不单独计分）

    # United Kingdom 专用
    ucas_route: Optional[str] = None
    foundation_need: Optional[str] = None
    placement_year_pref: Optional[str] = None
    russell_pref: Optional[str] = None
    prep_level: Optional[str] = None
    region_pref: Optional[str] = None
    intl_env_importance: Optional[str] = None
    oxbridge_must_cover: Optional[bool] = None

    # Singapore 专用
    orientation: Optional[str] = None
    bond_acceptance: Optional[str] = None
    interview_portfolio: Optional[str] = None
    want_double_degree: Optional[bool] = None
    want_exchange: Optional[bool] = None
    safety_importance: Optional[str] = None
    scholarship_importance: Optional[str] = None
    tg_must: Optional[bool] = None
    hard_refuse_bond: Optional[bool] = None
    hard_refuse_interview_or_portfolio: Optional[bool] = None

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
    fallback_info: Optional[Dict[str, Any]] = Field(None, description="回退策略信息（仅AU）")  # 新增字段
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