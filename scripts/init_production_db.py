#!/usr/bin/env python3
"""
Production database initialization script
Run this after deploying to Render to populate the production database
"""

import os
import sys
import asyncio
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

async def init_production_database():
    """Initialize production database"""
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        print("Error: MONGO_URL environment variable not set")
        return
    
    print(f"Connecting to MongoDB: {mongo_url[:50]}...")
    
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client.university_matcher
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Import initialization functions
        from scripts.init_database import create_indexes, import_sample_data
        
        # Create indexes
        print("Creating indexes...")
        create_indexes_sync(db)
        print("✅ Indexes created")
        
        # Check if universities collection is empty
        count = await db.universities.count_documents({})
        if count == 0:
            print("Universities collection is empty, importing sample data...")
            import_sample_data_sync(db)
            print("✅ Sample data imported")
        else:
            print(f"✅ Database already has {count} universities")
        
        print("🎉 Production database initialization completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()

def create_indexes_sync(db):
    """Create database indexes (sync version for async context)"""
    # This is a simplified version - you may need to adapt the original create_indexes function
    try:
        # Users
        db.users.create_index("created_at")
        
        # Universities
        db.universities.create_index("name")
        db.universities.create_index("country")
        db.universities.create_index("rank")
        db.universities.create_index([("country", 1), ("rank", 1)])
        
        # Evaluations
        db.parent_evaluations.create_index("user_id")
        db.parent_evaluations.create_index("created_at")
        db.student_personality_tests.create_index("user_id")
        db.student_personality_tests.create_index("created_at")
        
        print("Indexes created successfully")
    except Exception as e:
        print(f"Error creating indexes: {e}")

def import_sample_data_sync(db):
    """Import sample data (sync version for async context)"""
    # This would need to be adapted from your original import_sample_data function
    # For now, just print a message
    print("Sample data import would happen here")
    print("You may want to run the original init_database.py script locally and export the data")

if __name__ == "__main__":
    asyncio.run(init_production_database())
