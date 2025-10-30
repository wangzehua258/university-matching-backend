from pydantic import BaseModel, Field
from typing import List


class UniversityUK(BaseModel):
    name: str
    country: str = Field("United Kingdom")
    city: str
    rank: int
    tuition_local: int
    currency: str = Field("GBP")
    tuition_usd: int
    study_length_years: float
    ucas_deadline_type: str
    typical_offer_alevel: str
    typical_offer_ib: str
    foundation_available: bool
    russell_group: bool
    placement_year_available: bool
    interview_required: bool
    admissions_tests: str
    personal_statement_weight: int
    strengths: List[str] = []
    tags: List[str] = []
    intlRate: float
    website: str
    scholarship_available: bool


class UniversityUKResponse(BaseModel):
    id: str
    name: str
    country: str
    city: str
    rank: int
    tuition_local: int
    currency: str
    tuition_usd: int
    study_length_years: float
    ucas_deadline_type: str
    typical_offer_alevel: str
    typical_offer_ib: str
    foundation_available: bool
    russell_group: bool
    placement_year_available: bool
    interview_required: bool
    admissions_tests: str
    personal_statement_weight: int
    strengths: List[str]
    tags: List[str]
    intlRate: float
    website: str
    scholarship_available: bool


