#!/usr/bin/env python3
"""
Simple direct test of gitingest command to debug encoding issues.
"""

import subprocess
import sys

def test_direct_gitingest():
    """Test gitingest directly with a simple repo"""
    
    print("🧪 Testing gitingest directly...")
    
    # Test with a very simple repo
    repo_url = "https://github.com/octocat/Hello-World"
    
    try:
        # Simple gitingest command
        cmd = ['gitingest', repo_url, '--output', '-']
        
        print(f"🔧 Running: {' '.join(cmd)}")
        
        # Try with UTF-8 encoding
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"📊 Return code: {result.returncode}")
        print(f"📏 Stdout length: {len(result.stdout)} chars")
        print(f"📏 Stderr length: {len(result.stderr)} chars")
        
        if result.returncode == 0:
            print("✅ Success! Here's the first 500 chars of output:")
            print("-" * 50)
            print(result.stdout[:500])
            print("-" * 50)
            if len(result.stdout) > 500:
                print(f"... and {len(result.stdout) - 500} more characters")
        else:
            print("❌ Failed!")
            print("STDERR:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
    except Exception as e:
        print(f"💥 Error: {e}")

def test_gitingest_to_file():
    """Test gitingest with file output instead of stdout"""
    
    print("\n🧪 Testing gitingest with file output...")
    
    repo_url = "https://github.com/octocat/Hello-World"
    output_file = "test_output.txt"
    
    try:
        # Output to file instead of stdout
        cmd = ['gitingest', repo_url, '--output', output_file]
        
        print(f"🔧 Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"📊 Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ Success! Checking output file...")
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"📏 File size: {len(content)} chars")
                    print("📄 First 500 chars:")
                    print("-" * 50)
                    print(content[:500])
                    print("-" * 50)
                    
                # Clean up
                import os
                os.remove(output_file)
                print("🧹 Cleaned up output file")
                
            except Exception as e:
                print(f"❌ Error reading output file: {e}")
        else:
            print("❌ Failed!")
            print("STDERR:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    test_direct_gitingest()
    test_gitingest_to_file()