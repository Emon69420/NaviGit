#!/usr/bin/env python3
"""
Quick test script for gitingest integration with public repositories.
This tests the GitingestProcessor without requiring authentication.
"""

import asyncio
import sys
from pathlib import Path

# Add services to path
sys.path.append(str(Path(__file__).parent))

from services.gitingest_processor import GitingestProcessor, AuthConfig, ProcessingConfig


async def test_public_repo():
    """Test gitingest with a public repository"""
    
    # Test with small, well-known public repos
    test_repos = [
        "https://github.com/octocat/Hello-World",  # GitHub's official test repo
        "https://github.com/github/gitignore",     # Collection of gitignore templates
        "https://github.com/torvalds/linux"       # Large repo (will be limited by our filters)
    ]
    
    print("🧪 Testing GitingestProcessor with public repositories...")
    print("=" * 60)
    
    # Create processor with default config
    config = ProcessingConfig(
        max_file_size=1024 * 1024,  # 1MB limit for testing
        timeout=60,  # 1 minute timeout for testing
        include_patterns=["*.py", "*.md", "*.txt", "*.json", "*.yml", "*.yaml", "README*", "LICENSE*"],
        exclude_patterns=[".git", "node_modules", "__pycache__"]
    )
    
    processor = GitingestProcessor(config)
    
    # Test without authentication (public repos only)
    auth_config = AuthConfig(token=None)
    
    for i, repo_url in enumerate(test_repos, 1):
        print(f"\n📁 Test {i}: {repo_url}")
        print("-" * 40)
        
        try:
            # Test repository validation first
            print("🔍 Validating repository...")
            validation = await processor.validate_repository(repo_url)
            
            if not validation.valid:
                print(f"❌ Validation failed: {validation.error}")
                continue
            
            print("✅ Repository validation passed")
            
            # Test gitingest processing
            print("⚙️  Processing with gitingest...")
            result = await processor.process_repository(repo_url, auth_config)
            
            if result.success:
                print("✅ Gitingest processing successful!")
                
                # Display results
                repo = result.structured_repo
                print(f"📊 Results:")
                print(f"   • Files processed: {len(repo.files)}")
                print(f"   • Total size: {repo.gitingest_metadata.total_size:,} bytes")
                print(f"   • Languages found: {list(repo.language_stats.keys())}")
                
                # Debug: show raw output length
                print(f"   • Raw output length: {len(repo.raw_output)} chars")
                
                # Show first few files
                print(f"   • Sample files:")
                if repo.files:
                    for i, (path, block) in enumerate(list(repo.files.items())[:3]):
                        print(f"     - {path} ({block.language}, {block.line_count} lines)")
                    
                    if len(repo.files) > 3:
                        print(f"     ... and {len(repo.files) - 3} more files")
                else:
                    print("     (No files found - check parsing logic)")
                
                # Show processing stats
                if result.processing_stats:
                    stats = result.processing_stats
                    print(f"   • Processing time: {stats['processing_time_seconds']:.2f}s")
                
            else:
                print(f"❌ Processing failed: {result.error}")
                
        except Exception as e:
            print(f"💥 Unexpected error: {str(e)}")
        
        print()
    
    print("🏁 Testing complete!")


async def test_gitingest_command():
    """Test if gitingest command is available"""
    print("🔧 Testing gitingest installation...")
    
    import subprocess
    
    try:
        # Test gitingest help (since --version doesn't exist)
        result = subprocess.run(['gitingest', '--help'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Gitingest is installed and working!")
            # Try to extract version from help output if available
            if "gitingest" in result.stdout.lower():
                print("📋 Gitingest help command works correctly")
            return True
        else:
            print(f"❌ Gitingest command failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Gitingest is not installed or not in PATH")
        print("💡 Install with: pip install gitingest")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Gitingest command timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing gitingest: {str(e)}")
        return False


async def main():
    """Main test function"""
    print("🚀 GitIngest Integration Test")
    print("=" * 60)
    
    # First check if gitingest is installed
    gitingest_available = await test_gitingest_command()
    
    if not gitingest_available:
        print("\n⚠️  Cannot proceed without gitingest installed.")
        print("📦 Install gitingest first:")
        print("   pip install gitingest")
        return
    
    print()
    
    # Test with public repositories
    await test_public_repo()


if __name__ == "__main__":
    asyncio.run(main())