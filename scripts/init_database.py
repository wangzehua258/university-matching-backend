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
                "strengths": row.get("strengths", "").split(",") if row.get("strengths") else [],
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
            "strengths": ["business", "law", "medicine"],
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
            "strengths": ["computer science", "engineering", "business"],
            "gptSummary": "斯坦福大学在科技创新和创业方面享有盛誉，位于硅谷中心。",
            "logoUrl": "https://example.com/stanford-logo.png",
            "acceptanceRate": 0.04,
            "satRange": "1440-1570",
            "actRange": "32-35",
            "gpaRange": "3.8-4.0",
            "applicationDeadline": "2024-01-02",
            "website": "https://www.stanford.edu"
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