"""
Configuration module for gitingest processing.

This module handles loading and validation of environment variables
for gitingest integration configuration.
"""

import os
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class GitingestConfig:
    """Configuration class for gitingest processing settings"""
    
    max_file_size: int
    timeout: int
    temp_dir: str
    include_patterns: List[str]
    exclude_patterns: List[str]
    
    @classmethod
    def from_environment(cls) -> 'GitingestConfig':
        """
        Load gitingest configuration from environment variables.
        
        Returns:
            GitingestConfig instance with values from environment or defaults
        """
        # Load with defaults
        max_file_size = int(os.getenv('GITINGEST_MAX_FILE_SIZE', '10485760'))  # 10MB default
        timeout = int(os.getenv('GITINGEST_TIMEOUT', '300'))  # 5 minutes default
        temp_dir = os.getenv('GITINGEST_TEMP_DIR', '/tmp/gitingest')
        
        # Parse comma-separated patterns
        include_patterns_str = os.getenv(
            'GITINGEST_INCLUDE_PATTERNS', 
            '*.py,*.js,*.ts,*.jsx,*.tsx,*.md,*.json,*.yaml,*.yml'
        )
        include_patterns = [p.strip() for p in include_patterns_str.split(',') if p.strip()]
        
        exclude_patterns_str = os.getenv(
            'GITINGEST_EXCLUDE_PATTERNS',
            'node_modules,__pycache__,.git,*.pyc,*.log'
        )
        exclude_patterns = [p.strip() for p in exclude_patterns_str.split(',') if p.strip()]
        
        return cls(
            max_file_size=max_file_size,
            timeout=timeout,
            temp_dir=temp_dir,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration values.
        
        Returns:
            List of validation error messages, empty if valid
        """
        errors = []
        
        if self.max_file_size <= 0:
            errors.append("max_file_size must be positive")
        
        if self.timeout <= 0:
            errors.append("timeout must be positive")
        
        if not self.temp_dir:
            errors.append("temp_dir cannot be empty")
        
        if not self.include_patterns:
            errors.append("include_patterns cannot be empty")
        
        return errors
    
    def to_processing_config(self):
        """
        Convert to ProcessingConfig for GitingestProcessor.
        
        Returns:
            ProcessingConfig instance
        """
        from .gitingest_processor import ProcessingConfig
        
        return ProcessingConfig(
            include_patterns=self.include_patterns,
            exclude_patterns=self.exclude_patterns,
            max_file_size=self.max_file_size,
            respect_gitignore=True,
            include_binary_files=False,
            timeout=self.timeout
        )


def load_gitingest_config() -> GitingestConfig:
    """
    Load and validate gitingest configuration from environment.
    
    Returns:
        GitingestConfig instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    config = GitingestConfig.from_environment()
    
    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid gitingest configuration: {', '.join(errors)}")
    
    return config


def get_github_token() -> Optional[str]:
    """
    Get GitHub token from environment variables.
    
    Checks multiple possible environment variable names for GitHub token.
    
    Returns:
        GitHub token if found, None otherwise
    """
    # Check common environment variable names for GitHub token
    # Prioritize the one already used in your app
    token_vars = [
        'GITHUB_API_TOKEN',  # Your existing token variable
        'GITHUB_TOKEN',
        'GITHUB_ACCESS_TOKEN', 
        'GH_TOKEN',
        'PERSONAL_ACCESS_TOKEN'
    ]
    
    for var in token_vars:
        token = os.getenv(var)
        if token and token != 'your_github_token_here':  # Skip placeholder values
            return token
    
    return None


def setup_gitingest_environment() -> None:
    """
    Set up environment for gitingest processing.
    
    Creates necessary directories and validates configuration.
    """
    import tempfile
    from pathlib import Path
    
    config = load_gitingest_config()
    
    # Create temp directory if it doesn't exist
    temp_path = Path(config.temp_dir)
    if not temp_path.exists():
        try:
            temp_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fall back to system temp directory
            config.temp_dir = tempfile.gettempdir()
    
    # Validate gitingest is available
    import subprocess
    try:
        result = subprocess.run(['gitingest', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise RuntimeError("Gitingest command failed")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise RuntimeError("Gitingest is not installed or not accessible in PATH")