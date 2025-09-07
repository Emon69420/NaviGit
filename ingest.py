#!/usr/bin/env python3
"""
Simple gitingest integration - just get the structured text output.
This is how gitingest is meant to be used!
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SimpleGitingestProcessor:
    """
    Simple processor that uses gitingest as intended - get structured text output.
    No complex parsing needed, gitingest already does the hard work!
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize with optional GitHub token for private repos.
        
        Args:
            github_token: GitHub Personal Access Token for private repos
        """
        self.github_token = github_token
    
    def process_repository(self, repo_url: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process repository with gitingest and return the structured text.
        
        Args:
            repo_url: GitHub repository URL
            output_file: Optional output file path, uses temp file if None
            
        Returns:
            Dict with success status, structured_text, and metadata
        """
        temp_file = None
        
        try:
            # Create output file
            if output_file is None:
                fd, temp_file = tempfile.mkstemp(suffix='.txt', prefix='gitingest_')
                os.close(fd)
                output_file = temp_file
            
            # Build gitingest command
            cmd = ['gitingest', repo_url, '--output', output_file]
            
            # Add token if provided
            if self.github_token:
                cmd.extend(['--token', self.github_token])
            
            # Set up environment
            env = os.environ.copy()
            if self.github_token:
                env['GITHUB_TOKEN'] = self.github_token
            
            logger.info(f"Processing repository: {repo_url}")
            
            # Execute gitingest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown gitingest error"
                return {
                    'success': False,
                    'error': f"Gitingest failed: {error_msg}",
                    'repo_url': repo_url
                }
            
            # Read the structured output
            with open(output_file, 'r', encoding='utf-8', errors='replace') as f:
                structured_text = f.read()
            
            # Extract metadata from stderr (gitingest prints summary there)
            metadata = self._extract_metadata(result.stderr, repo_url)
            
            return {
                'success': True,
                'structured_text': structured_text,
                'metadata': metadata,
                'repo_url': repo_url
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "Gitingest execution timed out (5 minutes)",
                'repo_url': repo_url
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': "Gitingest is not installed or not in PATH",
                'repo_url': repo_url
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Processing failed: {str(e)}",
                'repo_url': repo_url
            }
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
    
    def _extract_metadata(self, stderr_output: str, repo_url: str) -> Dict[str, Any]:
        """Extract metadata from gitingest stderr output"""
        metadata = {
            'repo_url': repo_url,
            'files_analyzed': 0,
            'estimated_tokens': 0,
            'commit': None
        }
        
        if not stderr_output:
            return metadata
        
        lines = stderr_output.split('\n')
        
        for line in lines:
            if 'Files analyzed:' in line:
                try:
                    metadata['files_analyzed'] = int(line.split('Files analyzed:')[1].strip())
                except (ValueError, IndexError):
                    pass
            elif 'Estimated tokens:' in line:
                try:
                    token_str = line.split('Estimated tokens:')[1].strip()
                    # Handle formats like "29" or "1.2k"
                    if 'k' in token_str:
                        metadata['estimated_tokens'] = int(float(token_str.replace('k', '')) * 1000)
                    else:
                        metadata['estimated_tokens'] = int(token_str)
                except (ValueError, IndexError):
                    pass
            elif 'Commit:' in line:
                try:
                    metadata['commit'] = line.split('Commit:')[1].strip()
                except IndexError:
                    pass
        
        return metadata
    
    def save_structured_output(self, repo_url: str, output_dir: str = "gitingest_outputs") -> Dict[str, Any]:
        """
        Process repository and save structured output to a file.
        
        Args:
            repo_url: GitHub repository URL
            output_dir: Directory to save output files
            
        Returns:
            Dict with success status and file path
        """
        try:
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Generate filename from repo URL
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            owner = repo_url.split('/')[-2]
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            
            output_file = f"{output_dir}/{owner}_{repo_name}_{timestamp}.txt"
            
            # Process repository
            result = self.process_repository(repo_url, output_file)
            
            if result['success']:
                result['output_file'] = output_file
                logger.info(f"Structured output saved to: {output_file}")
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to save output: {str(e)}",
                'repo_url': repo_url
            }


def main():
    """Example usage of SimpleGitingestProcessor"""
    
    # Get GitHub token from environment
    github_token = os.getenv('GITHUB_API_TOKEN') or os.getenv('GITHUB_TOKEN')
    
    # Create processor
    processor = SimpleGitingestProcessor(github_token)
    
    # Test repositories

    repo_url = input("enter link for the repo: ").strip()

    
    print("Gitingestion of the file")
    print("=" * 50)
    

    print(f"\n📁 Processing: {repo_url}")
    print("-" * 40)
        
    # Process and save
    result = processor.save_structured_output(repo_url)
     
    if result['success']:
        print("✅ Success!")
        print(f"📊 Files analyzed: {result['metadata']['files_analyzed']}")
        print(f"🔢 Estimated tokens: {result['metadata']['estimated_tokens']}")
        print(f"💾 Output saved to: {result['output_file']}")
        
        # Show first 200 chars of structured text
        preview = result['structured_text'][:200] + "..." if len(result['structured_text']) > 200 else result['structured_text']
        print(f"📄 Preview:\n{preview}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print("\n Done! Check the gitingest_outputs/ directory for structured text files.")
    print("💡 These files are ready to be fed directly to your AI system!")


if __name__ == "__main__":
    main()