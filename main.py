from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routes import evals, universities, users
from db.mongo import connect_to_mongo, close_mongo_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接数据库
    await connect_to_mongo()
    yield
    # 关闭时断开数据库连接
    await close_mongo_connection()

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
    "https://your-domain.com",  # Replace with your GoDaddy domain
    "https://your-vercel-app.vercel.app",  # Replace with your Vercel app URL
]

# Add environment variable for production origins
if os.getenv("ALLOWED_ORIGINS"):
    allowed_origins.extend(os.getenv("ALLOWED_ORIGINS").split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(evals.router, prefix="/api/evals", tags=["评估"])
app.include_router(universities.router, prefix="/api/universities", tags=["大学"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])

@app.get("/")
async def root():
    return {"message": "University Matcher API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 