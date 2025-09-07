#!/usr/bin/env python3
"""
Test timing with a very small repository to minimize API calls
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_small_repo_timing():
    """Test with a very small repository"""
    print("🔍 Testing timing with small repository...")
    print("Note: This might still fail due to rate limits")
    
    # Try with a very small, well-known repo
    url = f"{BASE_URL}/api/repositories/deep-analyze"
    data = {
        "url": "https://github.com/octocat/Hello-World",  # Very small repo
        "max_file_size": 1024 * 1024  # 1MB limit
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Analysis successful!")
        
        # Show timing information
        if 'processing_time' in result:
            timing = result['processing_time']
            print(f"\n⏱️  Timing Results:")
            print(f"  🕐 Total time: {timing['formatted']} ({timing['seconds']}s)")
            print(f"  📊 Minutes: {timing['minutes']}")
        
        stats = result['deep_analysis']['structure']['processing_stats']
        print(f"\n📈 Performance:")
        print(f"  ✅ Files processed: {stats['processed']}")
        print(f"  🚀 Files per second: {stats.get('files_per_second', 0)}")
        print(f"  ⏱️  Start: {stats.get('start_time', 'N/A')}")
        print(f"  🏁 End: {stats.get('end_time', 'N/A')}")
        
    else:
        error = response.json()
        if 'rate limited' in error.get('error', '').lower():
            print("❌ Still rate limited. Try one of these:")
            print("1. Use GitHub token: python test_with_token.py")
            print("2. Wait until 00:39:17 for rate limit reset")
        else:
            print(f"❌ Error: {error}")

if __name__ == "__main__":
    test_small_repo_timing()