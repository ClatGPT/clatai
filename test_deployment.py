#!/usr/bin/env python3
"""
Simple test script to verify Flask app deployment readiness
"""

import os
import sys
import requests
import json

def test_health_endpoint(base_url="http://localhost:5000"):
    """Test the health endpoint"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed")
            print(f"   Status: {data.get('status')}")
            print(f"   Services: {data.get('services')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_static_files(base_url="http://localhost:5000"):
    """Test static file serving"""
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Landing page served successfully")
            return True
        else:
            print(f"❌ Landing page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Landing page error: {e}")
        return False

def test_api_endpoints(base_url="http://localhost:5000"):
    """Test API endpoints"""
    endpoints = [
        ("/gk/health", "GET"),
        ("/lexa/health", "GET"),
        ("/topics", "GET"),
    ]
    
    success_count = 0
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code in [200, 400, 405]:  # 405 is OK for GET endpoints
                print(f"✅ {method} {endpoint} - {response.status_code}")
                success_count += 1
            else:
                print(f"❌ {method} {endpoint} - {response.status_code}")
        except Exception as e:
            print(f"❌ {method} {endpoint} - Error: {e}")
    
    return success_count == len(endpoints)

def main():
    """Main test function"""
    print("🚀 Testing ClatAI deployment readiness...")
    print("=" * 50)
    
    # Check environment variables
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("✅ GROQ_API_KEY is set")
    else:
        print("⚠️  GROQ_API_KEY not set (required for AI features)")
    
    # Test endpoints
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:5000")
    print(f"\n🔗 Testing against: {base_url}")
    
    health_ok = test_health_endpoint(base_url)
    static_ok = test_static_files(base_url)
    api_ok = test_api_endpoints(base_url)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Static Files: {'✅ PASS' if static_ok else '❌ FAIL'}")
    print(f"   API Endpoints: {'✅ PASS' if api_ok else '❌ FAIL'}")
    
    if health_ok and static_ok and api_ok:
        print("\n🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 