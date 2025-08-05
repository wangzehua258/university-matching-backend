from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    role: str = Field(default="anonymous", description="用户角色: anonymous")

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str = Field(default="", alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class UserResponse(BaseModel):
    id: str
    role: str
    created_at: datetime 