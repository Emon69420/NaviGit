#!/usr/bin/env python3
"""
Test with GitHub token to bypass rate limits
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def login_with_token():
    """Login with GitHub token first"""
    # Replace with your actual GitHub token
    github_token = input("Enter your GitHub Personal Access Token: ").strip()
    
    if not github_token:
        print("❌ No token provided")
        return False
    
    print("🔐 Logging in with GitHub token...")
    
    url = f"{BASE_URL}/auth/github/login"
    data = {"token": github_token}
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Logged in as: {result['user']['login']}")
        return True
    else:
        print(f"❌ Login failed: {response.json()}")
        return False

def test_deep_analysis_with_auth():
    """Test deep analysis with authentication"""
    print("\n🔍 Testing deep analysis with authentication...")
    
    url = f"{BASE_URL}/api/repositories/deep-analyze"
    data = {
        "url": "https://github.com/Emon69420/HazMapApp",
        "max_file_size": 512 * 1024
    }
    
    # Use session to maintain login
    session = requests.Session()
    
    response = session.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Deep analysis successful!")
        
        if 'processing_time' in result:
            timing = result['processing_time']
            print(f"⏱️  Processing time: {timing['formatted']}")
        
        stats = result['deep_analysis']['structure']['processing_stats']
        print(f"📊 Files processed: {stats['processed']}")
        
    else:
        print(f"❌ Error: {response.json()}")

if __name__ == "__main__":
    print("🚀 Testing with GitHub Authentication")
    print("=" * 50)
    
    if login_with_token():
        test_deep_analysis_with_auth()
    else:
        print("\n💡 To get a GitHub token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Generate new token (classic)")
        print("3. Select 'repo' scope")
        print("4. Copy the token and paste it here")