#!/usr/bin/env python3
"""
Startup script for debugging environment and connection issues
"""

import os
import asyncio
from dotenv import load_dotenv

async def test_startup():
    """Test startup sequence"""
    print("🚀 Testing startup sequence...")
    
    # 1. Test environment variables
    print("\n1️⃣ Testing environment variables...")
    load_dotenv()
    
    mongo_url = os.getenv("MONGO_URL")
    if mongo_url:
        print(f"   ✅ MONGO_URL is set: {mongo_url[:50]}...")
    else:
        print("   ❌ MONGO_URL is NOT set")
        print("   🔧 Please set MONGO_URL in Render environment variables")
        return False
    
    # 2. Test MongoDB connection
    print("\n2️⃣ Testing MongoDB connection...")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        client = AsyncIOMotorClient(mongo_url)
        await client.admin.command('ping')
        print("   ✅ MongoDB connection successful")
        client.close()
    except Exception as e:
        print(f"   ❌ MongoDB connection failed: {e}")
        print("   🔧 Please check your MongoDB Atlas connection string")
        return False
    
    # 3. Test imports
    print("\n3️⃣ Testing imports...")
    try:
        from routes import evals, universities, users
        print("   ✅ All route imports successful")
    except Exception as e:
        print(f"   ❌ Route import failed: {e}")
        return False
    
    print("\n✅ All startup tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_startup())
    if success:
        print("\n🎉 Ready to start the application!")
    else:
        print("\n❌ Startup tests failed. Please fix the issues above.")
        exit(1)
