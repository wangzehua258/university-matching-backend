from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime

from models.user import User, UserCreate, UserResponse
from db.mongo import get_db

router = APIRouter()

@router.post("/anonymous", response_model=dict)
async def create_anonymous_user():
    """创建匿名用户"""
    db = get_db()
    
    # 创建匿名用户记录
    user = User(
        role="anonymous",
        created_at=datetime.utcnow()
    )
    
    result = await db.users.insert_one(user.dict(by_alias=True))
    user.id = result.inserted_id
    
    return {
        "user_id": str(user.id),
        "message": "匿名用户创建成功"
    }

@router.get("/anonymous/{user_id}", response_model=UserResponse)
async def get_anonymous_user(user_id: str):
    """获取匿名用户信息"""
    db = get_db()
    
    try:
        from bson import ObjectId
        user_obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="无效的用户ID")
    
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserResponse(
        id=str(user["_id"]),
        role=user["role"],
        created_at=user["created_at"]
    ) 