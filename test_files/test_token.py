#!/usr/bin/env python3
"""
Test script to validate your GitHub token with the Flask API
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_github_token():
    """Test GitHub token authentication"""
    
    # Get token from user
    print("🔑 GitHub Token Tester")
    print("=" * 30)
    
    token = input("Enter your GitHub Personal Access Token: ").strip()
    
    if not token:
        print("❌ No token provided!")
        return
    
    print(f"\n🔍 Testing token: {token[:8]}...")
    
    # Test token with login endpoint
    url = f"{BASE_URL}/auth/github/login"
    data = {"token": token}
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            user = result['user']
            
            print("✅ Token is valid!")
            print(f"👤 User: {user['login']}")
            print(f"📧 Email: {user.get('email', 'Not provided')}")
            print(f"🔐 Scopes: {', '.join(result['scopes'])}")
            
            # Test repository access with token
            print(f"\n🔍 Testing repository access...")
            test_repo_with_token()
            
        else:
            error = response.json()
            print(f"❌ Token validation failed: {error.get('error')}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Flask server.")
        print("Make sure the server is running with: python app.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_repo_with_token():
    """Test repository access with authenticated token"""
    
    # Test with your repository
    url = f"{BASE_URL}/api/repositories/validate"
    data = {"url": "https://github.com/Emon69420/HazMapApp"}
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        repo = result['repository']
        print(f"✅ Repository access successful!")
        print(f"📁 Repo: {repo['full_name']}")
        print(f"🔒 Private: {repo['private']}")
        print(f"⭐ Stars: {repo['stargazers_count']}")
    else:
        print(f"⚠️  Repository access issue: {response.json()}")

def show_token_info():
    """Show information about GitHub tokens"""
    print("\n📋 GitHub Token Information:")
    print("=" * 40)
    print("🔗 Get token at: https://github.com/settings/tokens")
    print("\n📝 Required scopes:")
    print("  ✅ repo (for private repositories)")
    print("  ✅ public_repo (for public repositories)")
    print("  ✅ user:email (for user information)")
    print("\n⚠️  Security tips:")
    print("  • Never share your token publicly")
    print("  • Set appropriate expiration dates")
    print("  • Use environment variables in production")
    print("  • Revoke tokens you no longer need")

if __name__ == "__main__":
    show_token_info()
    test_github_token()