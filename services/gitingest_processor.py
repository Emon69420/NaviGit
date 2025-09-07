"""
GitingestProcessor Service

This service handles gitingest execution and output processing for repository analysis.
It replaces the complex GitHub API streaming approach with gitingest's optimized
text format generation.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import shutil

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """Configuration for repository authentication"""
    token: Optional[str] = None
    auth_method: str = "token"  # token, ssh, https
    

@dataclass
class ProcessingConfig:
    """Configuration for gitingest processing"""
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB default
    respect_gitignore: bool = True
    include_binary_files: bool = False
    timeout: int = 300  # 5 minutes default
    
    def __post_init__(self):
        if self.include_patterns is None:
            self.include_patterns = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.md", "*.json", "*.yaml", "*.yml"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["node_modules", "__pycache__", ".git", "*.pyc", "*.log"]


@dataclass
class GitingestMetadata:
    """Metadata from gitingest processing"""
    processing_time: float
    total_files: int
    total_size: int
    gitingest_version: str
    processed_at: str


@dataclass
class ContentBlock:
    """Represents a content block from gitingest output"""
    file_path: str
    content: str
    language: str
    line_count: int
    size_bytes: int
    file_type: str


@dataclass
class StructuredRepository:
    """Structured representation of repository from gitingest"""
    repo_url: str
    files: Dict[str, ContentBlock]
    file_hierarchy: Dict[str, Any]
    language_stats: Dict[str, int]
    gitingest_metadata: GitingestMetadata
    raw_output: str


@dataclass
class ValidationResult:
    """Result of repository validation"""
    valid: bool
    error: Optional[str] = None
    repo_info: Optional[Dict[str, Any]] = None


@dataclass
class GitingestOutput:
    """Complete output from gitingest processing"""
    success: bool
    structured_repo: Optional[StructuredRepository] = None
    error: Optional[str] = None
    processing_stats: Optional[Dict[str, Any]] = None


class GitingestProcessor:
    """
    Core service that handles gitingest execution and output processing.
    
    This service provides methods to:
    - Process repositories using gitingest
    - Parse gitingest output into structured format
    - Validate repository access
    - Handle authentication and cleanup
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """
        Initialize GitingestProcessor with configuration.
        
        Args:
            config: Processing configuration, uses defaults if None
        """
        self.config = config or ProcessingConfig()
        self.temp_dir = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for gitingest operations"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def process_repository(self, repo_url: str, auth_config: AuthConfig) -> GitingestOutput:
        """
        Process a repository using gitingest to convert it to structured text format.
        
        Args:
            repo_url: URL of the repository to process
            auth_config: Authentication configuration for repository access
            
        Returns:
            GitingestOutput containing structured repository data or error information
        """
        start_time = datetime.now()
        process_id = None
        
        try:
            self.logger.info(f"Starting gitingest processing for repository: {repo_url}")
            
            # Validate repository first
            validation = await self.validate_repository(repo_url)
            if not validation.valid:
                return GitingestOutput(
                    success=False,
                    error=f"Repository validation failed: {validation.error}"
                )
            
            # Create temporary directory for processing
            process_id = self._create_temp_directory()
            
            # Execute gitingest command
            raw_output = await self._execute_gitingest(repo_url, auth_config, process_id)
            
            # Parse gitingest output
            structured_repo = self.parse_gitingest_output(raw_output, repo_url)
            
            # Calculate processing stats
            processing_time = (datetime.now() - start_time).total_seconds()
            processing_stats = {
                'processing_time_seconds': processing_time,
                'files_processed': len(structured_repo.files),
                'total_size_bytes': sum(block.size_bytes for block in structured_repo.files.values()),
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Successfully processed repository {repo_url} in {processing_time:.2f} seconds")
            
            return GitingestOutput(
                success=True,
                structured_repo=structured_repo,
                processing_stats=processing_stats
            )
            
        except Exception as e:
            self.logger.error(f"Error processing repository {repo_url}: {str(e)}")
            return GitingestOutput(
                success=False,
                error=f"Processing failed: {str(e)}"
            )
        finally:
            # Always cleanup temporary files
            if process_id:
                self.cleanup_temporary_files(process_id)
    
    async def validate_repository(self, repo_url: str) -> ValidationResult:
        """
        Validate repository URL and check basic accessibility.
        
        Args:
            repo_url: Repository URL to validate
            
        Returns:
            ValidationResult indicating if repository is valid and accessible
        """
        try:
            # Basic URL validation
            if not repo_url or not isinstance(repo_url, str):
                return ValidationResult(valid=False, error="Invalid repository URL")
            
            # Check if it's a valid Git URL format
            valid_patterns = [
                r'https://github\.com/[\w\-\.]+/[\w\-\.]+',
                r'git@github\.com:[\w\-\.]+/[\w\-\.]+\.git',
                r'https://gitlab\.com/[\w\-\.]+/[\w\-\.]+',
                r'https://bitbucket\.org/[\w\-\.]+/[\w\-\.]+',
            ]
            
            import re
            is_valid_format = any(re.match(pattern, repo_url) for pattern in valid_patterns)
            
            if not is_valid_format:
                return ValidationResult(
                    valid=False, 
                    error="Repository URL format not supported. Please use GitHub, GitLab, or Bitbucket URLs."
                )
            
            # For now, assume valid if format is correct
            # In a full implementation, we might do additional checks here
            return ValidationResult(
                valid=True,
                repo_info={
                    'url': repo_url,
                    'validated_at': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Repository validation error: {str(e)}")
            return ValidationResult(valid=False, error=f"Validation failed: {str(e)}")
    
    def parse_gitingest_output(self, raw_output: str, repo_url: str) -> StructuredRepository:
        """
        Parse gitingest raw output into structured repository representation.
        
        Args:
            raw_output: Raw text output from gitingest command
            repo_url: Original repository URL
            
        Returns:
            StructuredRepository with parsed and structured data
        """
        try:
            self.logger.info("Parsing gitingest output into structured format")
            
            # Initialize data structures
            files = {}
            file_hierarchy = {}
            language_stats = {}
            
            # Parse the gitingest output
            # Gitingest format: FILE: filename followed by content
            lines = raw_output.split('\n')
            current_file = None
            current_content = []
            in_file_section = False
            
            for line in lines:
                # Detect file headers - gitingest uses "FILE: filename" format
                if line.startswith('FILE: '):
                    # Save previous file if exists
                    if current_file and current_content:
                        self._add_file_to_structure(current_file, current_content, files, language_stats)
                    
                    # Start new file
                    current_file = line.replace('FILE: ', '').strip()
                    current_content = []
                    in_file_section = True
                    
                elif line.startswith('='):
                    # Skip separator lines
                    continue
                    
                elif line.startswith('Directory structure:'):
                    # Skip directory structure section
                    in_file_section = False
                    current_file = None
                    
                elif in_file_section and current_file:
                    # Add content line
                    current_content.append(line)
            
            # Add last file
            if current_file and current_content:
                self._add_file_to_structure(current_file, current_content, files, language_stats)
            
            # Build file hierarchy from the raw output directory structure
            file_hierarchy = self._parse_directory_structure(raw_output)
            
            # Create metadata
            metadata = GitingestMetadata(
                processing_time=0.0,  # Will be set by caller
                total_files=len(files),
                total_size=sum(block.size_bytes for block in files.values()),
                gitingest_version="unknown",  # Could be detected from gitingest --version
                processed_at=datetime.now().isoformat()
            )
            
            return StructuredRepository(
                repo_url=repo_url,
                files=files,
                file_hierarchy=file_hierarchy,
                language_stats=language_stats,
                gitingest_metadata=metadata,
                raw_output=raw_output
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing gitingest output: {str(e)}")
            raise
    
    def cleanup_temporary_files(self, process_id: str) -> None:
        """
        Clean up temporary files and directories created during processing.
        
        Args:
            process_id: Unique identifier for the processing session
        """
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Cleaned up temporary directory for process {process_id}")
        except Exception as e:
            self.logger.error(f"Error cleaning up temporary files for process {process_id}: {str(e)}")
    
    def _create_temp_directory(self) -> str:
        """Create temporary directory for processing and return process ID"""
        self.temp_dir = tempfile.mkdtemp(prefix="gitingest_")
        process_id = os.path.basename(self.temp_dir)
        self.logger.debug(f"Created temporary directory: {self.temp_dir}")
        return process_id
    
    async def _execute_gitingest(self, repo_url: str, auth_config: AuthConfig, process_id: str) -> str:
        """
        Execute gitingest command with proper authentication and configuration.
        
        Args:
            repo_url: Repository URL to process
            auth_config: Authentication configuration
            process_id: Process identifier for cleanup
            
        Returns:
            Raw output from gitingest command
        """
        output_file = None
        try:
            # Create temporary output file (Windows encoding workaround)
            import tempfile
            output_fd, output_file = tempfile.mkstemp(suffix='.txt', dir=self.temp_dir, text=True)
            os.close(output_fd)  # Close the file descriptor, we'll use the path
            
            # Build gitingest command with correct syntax
            cmd = ['gitingest', repo_url]
            
            # Add configuration options using correct flags
            if self.config.max_file_size:
                cmd.extend(['--max-size', str(self.config.max_file_size)])
            
            # Add include patterns
            for pattern in self.config.include_patterns:
                cmd.extend(['--include-pattern', pattern])
            
            # Add exclude patterns
            for pattern in self.config.exclude_patterns:
                cmd.extend(['--exclude-pattern', pattern])
            
            # Include gitignored files if configured
            if not self.config.respect_gitignore:
                cmd.append('--include-gitignored')
            
            # Add token if provided
            if auth_config.token:
                cmd.extend(['--token', auth_config.token])
            
            # Output to temporary file (Windows encoding workaround)
            cmd.extend(['--output', output_file])
            
            # Set up environment
            env = os.environ.copy()
            if auth_config.token:
                env['GITHUB_TOKEN'] = auth_config.token
            
            # Execute gitingest
            self.logger.debug(f"Executing gitingest command: {' '.join(cmd[:-2])} [URL] --output [temp_file]")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                env=env,
                cwd=self.temp_dir,
                encoding='utf-8',
                errors='replace'  # Handle encoding errors gracefully
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown gitingest error"
                raise RuntimeError(f"Gitingest execution failed: {error_msg}")
            
            # Read the output file
            with open(output_file, 'r', encoding='utf-8', errors='replace') as f:
                output_content = f.read()
            
            return output_content
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Gitingest execution timed out after {self.config.timeout} seconds")
        except FileNotFoundError:
            raise RuntimeError("Gitingest is not installed or not in PATH")
        except Exception as e:
            raise RuntimeError(f"Gitingest execution failed: {str(e)}")
        finally:
            # Clean up temporary output file
            if output_file and os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary output file {output_file}: {e}")
    
    def _add_file_to_structure(self, file_path: str, content_lines: List[str], 
                              files: Dict[str, ContentBlock], language_stats: Dict[str, int]) -> None:
        """Add a file to the structured repository data"""
        # Clean up content - remove empty lines at the end
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        
        content = '\n'.join(content_lines)
        language = self._detect_language(file_path)
        
        # Update language statistics
        if language:
            language_stats[language] = language_stats.get(language, 0) + 1
        
        # Create content block
        content_block = ContentBlock(
            file_path=file_path,
            content=content,
            language=language or 'unknown',
            line_count=len(content_lines),
            size_bytes=len(content.encode('utf-8')),
            file_type=self._get_file_type(file_path)
        )
        
        files[file_path] = content_block
    
    def _parse_directory_structure(self, raw_output: str) -> Dict[str, Any]:
        """Parse directory structure from gitingest output"""
        hierarchy = {}
        
        lines = raw_output.split('\n')
        in_directory_section = False
        
        for line in lines:
            if line.startswith('Directory structure:'):
                in_directory_section = True
                continue
            elif line.startswith('=') and in_directory_section:
                # End of directory section
                break
            elif in_directory_section and line.strip():
                # Parse directory tree lines
                # Example: "    └── README" or "└── octocat-hello-world/"
                if '└──' in line or '├──' in line:
                    # Extract file/folder name
                    parts = line.split('──')
                    if len(parts) > 1:
                        name = parts[-1].strip()
                        if name.endswith('/'):
                            # Directory
                            hierarchy[name[:-1]] = {}
                        else:
                            # File
                            hierarchy[name] = name
        
        return hierarchy
    
    def _build_file_hierarchy(self, file_paths: List[str]) -> Dict[str, Any]:
        """Build hierarchical structure from file paths"""
        hierarchy = {}
        
        for file_path in file_paths:
            parts = file_path.split('/')
            current = hierarchy
            
            for part in parts[:-1]:  # Directories
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # File
            if parts:
                current[parts[-1]] = file_path
        
        return hierarchy
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'JavaScript',
            '.tsx': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.md': 'Markdown',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.xml': 'XML',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.bash': 'Shell',
            '.ps1': 'PowerShell'
        }
        
        return language_map.get(ext)
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type category"""
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala']:
            return 'source'
        elif ext in ['.md', '.txt', '.rst', '.doc', '.docx']:
            return 'documentation'
        elif ext in ['.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.cfg']:
            return 'configuration'
        elif ext in ['.html', '.css', '.scss', '.less']:
            return 'web'
        elif ext in ['.sql']:
            return 'database'
        elif ext in ['.sh', '.bash', '.ps1', '.bat']:
            return 'script'
        else:
            return 'other'