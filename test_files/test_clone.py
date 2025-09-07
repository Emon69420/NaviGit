#!/usr/bin/env python3
"""
Test script for repository cloning functionality
"""

import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:5000"

def test_clone_repository():
    """Test cloning a repository"""
    print("🔄 Testing repository cloning...")
    print("=" * 50)
    
    url = f"{BASE_URL}/api/repositories/clone"
    data = {
        "url": "https://github.com/Emon69420/HazMapApp",
        "target_dir": "./my_repos"
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Clone successful!")
        print(f"📁 Clone path: {result['clone_path']}")
        print(f"📊 Total files: {result['stats']['total_files']}")
        print(f"📂 Total directories: {result['stats']['total_directories']}")
        print(f"💾 Size: {result['stats']['size_bytes']} bytes")
        print(f"🔤 Languages detected:")
        for lang, count in result['stats']['languages'].items():
            print(f"   - {lang}: {count} files")
        
        # Check if directory actually exists
        clone_path = Path(result['clone_path'])
        if clone_path.exists():
            print(f"✅ Directory exists: {clone_path}")
            
            # List some files
            files = list(clone_path.rglob('*'))[:10]
            print(f"📄 Sample files:")
            for file in files:
                if file.is_file():
                    print(f"   - {file.relative_to(clone_path)}")
        else:
            print(f"❌ Directory not found: {clone_path}")
            
    else:
        print(f"❌ Clone failed: {response.json()}")
    
    print()

def test_clone_and_analyze():
    """Test clone and analyze in one operation"""
    print("🔍 Testing clone and analyze...")
    print("=" * 50)
    
    url = f"{BASE_URL}/api/repositories/clone-and-analyze"
    data = {
        "url": "https://github.com/Emon69420/HazMapApp",
        "target_dir": "./my_repos",
        "max_file_size": 512 * 1024,  # 512KB limit
        "cleanup_after": False  # Keep the repository for inspection
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        # Clone info
        clone_info = result['clone_info']
        print(f"✅ Clone successful!")
        print(f"📁 Clone path: {clone_info['clone_path']}")
        print(f"⏰ Cloned at: {clone_info['cloned_at']}")
        
        # Analysis info
        analysis = result['analysis']
        stats = analysis['processing_stats']
        
        print(f"\n📈 Analysis Results:")
        print(f"  ✅ Files processed: {stats['processed']}")
        print(f"  ⚠️  Files skipped (too large): {stats['skipped_large']}")
        print(f"  🚫 Files skipped (binary): {stats['skipped_binary']}")
        print(f"  ❌ Errors: {stats['errors']}")
        
        # Repository stats
        repo_stats = analysis['stats']
        print(f"\n📊 Repository Statistics:")
        print(f"  📄 Total files: {repo_stats['total_files']}")
        print(f"  📂 Total directories: {repo_stats['total_directories']}")
        print(f"  💾 Size: {repo_stats['size_bytes']} bytes")
        
        # Languages
        if repo_stats['languages']:
            print(f"\n🔤 Languages detected:")
            for lang, count in sorted(repo_stats['languages'].items(), key=lambda x: x[1], reverse=True):
                print(f"   - {lang}: {count} files")
        
        # Show some processed files
        files_with_content = analysis['files_with_content'][:5]
        print(f"\n📄 Sample processed files:")
        for file_info in files_with_content:
            print(f"   - {file_info['path']} ({file_info['lines']} lines, {file_info['language'] or 'Unknown'})")
        
        if len(analysis['files_with_content']) > 5:
            print(f"   ... and {len(analysis['files_with_content']) - 5} more files")
        
        # Save detailed results
        output_file = "clone_analysis_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full results saved to: {output_file}")
        
    else:
        print(f"❌ Clone and analyze failed: {response.json()}")
    
    print()

def test_performance_comparison():
    """Compare API vs Clone performance"""
    print("⚡ Performance Comparison: API vs Clone")
    print("=" * 50)
    
    import time
    
    # Test API approach
    print("Testing API approach...")
    start_time = time.time()
    
    api_url = f"{BASE_URL}/api/repositories/deep-analyze"
    api_data = {
        "url": "https://github.com/octocat/Hello-World",  # Small repo for fair comparison
        "max_file_size": 1024 * 1024
    }
    
    api_response = requests.post(api_url, json=api_data)
    api_time = time.time() - start_time
    
    print(f"API approach: {api_time:.2f} seconds")
    
    # Test Clone approach
    print("Testing Clone approach...")
    start_time = time.time()
    
    clone_url = f"{BASE_URL}/api/repositories/clone-and-analyze"
    clone_data = {
        "url": "https://github.com/octocat/Hello-World",
        "cleanup_after": True  # Clean up after test
    }
    
    clone_response = requests.post(clone_url, json=clone_data)
    clone_time = time.time() - start_time
    
    print(f"Clone approach: {clone_time:.2f} seconds")
    
    # Compare results
    if api_response.status_code == 200 and clone_response.status_code == 200:
        api_files = len(api_response.json()['deep_analysis']['structure']['files_with_content'])
        clone_files = len(clone_response.json()['analysis']['files_with_content'])
        
        print(f"\n📊 Results:")
        print(f"API files processed: {api_files}")
        print(f"Clone files processed: {clone_files}")
        print(f"Speed improvement: {api_time/clone_time:.1f}x faster" if clone_time < api_time else f"API was {clone_time/api_time:.1f}x faster")
    
    print()

if __name__ == "__main__":
    print("🚀 Testing Repository Cloning System")
    print("=" * 60)
    
    try:
        # Check if git is available
        import subprocess
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Git is not installed or not in PATH")
            print("Please install Git to use cloning functionality")
            exit(1)
        else:
            print(f"✅ Git available: {result.stdout.strip()}")
            print()
        
        test_clone_repository()
        test_clone_and_analyze()
        test_performance_comparison()
        
        print("🎉 All cloning tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Flask server.")
        print("Make sure the server is running with: python app.py")
    except Exception as e:
        print(f"❌ Error: {e}")