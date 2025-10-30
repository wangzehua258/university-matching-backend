from pydantic import BaseModel, Field
from typing import List, Optional


class UniversityAU(BaseModel):
    name: str
    country: str = Field("Australia")
    city: str
    rank: int
    tuition_local: int
    currency: str = Field("AUD")
    tuition_usd: int
    study_length_years: float
    intakes: str
    english_requirements: str
    requires_english_test: bool
    group_of_eight: bool
    work_integrated_learning: bool
    placement_rate: Optional[float] = None
    post_study_visa_years: float
    scholarship_available: bool
    strengths: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    intlRate: float
    website: str


class UniversityAUResponse(BaseModel):
    id: str
    name: str
    country: str
    city: str
    rank: int
    tuition_local: int
    currency: str
    tuition_usd: int
    study_length_years: float
    intakes: str
    english_requirements: str
    requires_english_test: bool
    group_of_eight: bool
    work_integrated_learning: bool
    placement_rate: Optional[float] = None
    post_study_visa_years: float
    scholarship_available: bool
    strengths: List[str]
    tags: List[str]
    intlRate: float
    website: str


