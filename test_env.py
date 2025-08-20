#!/usr/bin/env python3
"""
Test script to verify environment variables are loaded correctly
Run this on Render to debug environment variable issues
"""

import os
from dotenv import load_dotenv

print("🔍 Environment Variable Test")
print("=" * 50)

# Load .env file if it exists
load_dotenv()

# Check key environment variables
key_vars = [
    "MONGO_URL",
    "SECRET_KEY", 
    "OPENAI_API_KEY",
    "WX_APP_ID",
    "WX_APP_SECRET",
    "MOCK_MODE"
]

print("📋 Environment Variables:")
for var in key_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "KEY" in var or "SECRET" in var or "PASSWORD" in var:
            masked_value = value[:8] + "..." if len(value) > 8 else "***"
            print(f"   {var}: {masked_value}")
        else:
            print(f"   {var}: {value}")
    else:
        print(f"   {var}: ❌ NOT SET")

print("\n🌍 All Environment Variables:")
for key, value in os.environ.items():
    if "KEY" in key or "SECRET" in key or "PASSWORD" in key:
        masked_value = value[:8] + "..." if len(value) > 8 else "***"
        print(f"   {key}: {masked_value}")
    else:
        print(f"   {key}: {value}")

print("\n✅ Environment test completed")
