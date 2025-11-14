#!/usr/bin/env python3
"""
简单的 MongoDB 连接测试脚本
用于诊断连接问题
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
import socket
import time

def test_dns_resolution(hostname):
    """测试DNS解析"""
    print(f"🔍 测试DNS解析: {hostname}")
    try:
        import socket
        ip = socket.gethostbyname(hostname)
        print(f"   ✅ DNS解析成功: {hostname} -> {ip}")
        return True
    except Exception as e:
        print(f"   ❌ DNS解析失败: {e}")
        return False

def test_network_connectivity(hostname, port=27017):
    """测试网络连通性"""
    print(f"🔍 测试网络连通性: {hostname}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()
        if result == 0:
            print(f"   ✅ 端口 {port} 可访问")
            return True
        else:
            print(f"   ❌ 端口 {port} 不可访问 (错误码: {result})")
            return False
    except Exception as e:
        print(f"   ⚠️  无法测试端口连通性: {e}")
        print(f"   注意: mongodb+srv 使用动态端口，此测试可能不准确")
        return None

def test_mongodb_connection(mongo_url):
    """测试MongoDB连接"""
    print(f"\n🔗 测试 MongoDB 连接...")
    print(f"   URL: {mongo_url[:60]}...")
    
    # 提取主机名
    if "mongodb+srv://" in mongo_url:
        hostname = mongo_url.split("@")[1].split("/")[0]
    elif "mongodb://" in mongo_url:
        hostname = mongo_url.split("@")[1].split("/")[0].split(":")[0]
    else:
        hostname = None
    
    if hostname:
        print(f"   主机名: {hostname}")
        test_dns_resolution(hostname)
    
    # 测试连接（短超时）
    print(f"\n   尝试连接（10秒超时）...")
    try:
        client = MongoClient(
            mongo_url,
            serverSelectionTimeoutMS=10000,  # 10秒超时
            connectTimeoutMS=5000,  # 5秒连接超时
            socketTimeoutMS=5000,  # 5秒socket超时
        )
        start_time = time.time()
        client.admin.command('ping')
        elapsed = time.time() - start_time
        print(f"   ✅ 连接成功！耗时: {elapsed:.2f}秒")
        return True
    except ServerSelectionTimeoutError as e:
        print(f"   ❌ 连接超时: {e}")
        print(f"   这通常意味着:")
        print(f"   1. MongoDB Atlas 网络访问列表未允许你的 IP")
        print(f"   2. 防火墙阻止了连接")
        print(f"   3. MongoDB 集群不可用")
        return False
    except ConfigurationError as e:
        print(f"   ❌ 配置错误: {e}")
        print(f"   请检查连接字符串格式")
        return False
    except Exception as e:
        print(f"   ❌ 连接失败: {type(e).__name__}: {e}")
        return False
    finally:
        try:
            client.close()
        except:
            pass

def main():
    print("=" * 60)
    print("MongoDB 连接诊断工具")
    print("=" * 60)
    
    # 获取连接字符串
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        print("❌ MONGO_URL 环境变量未设置")
        print("\n请设置环境变量:")
        print('export MONGO_URL="your_connection_string"')
        return
    
    # 测试连接
    success = test_mongodb_connection(mongo_url)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 连接测试通过！")
        print("\n如果 init_database.py 仍然失败，可能是:")
        print("1. 超时时间设置太短")
        print("2. 数据库操作权限问题")
    else:
        print("❌ 连接测试失败")
        print("\n故障排查步骤:")
        print("1. 检查 MongoDB Atlas Network Access:")
        print("   - 登录 https://cloud.mongodb.com")
        print("   - 进入你的集群 -> Network Access")
        print("   - 确保有 0.0.0.0/0 (允许所有IP) 或添加 Render 的 IP")
        print()
        print("2. 检查 MongoDB Atlas 集群状态:")
        print("   - 确认集群正在运行")
        print("   - 检查是否有维护或故障")
        print()
        print("3. 验证连接字符串:")
        print("   - 用户名和密码是否正确")
        print("   - 数据库名称是否正确")
        print("   - 连接字符串格式是否正确")
        print()
        print("4. 检查 Render 网络:")
        print("   - Render 服务是否正常运行")
        print("   - 是否有网络限制")
    print("=" * 60)

if __name__ == "__main__":
    main()
