# 大学数据管理指南

## 📁 文件结构

```
data/
├── README.md                    # 本说明文件
├── universities_template.csv     # CSV模板文件
├── universities.csv             # 你的大学数据文件（需要创建）
└── universities.json            # JSON格式数据（可选）
```

## 🚀 推荐工作流程

### 1. 使用Excel/Google Sheets管理数据

**优点：**
- 界面友好，易于编辑
- 支持多人协作
- 可以添加公式和验证
- 支持筛选和排序

**步骤：**
1. 打开 `universities_template.csv` 作为模板
2. 在Excel/Google Sheets中编辑
3. 添加更多大学数据
4. 导出为CSV格式
5. 保存为 `universities.csv`

### 2. 数据字段说明

| 字段名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| name | 字符串 | ✅ | 大学名称（唯一） |
| country | 字符串 | ✅ | 国家 |
| state | 字符串 | ✅ | 州/省 |
| rank | 整数 | ✅ | 排名（1-100） |
| tuition | 整数 | ✅ | 学费（美元） |
| intlRate | 小数 | ✅ | 国际学生比例（0.0-1.0） |
| type | 字符串 | ✅ | 类型：private/public |
| schoolSize | 字符串 | ✅ | 规模：small/medium/large |
| strengths | 字符串 | ✅ | 优势专业，用逗号分隔 |
| tags | 字符串 | ✅ | 标签，用逗号分隔 |
| has_internship_program | 布尔 | ✅ | 是否有实习项目 |
| has_research_program | 布尔 | ✅ | 是否有研究项目 |
| gptSummary | 字符串 | ✅ | 中文描述 |
| logoUrl | 字符串 | ❌ | 学校logo URL |
| acceptanceRate | 小数 | ✅ | 录取率（0.0-1.0） |
| satRange | 字符串 | ✅ | SAT分数范围 |
| actRange | 字符串 | ✅ | ACT分数范围 |
| gpaRange | 字符串 | ✅ | GPA范围 |
| applicationDeadline | 字符串 | ✅ | 申请截止日期 |
| website | 字符串 | ✅ | 官网 |
| supports_ed | 布尔 | ✅ | 支持ED申请 |
| supports_ea | 布尔 | ✅ | 支持EA申请 |
| supports_rd | 布尔 | ✅ | 支持RD申请 |
| internship_support_score | 整数 | ✅ | 实习支持评分（1-10） |
| personality_types | 字符串 | ✅ | 适合人格类型，用逗号分隔 |

### 3. 标签系统

**学术支持标签：**
- `academic_competitions` - 学术竞赛支持
- `undergrad_research` - 本科生研究机会
- `recommendation_letter_support` - 推荐信支持

**职业发展标签：**
- `career_center_support` - 职业中心支持
- `entrepreneurship_friendly` - 创业友好
- `student_government_support` - 学生政府支持

**国际化标签：**
- `intl_employment_friendly` - 国际就业友好
- `community_service_opportunities` - 社区服务机会

### 4. 人格类型

**可选值：**
- `学术明星型` - 适合学术研究
- `全能型` - 适合全面发展
- `探究型` - 适合科研探索
- `实践型` - 适合实践应用
- `艺术型` - 适合艺术创作
- `社交型` - 适合社交活动

## 🔧 使用方法

### 导入数据

```bash
# 在Render Shell中
cd /opt/render/project/src
python scripts/init_database.py

# 在本地
cd university-matching-backend
source venv/bin/activate
python scripts/init_database.py
```

### 脚本功能

- **自动检测数据文件**：优先使用CSV，其次JSON
- **增量更新**：可以选择是否清空现有数据
- **数据验证**：自动检查数据格式和必需字段
- **统计信息**：显示数据库统计信息
- **导出功能**：可以导出当前数据到CSV

## 📊 数据管理建议

### 1. 分批管理
- 先添加前50所顶尖大学
- 再添加50-100名大学
- 最后添加国际大学

### 2. 数据质量
- 确保所有必需字段都有值
- 验证数据格式正确性
- 定期备份数据

### 3. 协作编辑
- 使用Google Sheets支持多人编辑
- 设置数据验证规则
- 定期同步和更新

## 🎯 快速开始

1. **复制模板**：复制 `universities_template.csv`
2. **重命名**：改为 `universities.csv`
3. **添加数据**：在Excel中编辑，添加更多大学
4. **保存**：导出为CSV格式
5. **运行脚本**：执行 `python scripts/init_database.py`

## 💡 提示

- 保持CSV格式的一致性
- 使用UTF-8编码保存文件
- 定期备份你的数据文件
- 测试数据导入后再部署到生产环境
