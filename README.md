# 全球大学智能匹配系统 - 后端API

## 项目简介

这是一个基于FastAPI的留学择校辅助系统后端API，提供智能学校推荐、个性化评估和GPT分析功能。

## 功能特性

- 🎯 **智能学校推荐**：根据学生背景和家庭需求推荐合适的大学
- 🤖 **GPT个性化分析**：使用AI生成个性化的选校建议
- 👥 **匿名用户系统**：无需注册即可使用，数据持久化保存
- 📊 **家长评估**：基于学生信息的个性化择校建议
- 🧠 **学生测评**：人格类型测评和学校匹配

## 技术栈

- **框架**：FastAPI
- **数据库**：MongoDB
- **AI服务**：OpenAI GPT-3.5-turbo
- **异步处理**：Motor (MongoDB异步驱动)
- **数据验证**：Pydantic

## 快速开始

### 环境要求

- Python 3.8+
- MongoDB
- OpenAI API Key

### 安装依赖

```bash
pip install -r requirements.txt
```

### 环境配置

创建 `.env` 文件：

```env
MONGO_URL=mongodb://localhost:27017
OPENAI_API_KEY=your_openai_api_key_here
```

### 启动服务

```bash
python3 main.py
```

服务将在 `http://localhost:8000` 启动

## API文档

启动服务后，访问 `http://localhost:8000/docs` 查看完整的API文档。

### 主要接口

#### 用户相关
- `POST /api/users/anonymous` - 创建匿名用户
- `GET /api/users/anonymous/{user_id}` - 获取匿名用户信息

#### 评估相关
- `POST /api/evals/parent` - 创建家长评估
- `GET /api/evals/parent/{eval_id}` - 获取家长评估结果
- `GET /api/evals/parent/user/{user_id}` - 获取用户的家长评估列表
- `POST /api/evals/student` - 创建学生测评
- `GET /api/evals/student/{test_id}` - 获取学生测评结果
- `GET /api/evals/student/user/{user_id}` - 获取用户的学生测评列表

#### 大学相关
- `GET /api/universities` - 获取大学列表
- `GET /api/universities/{id}` - 获取大学详情
- `GET /api/universities/countries/list` - 获取国家列表
- `GET /api/universities/strengths/list` - 获取优势专业列表

#### GPT相关
- `POST /api/gpt/recommendation` - 生成推荐理由

## 数据库结构

### 用户表 (users)
```javascript
{
  "_id": ObjectId,
  "role": "anonymous",
  "created_at": ISODate
}
```

### 家长评估表 (parent_evaluations)
```javascript
{
  "_id": ObjectId,
  "user_id": "anon_xxx-xxx-xxx",
  "input": {...},
  "recommended_schools": [...],
  "gpt_summary": "...",
  "created_at": ISODate
}
```

### 学生测评表 (student_personality_tests)
```javascript
{
  "_id": ObjectId,
  "user_id": "anon_xxx-xxx-xxx",
  "answers": [...],
  "personality_type": "...",
  "recommended_universities": [...],
  "gpt_summary": "...",
  "created_at": ISODate
}
```

### 大学表 (universities)
```javascript
{
  "_id": ObjectId,
  "name": "Harvard University",
  "country": "USA",
  "rank": 1,
  "tuition": 55000,
  "intlRate": 0.12,
  "type": "private",
  "strengths": ["business", "law", "medicine"],
  "gptSummary": "..."
}
```

## 项目结构

```
backend/
├── main.py                 # 应用入口
├── requirements.txt        # 依赖列表
├── .env.example           # 环境变量示例
├── .gitignore             # Git忽略文件
├── README.md              # 项目说明
├── data/                  # 数据文件
│   └── universities.csv   # 大学数据
├── db/                    # 数据库相关
│   └── mongo.py          # MongoDB连接
├── models/                # 数据模型
│   ├── __init__.py
│   ├── evaluation.py     # 评估模型
│   ├── personality.py    # 人格测评模型
│   ├── university.py     # 大学模型
│   └── user.py           # 用户模型
├── routes/                # API路由
│   ├── __init__.py
│   ├── evals.py          # 评估相关接口
│   ├── universities.py   # 大学相关接口
│   └── users.py          # 用户相关接口
├── gpt/                   # GPT相关功能
│   ├── __init__.py
│   ├── generate_reason.py # GPT生成理由
│   └── recommend_schools.py # 学校推荐算法
├── scripts/               # 脚本文件
│   └── init_database.py  # 数据库初始化
└── utils/                 # 工具函数
    └── __init__.py
```

## 开发指南

### 添加新的API接口

1. 在 `routes/` 目录下创建或修改相应的路由文件
2. 在 `models/` 目录下定义数据模型
3. 更新API文档

### 数据库操作

使用 `scripts/init_database.py` 初始化数据库：

```bash
python3 scripts/init_database.py
```

### 测试

```bash
# 启动服务
python3 main.py

# 测试API
curl http://localhost:8000/api/universities
```

## 部署

### 本地部署

1. 安装MongoDB
2. 配置环境变量
3. 安装依赖
4. 启动服务

### 生产部署

建议使用Docker进行容器化部署：

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。 