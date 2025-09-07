#!/usr/bin/env python3
"""
Test script for deep repository analysis - fetches all files with their content
"""

import requests
import json
import os

BASE_URL = "http://localhost:5000"

def test_deep_analysis():
    """Test deep analysis of HazMapApp repository"""
    print("🔍 Starting deep analysis of HazMapApp repository...")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/repositories/deep-analyze"
    data = {
        "url": "https://github.com/Redomic/NeuThera-Drug-Discovery-Toolkit",
        "max_file_size": 1024 * 1024  # 512KB limit for demo
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        deep_analysis = result['deep_analysis']
        
        # Repository info
        repo_info = deep_analysis['repository_info']
        print(f"\n📁 Repository: {repo_info['full_name']}")
        print(f"📝 Description: {repo_info['description']}")
        print(f"🔤 Language: {repo_info['language']}")
        print(f"📊 Size: {repo_info['size']} KB")
        print(f"⭐ Stars: {repo_info['stargazers_count']}")
        
        # Structure stats
        structure = deep_analysis['structure']
        stats = structure['processing_stats']
        
        print(f"\n📈 Processing Statistics:")
        print(f"  ✅ Files processed: {stats['processed']}")
        print(f"  ⚠️  Files skipped (too large): {stats['skipped_large']}")
        print(f"  🚫 Files skipped (binary): {stats['skipped_binary']}")
        print(f"  ❌ Errors: {stats['errors']}")
        print(f"  📂 Total directories: {structure['total_directories']}")
        print(f"  📄 Total files: {structure['total_files']}")
        
        # Display timing information
        if 'processing_time' in result:
            timing = result['processing_time']
            print(f"\n⏱️  Performance Metrics:")
            print(f"  🕐 Processing time: {timing['formatted']} ({timing['seconds']}s)")
            print(f"  🚀 Files per second: {stats.get('files_per_second', 0)}")
            print(f"  📊 Average time per file: {round(timing['seconds'] / max(stats['processed'], 1), 3)}s")
        
        # Show directory structure
        print(f"\n📂 Directory Structure:")
        for directory in structure['directories'][:10]:
            print(f"  📁 {directory['path']}")
        if len(structure['directories']) > 10:
            print(f"  ... and {len(structure['directories']) - 10} more directories")
        
        # Show files with content
        print(f"\n📄 Files with Content ({len(structure['files_with_content'])}):")
        for i, file_info in enumerate(structure['files_with_content'][:5]):
            print(f"\n  {i+1}. 📄 {file_info['path']}")
            print(f"     Size: {file_info['size']} bytes")
            print(f"     Lines: {file_info['lines']}")
            print(f"     Extension: {file_info['extension']}")
            
            # Show first few lines of content
            content = file_info['content']
            if content:
                lines = content.split('\n')
                print(f"     Content preview (first 3 lines):")
                for j, line in enumerate(lines[:3]):
                    print(f"       {j+1}: {line[:80]}{'...' if len(line) > 80 else ''}")
            else:
                print(f"     Content: [Empty file]")
        
        if len(structure['files_with_content']) > 5:
            print(f"\n  ... and {len(structure['files_with_content']) - 5} more files with content")
        
        # Show skipped files
        if structure['skipped_files']:
            print(f"\n⚠️  Skipped Files ({len(structure['skipped_files'])}):")
            for skip_info in structure['skipped_files'][:5]:
                reason = skip_info['reason']
                path = skip_info['path']
                if reason == 'file_too_large':
                    print(f"  📏 {path} (too large: {skip_info['size']} bytes)")
                elif reason == 'binary_file':
                    print(f"  🔧 {path} (binary: {skip_info['extension']})")
                else:
                    print(f"  ❌ {path} ({reason})")
            
            if len(structure['skipped_files']) > 5:
                print(f"  ... and {len(structure['skipped_files']) - 5} more skipped files")
        
        # Save detailed results to file
        output_file = "hazmap_deep_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full analysis saved to: {output_file}")
        print(f"📊 Analysis completed at: {result['analyzed_at']}")
        
        if 'processing_time' in result:
            print(f"⚡ Total processing time: {result['processing_time']['formatted']}")
        
    else:
        print(f"❌ Error: {response.json()}")

def test_explore_endpoint():
    """Test the alternative explore endpoint"""
    print("\n🔍 Testing explore endpoint...")
    print("=" * 40)
    
    url = f"{BASE_URL}/api/repositories/Redomic/NeuThera-Drug-Discovery-Toolkit/explore?max_file_size=102400"  # 100KB limit
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        stats = result['deep_analysis']['structure']['processing_stats']
        print(f"✅ Processed {stats['processed']} files")
        print(f"⚠️  Skipped {stats['skipped_large'] + stats['skipped_binary']} files")
    else:
        print(f"❌ Error: {response.json()}")

if __name__ == "__main__":
    try:
        test_deep_analysis()
        test_explore_endpoint()
        
        print("\n🎉 Deep analysis testing completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Flask server.")
        print("Make sure the server is running with: python app.py")
    except Exception as e:
        print(f"❌ Error: {e}")