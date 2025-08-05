import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

# 数据库连接
client = None
db = None

async def init_db():
    """初始化数据库连接"""
    global client, db
    
    # 从环境变量获取MongoDB连接字符串，如果没有则使用本地连接
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client.university_matcher
    
    # 创建索引
    await create_indexes()
    
    # 初始化示例数据
    await init_sample_data()

async def create_indexes():
    """创建数据库索引"""
    # 用户集合索引
    await db.users.create_index("created_at")
    
    # 大学集合索引
    await db.universities.create_index("name")
    await db.universities.create_index("country")
    await db.universities.create_index("rank")
    await db.universities.create_index([("country", ASCENDING), ("rank", ASCENDING)])
    
    # 评估结果索引
    await db.parent_evaluations.create_index("user_id")
    await db.student_personality_tests.create_index("user_id")

async def init_sample_data():
    """初始化示例大学数据"""
    # 检查是否已有数据
    count = await db.universities.count_documents({})
    if count > 0:
        return
    
    # 示例大学数据
    universities = [
        {
            "name": "Harvard University",
            "country": "USA",
            "state": "Massachusetts",
            "rank": 1,
            "tuition": 55000,
            "intlRate": 0.12,
            "type": "private",
            "strengths": ["business", "law", "medicine"],
            "gptSummary": "哈佛大学是世界顶尖的私立研究型大学，以其卓越的学术声誉和丰富的资源著称。",
            "logoUrl": "https://example.com/harvard-logo.png"
        },
        {
            "name": "Stanford University",
            "country": "USA",
            "state": "California",
            "rank": 2,
            "tuition": 56000,
            "intlRate": 0.15,
            "type": "private",
            "strengths": ["computer science", "engineering", "business"],
            "gptSummary": "斯坦福大学在科技创新和创业方面享有盛誉，位于硅谷中心。",
            "logoUrl": "https://example.com/stanford-logo.png"
        },
        {
            "name": "MIT",
            "country": "USA",
            "state": "Massachusetts",
            "rank": 3,
            "tuition": 54000,
            "intlRate": 0.10,
            "type": "private",
            "strengths": ["engineering", "computer science", "physics"],
            "gptSummary": "麻省理工学院在工程和科学领域世界领先，注重创新和实用研究。",
            "logoUrl": "https://example.com/mit-logo.png"
        },
        {
            "name": "University of Oxford",
            "country": "UK",
            "state": "England",
            "rank": 4,
            "tuition": 39000,
            "intlRate": 0.20,
            "type": "public",
            "strengths": ["humanities", "social sciences", "medicine"],
            "gptSummary": "牛津大学是英语世界最古老的大学，在人文社科领域享有盛誉。",
            "logoUrl": "https://example.com/oxford-logo.png"
        },
        {
            "name": "University of Cambridge",
            "country": "UK",
            "state": "England",
            "rank": 5,
            "tuition": 38000,
            "intlRate": 0.18,
            "type": "public",
            "strengths": ["science", "mathematics", "engineering"],
            "gptSummary": "剑桥大学在自然科学和数学领域世界领先，拥有悠久的历史传统。",
            "logoUrl": "https://example.com/cambridge-logo.png"
        }
    ]
    
    await db.universities.insert_many(universities)
    print(f"已初始化 {len(universities)} 所大学数据")

def get_db():
    """获取数据库实例"""
    return db 