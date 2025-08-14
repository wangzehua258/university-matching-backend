#!/usr/bin/env python3
"""
Script to run backend tests with proper configuration.
"""

import subprocess
import sys
import os

def run_tests():
    """Run the test suite."""
    print("🚀 Starting backend tests...")
    
    # Install test dependencies if not already installed
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed/updated")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    
    # Run tests with coverage
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--cov=.", 
            "--cov-report=term-missing",
            "--cov-report=html"
        ], check=False)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
        
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)