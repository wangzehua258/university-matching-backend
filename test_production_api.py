#!/usr/bin/env python3
"""
生产环境API测试脚本
测试Render部署的API是否正常工作
"""

import requests
import json

# 你的生产环境URL
PRODUCTION_URL = "https://university-matching-backend.onrender.com"

def test_production_api():
    """测试生产环境API"""
    
    print("🧪 开始测试生产环境API...")
    print(f"生产环境URL: {PRODUCTION_URL}")
    print("-" * 60)
    
    # 测试根端点
    print("1. 测试根端点 /")
    try:
        response = requests.get(f"{PRODUCTION_URL}/", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应: {response.json()}")
        else:
            print(f"   响应: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⏰ 请求超时")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    
    # 测试健康检查
    print("2. 测试健康检查 /health")
    try:
        response = requests.get(f"{PRODUCTION_URL}/health", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应: {response.json()}")
        else:
            print(f"   响应: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⏰ 请求超时")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    
    # 测试大学列表
    print("3. 测试大学列表 /api/universities")
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/universities", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   返回大学数量: {len(data)}")
            if data:
                print(f"   第一所大学: {data[0]['name']}")
        else:
            print(f"   响应: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⏰ 请求超时")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    
    # 测试国家列表
    print("4. 测试国家列表 /api/universities/countries/list")
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/universities/countries/list", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   返回国家数量: {len(data.get('countries', []))}")
            print(f"   国家列表: {data.get('countries', [])}")
        else:
            print(f"   响应: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⏰ 请求超时")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()
    
    # 测试专业列表
    print("5. 测试专业列表 /api/universities/strengths/list")
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/universities/strengths/list", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   返回专业数量: {len(data.get('strengths', []))}")
            print(f"   专业列表: {data.get('strengths', [])[:5]}...")
        else:
            print(f"   响应: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⏰ 请求超时")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("-" * 60)
    print("✅ 生产环境API测试完成")

if __name__ == "__main__":
    test_production_api()
