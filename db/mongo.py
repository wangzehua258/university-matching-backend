import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB连接配置
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = "university_matcher"

# 全局数据库连接
db = None

async def connect_to_mongo():
    """连接到MongoDB数据库"""
    global db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DATABASE_NAME]
    
    # 创建索引
    await create_indexes()
    
    print("MongoDB连接成功")

def get_db():
    """获取数据库实例"""
    return db

async def create_indexes():
    """创建数据库索引"""
    print("创建数据库索引...")
    
    # 用户集合索引
    await db.users.create_index("created_at")
    
    # 大学集合索引
    await db.universities.create_index("name")
    await db.universities.create_index("country")
    await db.universities.create_index("rank")
    await db.universities.create_index([("country", 1), ("rank", 1)])
    await db.universities.create_index("strengths")
    await db.universities.create_index("tuition")
    await db.universities.create_index("type")
    await db.universities.create_index("schoolSize")
    await db.universities.create_index("tags")
    
    # 评估结果索引
    await db.parent_evaluations.create_index("user_id")
    await db.parent_evaluations.create_index("created_at")
    await db.student_personality_tests.create_index("user_id")
    await db.student_personality_tests.create_index("created_at")
    
    print("索引创建完成")

async def close_mongo_connection():
    """关闭MongoDB连接"""
    if db:
        db.client.close()
        print("MongoDB连接已关闭") 