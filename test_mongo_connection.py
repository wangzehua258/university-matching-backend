#!/usr/bin/env python3
"""
Test MongoDB Atlas connection
Replace the MONGO_URL below with your actual connection string
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Your actual MongoDB Atlas connection string
MONGO_URL = "mongodb+srv://bellawang1018jhu:0kz3LuojiJWNr59J@cluster0.v9nqbc7.mongodb.net/university_matcher?retryWrites=true&w=majority&appName=Cluster0"

async def test_connection():
    """Test MongoDB Atlas connection"""
    print("🔌 Testing MongoDB Atlas connection...")
    print(f"URL: {MONGO_URL[:50]}...")
    
    try:
        # Create client
        client = AsyncIOMotorClient(MONGO_URL)
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connection successful!")
        
        # Get database info
        db = client.university_matcher
        print(f"✅ Database 'university_matcher' accessible")
        
        # List collections (will be empty initially)
        collections = await db.list_collection_names()
        print(f"📚 Collections: {collections}")
        
        # Test creating a test document
        test_collection = db.test_connection
        result = await test_collection.insert_one({"test": "connection", "timestamp": "2024-01-01"})
        print(f"✅ Test document created with ID: {result.inserted_id}")
        
        # Clean up test document
        await test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Test document cleaned up")
        
        client.close()
        print("🎉 All tests passed! Your MongoDB Atlas is ready.")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your username and password")
        print("2. Verify the cluster name in the URL")
        print("3. Ensure Network Access allows connections from anywhere")
        print("4. Check if the database name is correct")

if __name__ == "__main__":
    print("🚀 MongoDB Atlas Connection Test")
    print("=" * 50)
    
    # Check if URL has been updated
    if "YOUR_PASSWORD" in MONGO_URL or "xxxxx" in MONGO_URL:
        print("⚠️  Please update the MONGO_URL variable with your actual connection string")
        print("   Then run this script again")
    else:
        asyncio.run(test_connection())
