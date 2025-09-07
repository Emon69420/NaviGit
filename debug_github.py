#!/usr/bin/env python3
"""
Debug script to check GitHub API status and rate limits
"""

import requests
import json

def check_github_api():
    """Check GitHub API status and rate limits"""
    print("🔍 Debugging GitHub API access...")
    print("=" * 50)
    
    # Check API rate limit status
    print("1. Checking GitHub API rate limits...")
    try:
        response = requests.get("https://api.github.com/rate_limit")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            rate_data = response.json()
            core = rate_data['resources']['core']
            print(f"✅ Rate limit status:")
            print(f"   Limit: {core['limit']}")
            print(f"   Used: {core['used']}")
            print(f"   Remaining: {core['remaining']}")
            print(f"   Reset time: {core['reset']}")
            
            if core['remaining'] == 0:
                print("❌ RATE LIMIT EXCEEDED! This is the issue.")
                import datetime
                reset_time = datetime.datetime.fromtimestamp(core['reset'])
                print(f"   Rate limit resets at: {reset_time}")
            else:
                print("✅ Rate limit OK")
        else:
            print(f"❌ Failed to check rate limits: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking rate limits: {e}")
    
    print()
    
    # Test direct repository access
    print("2. Testing direct repository access...")
    try:
        repo_url = "https://api.github.com/repos/Emon69420/HazMapApp"
        response = requests.get(repo_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            repo_data = response.json()
            print(f"✅ Repository accessible:")
            print(f"   Name: {repo_data['full_name']}")
            print(f"   Private: {repo_data['private']}")
            print(f"   Size: {repo_data['size']} KB")
        elif response.status_code == 403:
            print("❌ 403 Forbidden - Likely rate limited")
            print("Response headers:")
            for header, value in response.headers.items():
                if 'rate' in header.lower() or 'limit' in header.lower():
                    print(f"   {header}: {value}")
        elif response.status_code == 404:
            print("❌ 404 Not Found - Repository doesn't exist or is private")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error testing repository: {e}")
    
    print()
    
    # Test with a known public repository
    print("3. Testing with known public repository (octocat/Hello-World)...")
    try:
        repo_url = "https://api.github.com/repos/octocat/Hello-World"
        response = requests.get(repo_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Known public repo accessible - API is working")
        elif response.status_code == 403:
            print("❌ Even known public repo is forbidden - definitely rate limited")
        else:
            print(f"❌ Unexpected status for known repo: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing known repo: {e}")

def check_flask_server():
    """Check if Flask server is responding"""
    print("\n4. Testing Flask server...")
    try:
        response = requests.get("http://localhost:5000/auth/status")
        print(f"Flask server status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Flask server is running")
        else:
            print("❌ Flask server issue")
    except requests.exceptions.ConnectionError:
        print("❌ Flask server not running - start with: python app.py")
    except Exception as e:
        print(f"❌ Flask server error: {e}")

if __name__ == "__main__":
    check_github_api()
    check_flask_server()
    
    print("\n💡 Solutions:")
    print("1. If rate limited: Wait for reset time or use GitHub token")
    print("2. If server not running: python app.py")
    print("3. If repo changed: Check repository URL and permissions")