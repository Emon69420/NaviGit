#!/usr/bin/env python3
"""
Quick test to verify your GitHub token works
"""

import requests

def test_github_token():
    """Test if your GitHub token works"""
    print("🔑 GitHub Token Tester")
    print("=" * 30)
    
    # Get token from user
    token = input("Paste your GitHub token here: ").strip()
    
    if not token:
        print("❌ No token provided!")
        return
    
    if not token.startswith('ghp_'):
        print("⚠️  Warning: Token should start with 'ghp_'")
    
    print("\n🔍 Testing token...")
    
    # Test the token
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # Test 1: Get user info
        response = requests.get('https://api.github.com/user', headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Token valid!")
            print(f"   User: {user_data.get('login')}")
            print(f"   Name: {user_data.get('name', 'Not set')}")
            print(f"   Email: {user_data.get('email', 'Not public')}")
            
            # Test 2: Check rate limits
            rate_response = requests.get('https://api.github.com/rate_limit', headers=headers)
            if rate_response.status_code == 200:
                rate_data = rate_response.json()
                core = rate_data['resources']['core']
                print(f"\n📊 Rate Limits:")
                print(f"   Limit: {core['limit']} requests/hour")
                print(f"   Remaining: {core['remaining']}")
                print(f"   Used: {core['used']}")
            
            # Test 3: Access your repository
            print(f"\n🔍 Testing repository access...")
            repo_response = requests.get('https://api.github.com/repos/Emon69420/HazMapApp', headers=headers)
            
            if repo_response.status_code == 200:
                repo_data = repo_response.json()
                print(f"✅ Repository accessible!")
                print(f"   Name: {repo_data['full_name']}")
                print(f"   Private: {repo_data['private']}")
                print(f"   Size: {repo_data['size']} KB")
                
                print(f"\n🎉 Token is working perfectly!")
                print(f"💾 Save this token: {token}")
                
            else:
                print(f"❌ Repository access failed: {repo_response.status_code}")
                
        elif response.status_code == 401:
            print("❌ Token is invalid or expired")
        elif response.status_code == 403:
            print("❌ Token doesn't have required permissions")
        else:
            print(f"❌ Unexpected error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing token: {e}")

if __name__ == "__main__":
    test_github_token()
    
    print("\n💡 Next steps:")
    print("1. If token works: Run 'python test_with_token.py'")
    print("2. If token fails: Check permissions and regenerate")
    print("3. Keep your token safe - don't share it!")