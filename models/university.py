from pydantic import BaseModel, Field
from typing import List, Optional

class University(BaseModel):
    id: Optional[str] = Field(None, alias="_id", exclude=True)  # Exclude from dict by default
    name: str = Field(..., description="大学名称")
    country: str = Field(..., description="国家")
    state: str = Field(..., description="州/省")
    rank: int = Field(..., description="排名")
    tuition: int = Field(..., description="学费(美元)")
    intl_rate: float = Field(..., description="国际生比例", alias="intlRate")
    type: str = Field(..., description="学校类型: private/public")
    strengths: List[str] = Field(..., description="优势专业")
    gpt_summary: str = Field(..., description="GPT生成的描述", alias="gptSummary")
    logo_url: Optional[str] = Field(None, description="Logo URL", alias="logoUrl")
    
    # Additional fields that might be used
    location: Optional[str] = Field(None, description="位置描述")
    personality_types: Optional[List[str]] = Field(None, description="适合的人格类型")
    school_size: Optional[str] = Field(None, description="学校规模", alias="schoolSize")
    description: Optional[str] = Field(None, description="描述")
    
    # Application round support
    supports_ed: Optional[bool] = Field(False, description="是否支持Early Decision", alias="has_ed")
    supports_ea: Optional[bool] = Field(False, description="是否支持Early Action", alias="has_ea")
    supports_rd: Optional[bool] = Field(True, description="是否支持Regular Decision", alias="has_rd")
    
    # Enhanced internship support
    internship_support_score: Optional[float] = Field(0.0, description="实习项目支持程度(0-10)")
    
    # Application details
    acceptance_rate: Optional[float] = Field(None, description="录取率", alias="acceptanceRate")
    sat_range: Optional[str] = Field(None, description="SAT分数范围", alias="satRange")
    act_range: Optional[str] = Field(None, description="ACT分数范围", alias="actRange")
    gpa_range: Optional[str] = Field(None, description="GPA范围", alias="gpaRange")
    application_deadline: Optional[str] = Field(None, description="申请截止日期", alias="applicationDeadline")
    website: Optional[str] = Field(None, description="官网")
    
    # Program features
    has_internship_program: Optional[bool] = Field(False, description="是否有实习项目")
    has_research_program: Optional[bool] = Field(False, description="是否有研究项目")
    tags: Optional[List[str]] = Field(default_factory=list, description="学校标签和资源支持类型")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class UniversityResponse(BaseModel):
    id: str
    name: str
    country: str
    state: str
    rank: int
    tuition: int
    intl_rate: float
    type: str
    strengths: List[str]
    gpt_summary: str
    logo_url: Optional[str] = None
    location: Optional[str] = None
    personality_types: Optional[List[str]] = None
    school_size: Optional[str] = None
    description: Optional[str] = None
    
    # Application round support
    supports_ed: Optional[bool] = None
    supports_ea: Optional[bool] = None
    supports_rd: Optional[bool] = None
    
    # Enhanced internship support
    internship_support_score: Optional[float] = None
    
    # Application details
    acceptance_rate: Optional[float] = None
    sat_range: Optional[str] = None
    act_range: Optional[str] = None
    gpa_range: Optional[str] = None
    application_deadline: Optional[str] = None
    website: Optional[str] = None
    
    # Program features
    has_internship_program: Optional[bool] = None
    has_research_program: Optional[bool] = None
    tags: Optional[List[str]] = None 