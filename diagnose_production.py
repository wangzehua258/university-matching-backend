#!/usr/bin/env python3
"""
生产环境问题诊断脚本
检查500错误的可能原因
"""

import requests
import json

# 你的生产环境URL
PRODUCTION_URL = "https://university-matching-backend.onrender.com"

def diagnose_production_issues():
    """诊断生产环境问题"""
    
    print("🔍 开始诊断生产环境问题...")
    print(f"生产环境URL: {PRODUCTION_URL}")
    print("-" * 60)
    
    # 测试根端点
    print("1. 测试根端点 /")
    try:
        response = requests.get(f"{PRODUCTION_URL}/", timeout=15)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ 正常: {response.json()}")
        else:
            print(f"   ❌ 错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    print()
    
    # 测试健康检查
    print("2. 测试健康检查 /health")
    try:
        response = requests.get(f"{PRODUCTION_URL}/health", timeout=15)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 正常: {data}")
            if 'database' in data:
                print(f"   数据库状态: {data['database']}")
        else:
            print(f"   ❌ 错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    print()
    
    # 测试大学列表（有问题的端点）
    print("3. 测试大学列表 /api/universities")
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/universities", timeout=15)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 正常: 返回 {len(data)} 所大学")
        elif response.status_code == 500:
            print(f"   ❌ 500错误: {response.text}")
            print("   💡 这通常是数据库连接问题")
        else:
            print(f"   ❌ 其他错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    print()
    
    # 测试国家列表
    print("4. 测试国家列表 /api/universities/countries/list")
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/universities/countries/list", timeout=15)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 正常: {data}")
        elif response.status_code == 500:
            print(f"   ❌ 500错误: {response.text}")
        else:
            print(f"   ❌ 其他错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    print()
    
    # 测试专业列表
    print("5. 测试专业列表 /api/universities/strengths/list")
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/universities/strengths/list", timeout=15)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 正常: {data}")
        elif response.status_code == 500:
            print(f"   ❌ 500错误: {response.text}")
        else:
            print(f"   ❌ 其他错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    print("-" * 60)
    print("🔍 诊断完成")
    print("\n💡 如果看到500错误，请检查Render日志中的具体错误信息")
    print("💡 通常500错误是由以下原因造成：")
    print("   1. MongoDB连接失败")
    print("   2. 环境变量未正确设置")
    print("   3. 代码执行异常")

if __name__ == "__main__":
    diagnose_production_issues()
