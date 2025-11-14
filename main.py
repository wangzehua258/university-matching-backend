from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routes import evals, universities, users
from routes import universities_international
from db.mongo import connect_to_mongo, close_mongo_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 启动时连接数据库
        print("🚀 Starting application...")
        await connect_to_mongo()
        print("✅ Application startup completed")
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        print("⚠️  Application will continue in limited mode")
    
    yield
    
    try:
        # 关闭时断开数据库连接
        await close_mongo_connection()
        print("✅ Application shutdown completed")
    except Exception as e:
        print(f"❌ Application shutdown error: {e}")

app = FastAPI(
    title="University Matcher API",
    description="个性化大学推荐系统API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
import os
allowed_origins = [
    "http://localhost:3000", 
    "http://localhost:3001",
    "https://www.xuanxiao360.com",  # Production domain with www
    "https://xuanxiao360.com",  # Production domain without www
    "http://www.xuanxiao360.com",  # HTTP version with www (if needed)
    "http://xuanxiao360.com",  # HTTP version without www (if needed)
]

# Add environment variable for production origins
if os.getenv("ALLOWED_ORIGINS"):
    additional_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS").split(",") if origin.strip()]
    allowed_origins.extend(additional_origins)

# Remove duplicates while preserving order
seen = set()
allowed_origins = [x for x in allowed_origins if not (x in seen or seen.add(x))]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 注册路由
app.include_router(evals.router, prefix="/api/evals", tags=["评估"])
app.include_router(universities.router, prefix="/api/universities", tags=["大学"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(universities_international.router, prefix="/api/international", tags=["国际大学"])

@app.get("/api/international/ping")
async def international_ping():
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "University Matcher API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint that doesn't require database connection"""
    try:
        from db.mongo import get_db
        db = get_db()
        if db is not None:
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        else:
            return {
                "status": "degraded",
                "database": "not_connected",
                "timestamp": "2024-01-01T00:00:00Z"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 