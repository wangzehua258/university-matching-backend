from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import users, evals, universities
from gpt import gpt
from db.mongo import init_db

app = FastAPI(
    title="全球大学智能匹配系统",
    description="帮助中国家长高效决策留学路径的智能择校辅助平台",
    version="1.0.0"
)

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    await init_db()

# 注册路由
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(evals.router, prefix="/api/evals", tags=["评估"])
app.include_router(universities.router, prefix="/api/universities", tags=["大学"])
app.include_router(gpt.router, prefix="/api/gpt", tags=["AI推荐"])

@app.get("/")
async def root():
    return {"message": "全球大学智能匹配系统 API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 