from pydantic import BaseModel, Field
from typing import List, Optional

class University(BaseModel):
    id: str = Field(default="", alias="_id")
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