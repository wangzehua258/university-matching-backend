#!/usr/bin/env python3
"""
数据库初始化脚本
用于导入大学数据、创建索引等
"""

import os
import sys
import json
import csv
from pathlib import Path
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def connect_database():
    """连接MongoDB数据库"""
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = MongoClient(mongo_url)
    db = client.university_matcher
    return db

def create_indexes(db):
    """创建数据库索引"""
    print("创建数据库索引...")
    
    # 用户集合索引
    db.users.create_index("created_at")
    
    # 大学集合索引
    db.universities.create_index("name")
    db.universities.create_index("country")
    db.universities.create_index("rank")
    db.universities.create_index([("country", ASCENDING), ("rank", ASCENDING)])
    db.universities.create_index("strengths")
    db.universities.create_index("tuition")
    db.universities.create_index("type")
    db.universities.create_index("schoolSize")
    db.universities.create_index("tags")
    
    # 评估结果索引
    db.parent_evaluations.create_index("user_id")
    db.parent_evaluations.create_index("created_at")
    db.student_personality_tests.create_index("user_id")
    db.student_personality_tests.create_index("created_at")
    
    print("索引创建完成")

def import_universities_from_csv(db, csv_file_path):
    """从CSV文件导入大学数据"""
    if not os.path.exists(csv_file_path):
        print(f"CSV文件不存在: {csv_file_path}")
        return
    
    print(f"从CSV文件导入大学数据: {csv_file_path}")
    
    # 清空现有数据
    db.universities.delete_many({})
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        universities = []
        
        for row in reader:
            university = {
                "name": row.get("name", ""),
                "country": row.get("country", ""),
                "state": row.get("state", ""),
                "rank": int(row.get("rank", 999)),
                "tuition": int(row.get("tuition", 0)),
                "intlRate": float(row.get("intl_rate", 0)),
                "type": row.get("type", "private"),
                "schoolSize": row.get("school_size", "medium"),
                "strengths": row.get("strengths", "").split(",") if row.get("strengths") else [],
                "tags": row.get("tags", "").split(",") if row.get("tags") else [],
                "has_internship_program": row.get("has_internship_program", "true").lower() == "true",
                "has_research_program": row.get("has_research_program", "true").lower() == "true",
                "gptSummary": row.get("gpt_summary", ""),
                "logoUrl": row.get("logo_url", ""),
                "acceptanceRate": float(row.get("acceptance_rate", 0)),
                "satRange": row.get("sat_range", ""),
                "actRange": row.get("act_range", ""),
                "gpaRange": row.get("gpa_range", ""),
                "applicationDeadline": row.get("application_deadline", ""),
                "website": row.get("website", "")
            }
            universities.append(university)
        
        if universities:
            result = db.universities.insert_many(universities)
            print(f"成功导入 {len(result.inserted_ids)} 所大学")
        else:
            print("没有找到有效的大学数据")

def import_sample_data(db):
    """导入示例数据（如果没有CSV文件）"""
    print("导入示例大学数据...")
    
    # 清空现有数据
    db.universities.delete_many({})
    
    universities = [
        {
            "name": "Harvard University",
            "country": "USA",
            "state": "Massachusetts",
            "rank": 1,
            "tuition": 55000,
            "intlRate": 0.12,
            "type": "private",
            "schoolSize": "large",
            "strengths": ["business", "law", "medicine", "computer science"],
            "tags": ["undergrad_research", "academic_competitions", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "哈佛大学是世界顶尖的私立研究型大学，以其卓越的学术声誉和丰富的资源著称。",
            "logoUrl": "https://example.com/harvard-logo.png",
            "acceptanceRate": 0.05,
            "satRange": "1460-1580",
            "actRange": "33-36",
            "gpaRange": "3.9-4.0",
            "applicationDeadline": "2024-01-01",
            "website": "https://www.harvard.edu"
        },
        {
            "name": "Stanford University",
            "country": "USA",
            "state": "California",
            "rank": 2,
            "tuition": 56000,
            "intlRate": 0.15,
            "type": "private",
            "schoolSize": "large",
            "strengths": ["computer science", "engineering", "business", "artificial intelligence"],
            "tags": ["entrepreneurship_friendly", "undergrad_research", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "斯坦福大学在科技创新和创业方面享有盛誉，位于硅谷中心。",
            "logoUrl": "https://example.com/stanford-logo.png",
            "acceptanceRate": 0.04,
            "satRange": "1440-1570",
            "actRange": "32-35",
            "gpaRange": "3.8-4.0",
            "applicationDeadline": "2024-01-02",
            "website": "https://www.stanford.edu"
        },
        {
            "name": "MIT",
            "country": "USA",
            "state": "Massachusetts",
            "rank": 3,
            "tuition": 54000,
            "intlRate": 0.10,
            "type": "private",
            "schoolSize": "medium",
            "strengths": ["engineering", "computer science", "physics", "artificial intelligence"],
            "tags": ["undergrad_research", "academic_competitions", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "麻省理工学院在工程和科学领域世界领先，注重创新和实用研究。",
            "logoUrl": "https://example.com/mit-logo.png",
            "acceptanceRate": 0.07,
            "satRange": "1500-1570",
            "actRange": "34-36",
            "gpaRange": "3.9-4.0",
            "applicationDeadline": "2024-01-01",
            "website": "https://www.mit.edu"
        },
        {
            "name": "University of California, Berkeley",
            "country": "USA",
            "state": "California",
            "rank": 4,
            "tuition": 44000,
            "intlRate": 0.15,
            "type": "public",
            "schoolSize": "large",
            "strengths": ["computer science", "engineering", "business", "artificial intelligence"],
            "tags": ["undergrad_research", "entrepreneurship_friendly", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "加州大学伯克利分校在计算机科学和工程领域享有盛誉，位于科技创新的前沿。",
            "logoUrl": "https://example.com/berkeley-logo.png",
            "acceptanceRate": 0.15,
            "satRange": "1330-1530",
            "actRange": "29-35",
            "gpaRange": "3.7-4.0",
            "applicationDeadline": "2024-11-30",
            "website": "https://www.berkeley.edu"
        },
        {
            "name": "Carnegie Mellon University",
            "country": "USA",
            "state": "Pennsylvania",
            "rank": 5,
            "tuition": 58000,
            "intlRate": 0.20,
            "type": "private",
            "schoolSize": "medium",
            "strengths": ["computer science", "engineering", "artificial intelligence", "robotics"],
            "tags": ["undergrad_research", "academic_competitions", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "卡内基梅隆大学在计算机科学和人工智能领域世界领先，特别在机器人技术方面有独特优势。",
            "logoUrl": "https://example.com/cmu-logo.png",
            "acceptanceRate": 0.15,
            "satRange": "1460-1560",
            "actRange": "33-35",
            "gpaRange": "3.8-4.0",
            "applicationDeadline": "2024-01-01",
            "website": "https://www.cmu.edu"
        },
        {
            "name": "University of Michigan",
            "country": "USA",
            "state": "Michigan",
            "rank": 6,
            "tuition": 52000,
            "intlRate": 0.12,
            "type": "public",
            "schoolSize": "large",
            "strengths": ["engineering", "computer science", "business", "medicine"],
            "tags": ["undergrad_research", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "密歇根大学在工程和计算机科学领域实力强劲，提供丰富的实习和研究机会。",
            "logoUrl": "https://example.com/umich-logo.png",
            "acceptanceRate": 0.20,
            "satRange": "1340-1530",
            "actRange": "31-34",
            "gpaRange": "3.6-4.0",
            "applicationDeadline": "2024-02-01",
            "website": "https://www.umich.edu"
        },
        {
            "name": "Georgia Institute of Technology",
            "country": "USA",
            "state": "Georgia",
            "rank": 7,
            "tuition": 33000,
            "intlRate": 0.08,
            "type": "public",
            "schoolSize": "large",
            "strengths": ["engineering", "computer science", "industrial engineering"],
            "tags": ["undergrad_research", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "佐治亚理工学院在工程领域享有盛誉，特别是工业工程和计算机科学专业。",
            "logoUrl": "https://example.com/gatech-logo.png",
            "acceptanceRate": 0.18,
            "satRange": "1390-1540",
            "actRange": "31-35",
            "gpaRange": "3.7-4.0",
            "applicationDeadline": "2024-01-15",
            "website": "https://www.gatech.edu"
        },
        {
            "name": "University of Illinois Urbana-Champaign",
            "country": "USA",
            "state": "Illinois",
            "rank": 8,
            "tuition": 34000,
            "intlRate": 0.10,
            "type": "public",
            "schoolSize": "large",
            "strengths": ["engineering", "computer science", "agriculture"],
            "tags": ["undergrad_research", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "伊利诺伊大学香槟分校在工程和计算机科学领域实力强劲，提供优质的教育和研究环境。",
            "logoUrl": "https://example.com/uiuc-logo.png",
            "acceptanceRate": 0.60,
            "satRange": "1330-1500",
            "actRange": "29-33",
            "gpaRange": "3.5-4.0",
            "applicationDeadline": "2024-01-05",
            "website": "https://www.illinois.edu"
        },
        {
            "name": "University of Texas at Austin",
            "country": "USA",
            "state": "Texas",
            "rank": 9,
            "tuition": 38000,
            "intlRate": 0.05,
            "type": "public",
            "schoolSize": "large",
            "strengths": ["engineering", "computer science", "business"],
            "tags": ["undergrad_research", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "德克萨斯大学奥斯汀分校在工程和计算机科学领域表现优异，位于科技发展迅速的奥斯汀市。",
            "logoUrl": "https://example.com/utexas-logo.png",
            "acceptanceRate": 0.32,
            "satRange": "1230-1480",
            "actRange": "26-33",
            "gpaRange": "3.4-4.0",
            "applicationDeadline": "2024-12-01",
            "website": "https://www.utexas.edu"
        },
        {
            "name": "Purdue University",
            "country": "USA",
            "state": "Indiana",
            "rank": 10,
            "tuition": 29000,
            "intlRate": 0.12,
            "type": "public",
            "schoolSize": "large",
            "strengths": ["engineering", "aviation", "agriculture"],
            "tags": ["undergrad_research", "intl_employment_friendly"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "普渡大学在工程领域享有盛誉，特别是航空工程专业，提供优质的教育和研究机会。",
            "logoUrl": "https://example.com/purdue-logo.png",
            "acceptanceRate": 0.67,
            "satRange": "1190-1440",
            "actRange": "25-32",
            "gpaRange": "3.3-4.0",
            "applicationDeadline": "2024-01-15",
            "website": "https://www.purdue.edu"
        }
    ]
    
    result = db.universities.insert_many(universities)
    print(f"成功导入 {len(result.inserted_ids)} 所大学")

def main():
    """主函数"""
    print("开始初始化数据库...")
    
    # 连接数据库
    db = connect_database()
    
    # 创建索引
    create_indexes(db)
    
    # 尝试从CSV文件导入数据
    csv_file = Path(__file__).parent.parent / "data" / "universities.csv"
    if csv_file.exists():
        import_universities_from_csv(db, str(csv_file))
    else:
        print("未找到universities.csv文件，导入示例数据")
        import_sample_data(db)
    
    print("数据库初始化完成！")

if __name__ == "__main__":
    main() 