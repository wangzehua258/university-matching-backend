from pydantic import BaseModel, Field
from typing import List, Optional


class UniversitySG(BaseModel):
    name: str
    country: str = Field("Singapore")
    city: str = Field("Singapore")
    rank: int
    tuition_local: int
    currency: str = Field("SGD")
    tuition_usd: int
    study_length_years: float
    tuition_grant_available: bool
    tuition_grant_bond_years: Optional[float] = None
    interview_required: bool
    essay_or_portfolio_required: bool
    coop_or_internship_required: bool
    industry_links_score: int
    exchange_opportunities_score: Optional[int] = None
    strengths: List[str] = []
    tags: List[str] = []
    intlRate: float
    website: str
    scholarship_available: bool


class UniversitySGResponse(BaseModel):
    id: str
    name: str
    country: str
    city: str
    rank: int
    tuition_local: int
    currency: str
    tuition_usd: int
    study_length_years: float
    tuition_grant_available: bool
    tuition_grant_bond_years: Optional[float] = None
    interview_required: bool
    essay_or_portfolio_required: bool
    coop_or_internship_required: bool
    industry_links_score: int
    exchange_opportunities_score: Optional[int] = None
    strengths: List[str]
    tags: List[str]
    intlRate: float
    website: str
    scholarship_available: bool



