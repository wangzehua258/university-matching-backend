import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB连接配置
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = "university_matcher"
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# Debug: Print environment variables (remove in production)
print(f"🔍 Environment Debug:")
print(f"   MONGO_URL: {MONGO_URL[:50]}..." if len(MONGO_URL) > 50 else f"   MONGO_URL: {MONGO_URL}")
print(f"   DATABASE_NAME: {DATABASE_NAME}")
print(f"   MOCK_MODE: {MOCK_MODE}")
print(f"   All env vars: {dict(os.environ)}")

# 全局数据库连接
db = None

async def connect_to_mongo():
    """连接到MongoDB数据库"""
    global db
    
    if MOCK_MODE:
        print("🔧 Running in MOCK MODE - No MongoDB connection required")
        # Create a mock database object for development
        db = MockDatabase()
        return
    
    try:
        print(f"🔌 Attempting to connect to MongoDB...")
        print(f"   URL: {MONGO_URL[:50]}..." if len(MONGO_URL) > 50 else f"   URL: {MONGO_URL}")
        
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DATABASE_NAME]
        
        # Test connection first
        await client.admin.command('ping')
        print("✅ MongoDB connection test successful")
        
        # 创建索引
        await create_indexes()
        
        print("✅ MongoDB连接成功")
    except Exception as e:
        print(f"❌ MongoDB连接失败: {e}")
        print("🔧 请确保MongoDB正在运行，或设置MOCK_MODE=true")
        
        # Fallback to mock mode if connection fails
        print("🔄 Falling back to MOCK_MODE for startup...")
        db = MockDatabase()
        # Don't raise the error, just log it and continue with mock mode
        print("⚠️  Application will run in mock mode. Some features may not work properly.")

def get_db():
    """获取数据库实例"""
    return db

async def create_indexes():
    """创建数据库索引"""
    try:
        db = get_db()
        if db is None:
            print("⚠️  数据库未连接，跳过索引创建")
            return
        
        print("创建数据库索引...")
        
        # 用户集合索引
        try:
            db.users.create_index("created_at")
            print("✅ 用户索引创建完成")
        except Exception as e:
            print(f"⚠️  用户索引创建跳过: {e}")
        
        # 大学集合索引 - 先清理可能冲突的索引
        try:
            # 删除可能冲突的索引
            existing_indexes = await db.universities.list_indexes().to_list(None)
            for index in existing_indexes:
                if index.get("name") == "name_1":
                    try:
                        await db.universities.drop_index("name_1")
                        print("🔄 删除旧名称索引")
                    except:
                        pass
                    break
            
            # 创建新索引
            db.universities.create_index("name", unique=True)
            db.universities.create_index("country")
            db.universities.create_index("rank")
            db.universities.create_index([("country", 1), ("rank", 1)])
            db.universities.create_index("strengths")
            db.universities.create_index("tuition")
            db.universities.create_index("type")
            db.universities.create_index("schoolSize")
            db.universities.create_index("tags")
            
            # 新增字段索引
            db.universities.create_index("supports_ed")
            db.universities.create_index("supports_ea")
            db.universities.create_index("supports_rd")
            db.universities.create_index("internship_support_score")
            db.universities.create_index("acceptanceRate")
            db.universities.create_index("intlRate")
            db.universities.create_index("state")
            db.universities.create_index("personality_types")
            
            print("✅ 大学索引创建完成")
        except Exception as e:
            print(f"⚠️  大学索引创建跳过: {e}")
        
        # 评估结果索引
        try:
            db.parent_evaluations.create_index("user_id")
            db.parent_evaluations.create_index("created_at")
            db.student_personality_tests.create_index("user_id")
            db.student_personality_tests.create_index("created_at")
            print("✅ 评估索引创建完成")
        except Exception as e:
            print(f"⚠️  评估索引创建跳过: {e}")
        
        print("索引创建完成")
        
    except Exception as e:
        print(f"❌ 索引创建失败: {e}")
        print("⚠️  应用将继续运行，但性能可能受影响")

async def close_mongo_connection():
    """关闭MongoDB连接"""
    if db is not None and not MOCK_MODE:
        db.client.close()
        print("MongoDB连接已关闭")
    elif MOCK_MODE:
        print("🔧 Mock mode - no connection to close")

class MockDatabase:
    """Mock database for development without MongoDB"""
    
    def __init__(self):
        self.users = MockCollection()
        self.universities = MockCollection()
        self.parent_evaluations = MockCollection()
        self.student_personality_tests = MockCollection()
        
        # Add some sample data for testing
        self._add_sample_data()
        print("🔧 Mock database initialized")
    
    def _add_sample_data(self):
        """Add sample data for testing"""
        sample_universities = [
            {
                "_id": "mock_1",
                "name": "Harvard University",
                "country": "USA",
                "state": "Massachusetts",
                "rank": 1,
                "tuition": 55000,
                "intlRate": 0.12,
                "type": "private",
                "strengths": ["business", "law", "medicine"],
                "gptSummary": "哈佛大学是世界顶尖的私立研究型大学",
                "logoUrl": "https://example.com/harvard.png"
            },
            {
                "_id": "mock_2", 
                "name": "Stanford University",
                "country": "USA",
                "state": "California",
                "rank": 2,
                "tuition": 56000,
                "intlRate": 0.15,
                "type": "private",
                "strengths": ["engineering", "computer science"],
                "gptSummary": "斯坦福大学在科技创新方面享有盛誉",
                "logoUrl": "https://example.com/stanford.png"
            }
        ]
        
        for uni in sample_universities:
            self.universities.data.append(uni)

class MockCollection:
    """Mock collection for development"""
    
    def __init__(self):
        self.data = []
    
    def create_index(self, *args, **kwargs):
        """Mock index creation"""
        pass
    
    async def insert_one(self, document):
        """Mock insert operation"""
        doc_id = f"mock_id_{len(self.data)}"
        document["_id"] = doc_id
        self.data.append(document)
        return type('MockResult', (), {'inserted_id': doc_id})()
    
    async def find_one(self, query):
        """Mock find one operation"""
        for doc in self.data:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None
    
    def find(self, query):
        """Mock find operation"""
        results = []
        for doc in self.data:
            if all(doc.get(k) == v for k, v in query.items()):
                results.append(doc)
        return MockCursor(results)
    
    async def update_one(self, query, update):
        """Mock update operation"""
        for doc in self.data:
            if all(doc.get(k) == v for k, v in query.items()):
                doc.update(update.get('$set', {}))
                return type('MockResult', (), {'modified_count': 1})()
        return type('MockResult', (), {'modified_count': 0})()
    
    async def delete_many(self, query):
        """Mock delete many operation"""
        if not query:  # If query is empty, delete all
            deleted_count = len(self.data)
            self.data.clear()
            return type('MockResult', (), {'deleted_count': deleted_count})()
        return type('MockResult', (), {'deleted_count': 0})()
    
    async def distinct(self, field):
        """Mock distinct operation"""
        values = set()
        for doc in self.data:
            if field in doc:
                values.add(doc[field])
        return list(values)

class MockCursor:
    """Mock cursor for find operations"""
    
    def __init__(self, data):
        self.data = data
        self.index = 0
    
    async def to_list(self, length=None):
        """Mock to_list operation"""
        if length is None:
            return self.data
        return self.data[:length]
    
    def sort(self, field, direction):
        """Mock sort operation"""
        if direction == -1:
            self.data.sort(key=lambda x: x.get(field, ''), reverse=True)
        else:
            self.data.sort(key=lambda x: x.get(field, ''))
        return self
    
    def skip(self, count):
        """Mock skip operation"""
        self.data = self.data[count:]
        return self
    
    def limit(self, count):
        """Mock limit operation"""
        self.data = self.data[:count]
        return self