#!/usr/bin/env python3
"""
Test gitingest and save the output to see the generated files
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

# Add services to path
sys.path.append(str(Path(__file__).parent))

from services.gitingest_processor import GitingestProcessor, AuthConfig, ProcessingConfig


async def test_and_save_output():
    """Test gitingest and save the structured output to files"""
    
    print("🧪 Testing gitingest and saving output files...")
    
    # Create output directory
    output_dir = Path("gitingest_outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Test repositories
    test_repos = [
        "https://github.com/octocat/Hello-World",
        "https://github.com/github/gitignore"
    ]
    
    # Create processor
    config = ProcessingConfig(
        max_file_size=1024 * 1024,
        timeout=60,
        include_patterns=["*.py", "*.md", "*.txt", "*.json", "*.yml", "*.yaml", "README*", "LICENSE*"],
        exclude_patterns=[".git", "node_modules", "__pycache__"]
    )
    
    processor = GitingestProcessor(config)
    auth_config = AuthConfig(token=None)
    
    for i, repo_url in enumerate(test_repos, 1):
        print(f"\n📁 Processing {i}: {repo_url}")
        
        try:
            result = await processor.process_repository(repo_url, auth_config)
            
            if result.success:
                repo = result.structured_repo
                repo_name = repo_url.split('/')[-1]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                print(f"✅ Success! Files processed: {len(repo.files)}")
                
                # Save raw gitingest output
                raw_file = output_dir / f"{repo_name}_raw_{timestamp}.txt"
                with open(raw_file, 'w', encoding='utf-8') as f:
                    f.write(repo.raw_output)
                print(f"📄 Raw output saved to: {raw_file}")
                
                # Save structured data as JSON
                structured_data = {
                    "repo_url": repo.repo_url,
                    "processed_at": repo.gitingest_metadata.processed_at,
                    "total_files": len(repo.files),
                    "total_size": repo.gitingest_metadata.total_size,
                    "language_stats": repo.language_stats,
                    "file_hierarchy": repo.file_hierarchy,
                    "files": {
                        path: {
                            "content": block.content,
                            "language": block.language,
                            "line_count": block.line_count,
                            "size_bytes": block.size_bytes,
                            "file_type": block.file_type
                        }
                        for path, block in repo.files.items()
                    }
                }
                
                json_file = output_dir / f"{repo_name}_structured_{timestamp}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(structured_data, f, indent=2, ensure_ascii=False)
                print(f"📊 Structured data saved to: {json_file}")
                
                # Save individual files
                files_dir = output_dir / f"{repo_name}_files_{timestamp}"
                files_dir.mkdir(exist_ok=True)
                
                for file_path, block in repo.files.items():
                    # Create safe filename
                    safe_filename = file_path.replace('/', '_').replace('\\', '_')
                    if not safe_filename:
                        safe_filename = "root_file"
                    
                    file_output = files_dir / f"{safe_filename}.txt"
                    with open(file_output, 'w', encoding='utf-8') as f:
                        f.write(f"# File: {file_path}\n")
                        f.write(f"# Language: {block.language}\n")
                        f.write(f"# Lines: {block.line_count}\n")
                        f.write(f"# Size: {block.size_bytes} bytes\n")
                        f.write(f"# Type: {block.file_type}\n")
                        f.write("# " + "="*50 + "\n\n")
                        f.write(block.content)
                
                print(f"📁 Individual files saved to: {files_dir}")
                print(f"   Files: {list(repo.files.keys())}")
                
            else:
                print(f"❌ Failed: {result.error}")
                
        except Exception as e:
            print(f"💥 Error: {e}")
    
    print(f"\n🏁 All outputs saved to: {output_dir.absolute()}")
    print("📋 Generated files:")
    for file in sorted(output_dir.rglob("*")):
        if file.is_file():
            print(f"   {file.relative_to(output_dir)}")


if __name__ == "__main__":
    asyncio.run(test_and_save_output())