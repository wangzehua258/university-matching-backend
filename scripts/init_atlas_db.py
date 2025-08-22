#!/usr/bin/env python3
"""
MongoDB Atlas Database Initialization Script
Handles SSL connection issues and populates the cloud database
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def init_atlas_database():
    """Initialize MongoDB Atlas database with sample data"""
    
    # Your MongoDB Atlas connection string with SSL parameters
    mongo_url = "mongodb+srv://bellawang1018jhu:0kz3LuojiJWNr59J@cluster0.v9nqbc7.mongodb.net/university_matcher?retryWrites=true&w=majority&appName=Cluster0&ssl=true&ssl_cert_reqs=CERT_NONE&tlsAllowInvalidCertificates=true"
    
    print("🚀 Initializing MongoDB Atlas Database...")
    print(f"Connecting to: {mongo_url[:80]}...")
    
    try:
        # Import MongoDB client
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Create client with SSL configuration
        client = AsyncIOMotorClient(mongo_url)
        db = client.university_matcher
        
        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB Atlas connection successful!")
        
        # Create indexes
        print("📊 Creating database indexes...")
        await create_indexes(db)
        print("✅ Indexes created successfully")
        
        # Import sample data
        print("📚 Importing sample university data...")
        await import_sample_universities(db)
        print("✅ Sample data imported successfully")
        
        print("🎉 MongoDB Atlas database initialization completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if MongoDB Atlas is accessible")
        print("2. Verify network access settings in Atlas")
        print("3. Try running this from a different environment")
    finally:
        if 'client' in locals():
            client.close()

async def create_indexes(db):
    """Create database indexes"""
    try:
        # Users collection
        await db.users.create_index("created_at")
        
        # Universities collection
        await db.universities.create_index("name")
        await db.universities.create_index("country")
        await db.universities.create_index("rank")
        await db.universities.create_index([("country", 1), ("rank", 1)])
        await db.universities.create_index("strengths")
        await db.universities.create_index("tuition")
        await db.universities.create_index("type")
        await db.universities.create_index("schoolSize")
        await db.universities.create_index("tags")
        await db.universities.create_index("supports_ed")
        await db.universities.create_index("supports_ea")
        await db.universities.create_index("supports_rd")
        await db.universities.create_index("internship_support_score")
        await db.universities.create_index("acceptanceRate")
        await db.universities.create_index("intlRate")
        await db.universities.create_index("state")
        await db.universities.create_index("personality_types")
        
        # Evaluations
        await db.parent_evaluations.create_index("user_id")
        await db.parent_evaluations.create_index("created_at")
        await db.student_personality_tests.create_index("user_id")
        await db.student_personality_tests.create_index("created_at")
        
    except Exception as e:
        print(f"⚠️  Some indexes may already exist: {e}")

async def import_sample_universities(db):
    """Import sample university data"""
    
    # Clear existing data
    await db.universities.delete_many({})
    
    # Sample universities data
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
            "tags": ["undergrad_research", "academic_competitions", "intl_employment_friendly", "student_government_support", "career_center_support"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "哈佛大学是世界顶尖的私立研究型大学，以其卓越的学术声誉和丰富的资源著称。",
            "logoUrl": "https://example.com/harvard-logo.png",
            "acceptanceRate": 0.05,
            "satRange": "1460-1580",
            "actRange": "33-36",
            "gpaRange": "3.9-4.0",
            "applicationDeadline": "2024-01-01",
            "website": "https://www.harvard.edu",
            "supports_ed": True,
            "supports_ea": False,
            "supports_rd": True,
            "internship_support_score": 9.5,
            "personality_types": ["学术明星型", "全能型", "探究型"]
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
            "tags": ["entrepreneurship_friendly", "undergrad_research", "intl_employment_friendly", "career_center_support", "student_club_support"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "斯坦福大学在科技创新和创业方面享有盛誉，位于硅谷中心。",
            "logoUrl": "https://example.com/stanford-logo.png",
            "acceptanceRate": 0.04,
            "satRange": "1440-1570",
            "actRange": "32-35",
            "gpaRange": "3.8-4.0",
            "applicationDeadline": "2024-01-02",
            "website": "https://www.stanford.edu",
            "supports_ed": False,
            "supports_ea": True,
            "supports_rd": True,
            "internship_support_score": 9.8,
            "personality_types": ["实践型", "探究型", "全能型"]
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
            "tags": ["undergrad_research", "academic_competitions", "intl_employment_friendly", "career_center_support"],
            "has_internship_program": True,
            "has_research_program": True,
            "gptSummary": "麻省理工学院在工程和科学领域世界领先，注重创新和实用研究。",
            "logoUrl": "https://example.com/mit-logo.png",
            "acceptanceRate": 0.07,
            "satRange": "1500-1570",
            "actRange": "34-36",
            "gpaRange": "3.9-4.0",
            "applicationDeadline": "2024-01-01",
            "website": "https://www.mit.edu",
            "supports_ed": False,
            "supports_ea": True,
            "supports_rd": True,
            "internship_support_score": 9.2,
            "personality_types": ["学术明星型", "探究型", "实践型"]
        }
    ]
    
    # Insert universities
    result = await db.universities.insert_many(universities)
    print(f"✅ Inserted {len(result.inserted_ids)} universities")

if __name__ == "__main__":
    asyncio.run(init_atlas_database())
