from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import requests
from datetime import datetime
import logging
import re
from urllib.parse import urlparse
import subprocess
import shutil
from pathlib import Path
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Enable CORS for frontend integration
CORS(app, supports_credentials=True)

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.environ.get('GITHUB_REDIRECT_URI', 'http://localhost:5000/auth/github/callback')

class GitHubService:
    """Service for handling GitHub authentication and repository access"""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        
    def validate_token(self, token):
        """Validate GitHub personal access token"""
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(f'{self.base_url}/user', headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'valid': True,
                    'user': {
                        'login': user_data.get('login'),
                        'id': user_data.get('id'),
                        'name': user_data.get('name'),
                        'email': user_data.get('email')
                    },
                    'scopes': response.headers.get('X-OAuth-Scopes', '').split(', ')
                }
            else:
                return {
                    'valid': False,
                    'error': 'Invalid token or insufficient permissions'
                }
                
        except requests.RequestException as e:
            logger.error(f"GitHub API error: {str(e)}")
            return {
                'valid': False,
                'error': 'Failed to validate token with GitHub API'
            }
    
    def get_oauth_url(self, state=None):
        """Generate GitHub OAuth authorization URL"""
        if not GITHUB_CLIENT_ID:
            raise ValueError("GitHub Client ID not configured")
            
        params = {
            'client_id': GITHUB_CLIENT_ID,
            'redirect_uri': GITHUB_REDIRECT_URI,
            'scope': 'repo,user:email',
            'state': state or 'default'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    def exchange_code_for_token(self, code, state):
        """Exchange OAuth code for access token"""
        try:
            data = {
                'client_id': GITHUB_CLIENT_ID,
                'client_secret': GITHUB_CLIENT_SECRET,
                'code': code,
                'redirect_uri': GITHUB_REDIRECT_URI,
                'state': state
            }
            
            headers = {
                'Accept': 'application/json'
            }
            
            response = requests.post(
                'https://github.com/login/oauth/access_token',
                data=data,
                headers=headers
            )
            
            if response.status_code == 200:
                token_data = response.json()
                if 'access_token' in token_data:
                    return {
                        'success': True,
                        'access_token': token_data['access_token'],
                        'token_type': token_data.get('token_type', 'bearer'),
                        'scope': token_data.get('scope', '')
                    }
                else:
                    return {
                        'success': False,
                        'error': token_data.get('error_description', 'Failed to get access token')
                    }
            else:
                return {
                    'success': False,
                    'error': 'GitHub OAuth server error'
                }
                
        except requests.RequestException as e:
            logger.error(f"OAuth token exchange error: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to exchange code for token'
            }
    
    def parse_github_url(self, url):
        """Parse GitHub repository URL to extract owner and repo name"""
        try:
            # Handle different GitHub URL formats
            patterns = [
                r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$',
                r'github\.com/([^/]+)/([^/]+?)(?:/.*)?$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    owner, repo = match.groups()
                    # Remove .git suffix if present
                    repo = repo.replace('.git', '')
                    return {'owner': owner, 'repo': repo}
            
            return None
        except Exception as e:
            logger.error(f"URL parsing error: {str(e)}")
            return None
    
    def validate_repository_access(self, owner, repo, token=None):
        """Validate repository exists and check access permissions"""
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'AI-Project-Analyzer/1.0'
            }
            
            if token:
                headers['Authorization'] = f'token {token}'
            
            # Check repository existence and basic info
            response = requests.get(
                f'{self.base_url}/repos/{owner}/{repo}',
                headers=headers
            )
            
            if response.status_code == 200:
                repo_data = response.json()
                return {
                    'accessible': True,
                    'repo_info': {
                        'name': repo_data.get('name'),
                        'full_name': repo_data.get('full_name'),
                        'description': repo_data.get('description'),
                        'private': repo_data.get('private', False),
                        'size': repo_data.get('size', 0),
                        'language': repo_data.get('language'),
                        'languages_url': repo_data.get('languages_url'),
                        'default_branch': repo_data.get('default_branch', 'main'),
                        'clone_url': repo_data.get('clone_url'),
                        'html_url': repo_data.get('html_url'),
                        'created_at': repo_data.get('created_at'),
                        'updated_at': repo_data.get('updated_at'),
                        'stargazers_count': repo_data.get('stargazers_count', 0),
                        'forks_count': repo_data.get('forks_count', 0)
                    }
                }
            elif response.status_code == 404:
                return {
                    'accessible': False,
                    'error': 'Repository not found or not accessible'
                }
            elif response.status_code == 403:
                return {
                    'accessible': False,
                    'error': 'Access forbidden - repository may be private or rate limited'
                }
            else:
                return {
                    'accessible': False,
                    'error': f'GitHub API error: {response.status_code}'
                }
                
        except requests.RequestException as e:
            logger.error(f"Repository validation error: {str(e)}")
            return {
                'accessible': False,
                'error': 'Failed to connect to GitHub API'
            }
    
    def get_repository_tree(self, owner, repo, token=None, branch=None):
        """Get repository file tree structure"""
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'AI-Project-Analyzer/1.0'
            }
            
            if token:
                headers['Authorization'] = f'token {token}'
            
            # Get default branch if not specified
            if not branch:
                repo_info = self.validate_repository_access(owner, repo, token)
                if repo_info['accessible']:
                    branch = repo_info['repo_info']['default_branch']
                else:
                    return repo_info
            
            # Get repository tree
            response = requests.get(
                f'{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1',
                headers=headers
            )
            
            if response.status_code == 200:
                tree_data = response.json()
                
                # Process tree data
                files = []
                directories = []
                
                for item in tree_data.get('tree', []):
                    if item['type'] == 'blob':  # File
                        files.append({
                            'path': item['path'],
                            'sha': item['sha'],
                            'size': item.get('size', 0),
                            'url': item.get('url')
                        })
                    elif item['type'] == 'tree':  # Directory
                        directories.append({
                            'path': item['path'],
                            'sha': item['sha']
                        })
                
                return {
                    'success': True,
                    'tree': {
                        'files': files,
                        'directories': directories,
                        'total_files': len(files),
                        'total_directories': len(directories),
                        'sha': tree_data.get('sha'),
                        'truncated': tree_data.get('truncated', False)
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to get repository tree: {response.status_code}'
                }
                
        except requests.RequestException as e:
            logger.error(f"Repository tree error: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to fetch repository tree'
            }
    
    def get_file_content(self, owner, repo, file_path, token=None, branch=None):
        """Get content of a specific file from repository"""
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'AI-Project-Analyzer/1.0'
            }
            
            if token:
                headers['Authorization'] = f'token {token}'
            
            # Build URL with branch if specified
            url = f'{self.base_url}/repos/{owner}/{repo}/contents/{file_path}'
            if branch:
                url += f'?ref={branch}'
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                
                # Handle file vs directory
                if isinstance(file_data, list):
                    return {
                        'success': False,
                        'error': 'Path is a directory, not a file'
                    }
                
                return {
                    'success': True,
                    'file': {
                        'name': file_data.get('name'),
                        'path': file_data.get('path'),
                        'sha': file_data.get('sha'),
                        'size': file_data.get('size'),
                        'content': file_data.get('content'),  # Base64 encoded
                        'encoding': file_data.get('encoding'),
                        'download_url': file_data.get('download_url'),
                        'html_url': file_data.get('html_url')
                    }
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'File not found'
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to get file content: {response.status_code}'
                }
                
        except requests.RequestException as e:
            logger.error(f"File content error: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to fetch file content'
            }
    
    def deep_analyze_repository(self, owner, repo, token=None, max_file_size=1024*1024):
        """
        Perform deep analysis of repository - fetch all files with content
        Returns complete repository structure with file contents
        """
        import time
        start_time = time.time()
        
        try:
            # First get repository info and tree
            repo_info = self.validate_repository_access(owner, repo, token)
            if not repo_info['accessible']:
                return repo_info
            
            tree_result = self.get_repository_tree(owner, repo, token)
            if not tree_result['success']:
                return tree_result
            
            # Initialize result structure
            deep_analysis = {
                'repository_info': repo_info['repo_info'],
                'structure': {
                    'total_files': tree_result['tree']['total_files'],
                    'total_directories': tree_result['tree']['total_directories'],
                    'directories': tree_result['tree']['directories'],
                    'files_with_content': [],
                    'skipped_files': [],
                    'processing_stats': {
                        'processed': 0,
                        'skipped_large': 0,
                        'skipped_binary': 0,
                        'errors': 0,
                        'start_time': datetime.utcnow().isoformat(),
                        'files_per_second': 0
                    }
                }
            }
            
            # Define file extensions to skip (binary files)
            binary_extensions = {
                '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
                '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
                '.exe', '.dll', '.so', '.dylib',
                '.mp4', '.avi', '.mov', '.wmv', '.flv',
                '.mp3', '.wav', '.ogg', '.flac',
                '.woff', '.woff2', '.ttf', '.eot',
                '.bin', '.dat', '.db', '.sqlite'
            }
            
            # Process each file
            for file_info in tree_result['tree']['files']:
                file_path = file_info['path']
                file_size = file_info.get('size', 0)
                
                # Skip large files
                if file_size > max_file_size:
                    deep_analysis['structure']['skipped_files'].append({
                        'path': file_path,
                        'reason': 'file_too_large',
                        'size': file_size,
                        'max_size': max_file_size
                    })
                    deep_analysis['structure']['processing_stats']['skipped_large'] += 1
                    continue
                
                # Skip binary files based on extension
                file_ext = '.' + file_path.split('.')[-1].lower() if '.' in file_path else ''
                if file_ext in binary_extensions:
                    deep_analysis['structure']['skipped_files'].append({
                        'path': file_path,
                        'reason': 'binary_file',
                        'extension': file_ext
                    })
                    deep_analysis['structure']['processing_stats']['skipped_binary'] += 1
                    continue
                
                # Fetch file content
                try:
                    file_result = self.get_file_content(owner, repo, file_path, token)
                    
                    if file_result['success']:
                        file_data = file_result['file']
                        
                        # Decode content if it's base64 encoded
                        content = file_data.get('content', '')
                        if content and file_data.get('encoding') == 'base64':
                            try:
                                import base64
                                decoded_content = base64.b64decode(content).decode('utf-8')
                                content = decoded_content
                            except (UnicodeDecodeError, Exception):
                                # If decoding fails, treat as binary
                                deep_analysis['structure']['skipped_files'].append({
                                    'path': file_path,
                                    'reason': 'decode_error',
                                    'size': file_size
                                })
                                deep_analysis['structure']['processing_stats']['skipped_binary'] += 1
                                continue
                        
                        # Add file with content to results
                        deep_analysis['structure']['files_with_content'].append({
                            'path': file_path,
                            'name': file_data['name'],
                            'size': file_data['size'],
                            'sha': file_data['sha'],
                            'content': content,
                            'download_url': file_data.get('download_url'),
                            'html_url': file_data.get('html_url'),
                            'lines': len(content.split('\n')) if content else 0,
                            'extension': file_ext
                        })
                        
                        deep_analysis['structure']['processing_stats']['processed'] += 1
                        
                    else:
                        deep_analysis['structure']['skipped_files'].append({
                            'path': file_path,
                            'reason': 'fetch_error',
                            'error': file_result.get('error')
                        })
                        deep_analysis['structure']['processing_stats']['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    deep_analysis['structure']['skipped_files'].append({
                        'path': file_path,
                        'reason': 'processing_error',
                        'error': str(e)
                    })
                    deep_analysis['structure']['processing_stats']['errors'] += 1
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Update processing stats with timing info
            total_files_processed = deep_analysis['structure']['processing_stats']['processed']
            files_per_second = total_files_processed / processing_time if processing_time > 0 else 0
            deep_analysis['structure']['processing_stats']['files_per_second'] = round(files_per_second, 2)
            deep_analysis['structure']['processing_stats']['end_time'] = datetime.utcnow().isoformat()
            deep_analysis['structure']['processing_stats']['total_processing_time_seconds'] = round(processing_time, 2)
            
            return {
                'success': True,
                'deep_analysis': deep_analysis,
                'analyzed_at': datetime.utcnow().isoformat(),
                'processing_time': {
                    'seconds': round(processing_time, 2),
                    'minutes': round(processing_time / 60, 2),
                    'formatted': f"{int(processing_time // 60)}m {int(processing_time % 60)}s"
                }
            }
            
        except Exception as e:
            logger.error(f"Deep analysis error: {str(e)}")
            return {
                'success': False,
                'error': f'Deep analysis failed: {str(e)}'
            }
    
    def clone_repository(self, owner, repo, token=None, target_dir="./my_repos"):
        """
        Clone a GitHub repository to local directory
        Returns path to cloned repository and metadata
        """
        try:
            # Create target directory if it doesn't exist
            repos_dir = Path(target_dir)
            repos_dir.mkdir(exist_ok=True)
            
            # Create owner directory
            owner_dir = repos_dir / owner
            owner_dir.mkdir(exist_ok=True)
            
            # Repository path
            repo_path = owner_dir / repo
            
            # If repository already exists, remove it for fresh clone
            if repo_path.exists():
                logger.info(f"Removing existing repository at {repo_path}")
                shutil.rmtree(repo_path)
            
            # Build clone URL
            if token:
                # Use token for authentication (works for both public and private repos)
                clone_url = f"https://{token}@github.com/{owner}/{repo}.git"
            else:
                # Public repository clone
                clone_url = f"https://github.com/{owner}/{repo}.git"
            
            logger.info(f"Cloning repository: {owner}/{repo}")
            
            # Clone the repository
            result = subprocess.run([
                'git', 'clone', 
                '--depth', '1',  # Shallow clone for faster operation
                clone_url, 
                str(repo_path)
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                # Get repository statistics
                stats = self._get_local_repo_stats(repo_path)
                
                return {
                    'success': True,
                    'clone_path': str(repo_path),
                    'clone_url': clone_url.replace(token, '***') if token else clone_url,
                    'stats': stats,
                    'cloned_at': datetime.utcnow().isoformat()
                }
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown git error"
                # Don't expose token in error messages
                if token:
                    error_msg = error_msg.replace(token, '***')
                
                return {
                    'success': False,
                    'error': f'Git clone failed: {error_msg}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Repository clone timed out (5 minutes)'
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': 'Git is not installed or not in PATH'
            }
        except Exception as e:
            logger.error(f"Clone error: {str(e)}")
            return {
                'success': False,
                'error': f'Clone failed: {str(e)}'
            }
    
    def _get_local_repo_stats(self, repo_path):
        """Get statistics from locally cloned repository"""
        try:
            stats = {
                'total_files': 0,
                'total_directories': 0,
                'file_types': {},
                'size_bytes': 0,
                'languages': {}
            }
            
            # Walk through all files
            for root, dirs, files in os.walk(repo_path):
                # Skip .git directory
                if '.git' in dirs:
                    dirs.remove('.git')
                
                stats['total_directories'] += len(dirs)
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # Count files
                    stats['total_files'] += 1
                    
                    # Get file size
                    try:
                        stats['size_bytes'] += file_path.stat().st_size
                    except:
                        pass
                    
                    # Count file extensions
                    ext = file_path.suffix.lower()
                    if ext:
                        stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
                    
                    # Detect languages by extension
                    language = self._detect_language_by_extension(ext)
                    if language:
                        stats['languages'][language] = stats['languages'].get(language, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return {'error': str(e)}
    
    def _detect_language_by_extension(self, ext):
        """Detect programming language by file extension"""
        language_map = {
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.py': 'Python',
            '.java': 'Java',
            '.kt': 'Kotlin',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.cc': 'C++',
            '.cxx': 'C++',
            '.c': 'C',
            '.h': 'C/C++',
            '.hpp': 'C++',
            '.swift': 'Swift',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.scala': 'Scala',
            '.sh': 'Shell',
            '.bash': 'Shell',
            '.ps1': 'PowerShell',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'Sass',
            '.less': 'Less',
            '.vue': 'Vue',
            '.svelte': 'Svelte',
            '.sql': 'SQL',
            '.json': 'JSON',
            '.xml': 'XML',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.toml': 'TOML',
            '.md': 'Markdown',
            '.dockerfile': 'Docker',
            '.r': 'R',
            '.m': 'Objective-C',
            '.mm': 'Objective-C++',
            '.dart': 'Dart',
            '.lua': 'Lua',
            '.pl': 'Perl',
            '.clj': 'Clojure',
            '.ex': 'Elixir',
            '.exs': 'Elixir',
            '.erl': 'Erlang',
            '.hrl': 'Erlang',
            '.fs': 'F#',
            '.fsx': 'F#',
            '.ml': 'OCaml',
            '.mli': 'OCaml',
            '.hs': 'Haskell',
            '.elm': 'Elm',
            '.jl': 'Julia',
            '.nim': 'Nim',
            '.zig': 'Zig'
        }
        return language_map.get(ext)
    
    def analyze_local_repository(self, repo_path, max_file_size=1024*1024):
        """
        Analyze locally cloned repository - much faster than API approach
        """
        try:
            repo_path = Path(repo_path)
            if not repo_path.exists():
                return {
                    'success': False,
                    'error': 'Repository path does not exist'
                }
            
            # Get repository stats
            stats = self._get_local_repo_stats(repo_path)
            
            # Initialize analysis result
            analysis = {
                'repository_path': str(repo_path),
                'stats': stats,
                'files_with_content': [],
                'skipped_files': [],
                'processing_stats': {
                    'processed': 0,
                    'skipped_large': 0,
                    'skipped_binary': 0,
                    'errors': 0
                }
            }
            
            # Binary file extensions to skip
            binary_extensions = {
                '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
                '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
                '.exe', '.dll', '.so', '.dylib',
                '.mp4', '.avi', '.mov', '.wmv', '.flv',
                '.mp3', '.wav', '.ogg', '.flac',
                '.woff', '.woff2', '.ttf', '.eot',
                '.bin', '.dat', '.db', '.sqlite',
                '.node', '.pyc', '.class', '.jar'
            }
            
            # Process all files
            for root, dirs, files in os.walk(repo_path):
                # Skip .git directory
                if '.git' in dirs:
                    dirs.remove('.git')
                
                # Skip node_modules and other common build directories
                skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 
                           'build', 'dist', 'target', '.gradle', '.idea', '.vscode'}
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(repo_path)
                    
                    try:
                        # Get file size
                        file_size = file_path.stat().st_size
                        
                        # Skip large files
                        if file_size > max_file_size:
                            analysis['skipped_files'].append({
                                'path': str(relative_path),
                                'reason': 'file_too_large',
                                'size': file_size
                            })
                            analysis['processing_stats']['skipped_large'] += 1
                            continue
                        
                        # Skip binary files
                        file_ext = file_path.suffix.lower()
                        if file_ext in binary_extensions:
                            analysis['skipped_files'].append({
                                'path': str(relative_path),
                                'reason': 'binary_file',
                                'extension': file_ext
                            })
                            analysis['processing_stats']['skipped_binary'] += 1
                            continue
                        
                        # Read file content
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Add to analysis
                            analysis['files_with_content'].append({
                                'path': str(relative_path),
                                'name': file_path.name,
                                'size': file_size,
                                'content': content,
                                'lines': len(content.split('\n')),
                                'extension': file_ext,
                                'language': self._detect_language_by_extension(file_ext)
                            })
                            
                            analysis['processing_stats']['processed'] += 1
                            
                        except UnicodeDecodeError:
                            # File is likely binary
                            analysis['skipped_files'].append({
                                'path': str(relative_path),
                                'reason': 'encoding_error',
                                'size': file_size
                            })
                            analysis['processing_stats']['skipped_binary'] += 1
                            
                    except Exception as e:
                        analysis['skipped_files'].append({
                            'path': str(relative_path),
                            'reason': 'processing_error',
                            'error': str(e)
                        })
                        analysis['processing_stats']['errors'] += 1
            
            return {
                'success': True,
                'analysis': analysis,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Local analysis error: {str(e)}")
            return {
                'success': False,
                'error': f'Local analysis failed: {str(e)}'
            }

# Initialize services
github_service = GitHubService()

@app.route('/auth/github/login', methods=['POST'])
def github_login():
    """Initiate GitHub OAuth login or validate personal access token"""
    try:
        # Better JSON parsing with error handling
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Handle personal access token authentication
        if 'token' in data:
            token = data['token'].strip()
            
            if not token:
                return jsonify({'error': 'Token cannot be empty'}), 400
            
            # Validate the token
            validation_result = github_service.validate_token(token)
            
            if validation_result['valid']:
                # Store token in session (in-memory only)
                session['github_token'] = token
                session['github_user'] = validation_result['user']
                session['login_time'] = datetime.utcnow().isoformat()
                
                return jsonify({
                    'success': True,
                    'user': validation_result['user'],
                    'scopes': validation_result['scopes'],
                    'auth_method': 'token'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': validation_result['error']
                }), 401
        
        # Handle OAuth flow initiation
        elif 'oauth' in data and data['oauth']:
            try:
                state = data.get('state', 'default')
                oauth_url = github_service.get_oauth_url(state)
                
                return jsonify({
                    'success': True,
                    'oauth_url': oauth_url,
                    'auth_method': 'oauth'
                })
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        else:
            return jsonify({
                'error': 'Either "token" or "oauth": true must be provided'
            }), 400
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/github/callback', methods=['GET'])
def github_callback():
    """Handle GitHub OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            return jsonify({
                'success': False,
                'error': f'GitHub OAuth error: {error}'
            }), 400
        
        if not code:
            return jsonify({
                'success': False,
                'error': 'Authorization code not provided'
            }), 400
        
        # Exchange code for token
        token_result = github_service.exchange_code_for_token(code, state)
        
        if token_result['success']:
            # Validate the received token
            validation_result = github_service.validate_token(token_result['access_token'])
            
            if validation_result['valid']:
                # Store token in session
                session['github_token'] = token_result['access_token']
                session['github_user'] = validation_result['user']
                session['login_time'] = datetime.utcnow().isoformat()
                
                return jsonify({
                    'success': True,
                    'user': validation_result['user'],
                    'scopes': validation_result['scopes'],
                    'auth_method': 'oauth'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to validate received token'
                }), 401
        else:
            return jsonify({
                'success': False,
                'error': token_result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/status', methods=['GET'])
def auth_status():
    """Check current authentication status"""
    try:
        if 'github_token' in session and 'github_user' in session:
            return jsonify({
                'authenticated': True,
                'user': session['github_user'],
                'login_time': session.get('login_time')
            })
        else:
            return jsonify({
                'authenticated': False
            })
    except Exception as e:
        logger.error(f"Auth status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Clear authentication session"""
    try:
        # Clear all authentication data from session
        session.pop('github_token', None)
        session.pop('github_user', None)
        session.pop('login_time', None)
        
        return jsonify({
            'success': True,
            'message': 'Successfully logged out'
        })
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Repository endpoints
@app.route('/api/repositories/validate', methods=['POST'])
def validate_repository():
    """Validate repository URL and check access"""
    try:
        # Better JSON parsing with error handling
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        if not data or 'url' not in data:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        repo_url = data['url'].strip()
        if not repo_url:
            return jsonify({'error': 'Repository URL cannot be empty'}), 400
        
        # Parse GitHub URL
        parsed = github_service.parse_github_url(repo_url)
        if not parsed:
            return jsonify({
                'error': 'Invalid GitHub repository URL format'
            }), 400
        
        owner, repo = parsed['owner'], parsed['repo']
        
        # Get token from session if available
        token = session.get('github_token')
        
        # Validate repository access
        validation_result = github_service.validate_repository_access(owner, repo, token)
        
        if validation_result['accessible']:
            return jsonify({
                'success': True,
                'repository': validation_result['repo_info'],
                'parsed': {'owner': owner, 'repo': repo}
            })
        else:
            return jsonify({
                'success': False,
                'error': validation_result['error']
            }), 404
            
    except Exception as e:
        logger.error(f"Repository validation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/repositories/<owner>/<repo>/tree', methods=['GET'])
def get_repository_tree(owner, repo):
    """Get repository file tree structure"""
    try:
        # Get optional branch parameter
        branch = request.args.get('branch')
        
        # Get token from session if available
        token = session.get('github_token')
        
        # Get repository tree
        tree_result = github_service.get_repository_tree(owner, repo, token, branch)
        
        if tree_result.get('success'):
            return jsonify(tree_result)
        else:
            return jsonify({
                'error': tree_result.get('error', 'Failed to get repository tree')
            }), 400
            
    except Exception as e:
        logger.error(f"Repository tree error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/repositories/<owner>/<repo>/files/<path:file_path>', methods=['GET'])
def get_file_content(owner, repo, file_path):
    """Get content of a specific file from repository"""
    try:
        # Get optional branch parameter
        branch = request.args.get('branch')
        
        # Get token from session if available
        token = session.get('github_token')
        
        # Get file content
        file_result = github_service.get_file_content(owner, repo, file_path, token, branch)
        
        if file_result.get('success'):
            return jsonify(file_result)
        else:
            return jsonify({
                'error': file_result.get('error', 'Failed to get file content')
            }), 404
            
    except Exception as e:
        logger.error(f"File content error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/repositories/analyze', methods=['POST'])
def analyze_repository():
    """Start repository analysis process"""
    try:
        # Better JSON parsing with error handling
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        if not data or 'url' not in data:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        repo_url = data['url'].strip()
        
        # Parse GitHub URL
        parsed = github_service.parse_github_url(repo_url)
        if not parsed:
            return jsonify({
                'error': 'Invalid GitHub repository URL format'
            }), 400
        
        owner, repo = parsed['owner'], parsed['repo']
        
        # Get token from session if available
        token = session.get('github_token')
        
        # First validate repository access
        validation_result = github_service.validate_repository_access(owner, repo, token)
        
        if not validation_result['accessible']:
            return jsonify({
                'success': False,
                'error': validation_result['error']
            }), 404
        
        # Get repository structure
        tree_result = github_service.get_repository_tree(owner, repo, token)
        
        if not tree_result.get('success'):
            return jsonify({
                'success': False,
                'error': tree_result.get('error', 'Failed to analyze repository structure')
            }), 400
        
        # Return analysis results
        return jsonify({
            'success': True,
            'analysis': {
                'repository': validation_result['repo_info'],
                'structure': tree_result['tree'],
                'parsed': {'owner': owner, 'repo': repo},
                'analyzed_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Repository analysis error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/repositories/deep-analyze', methods=['POST'])
def deep_analyze_repository():
    """Perform deep analysis of repository - fetch all files with their content"""
    try:
        # Better JSON parsing with error handling
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        if not data or 'url' not in data:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        repo_url = data['url'].strip()
        max_file_size = data.get('max_file_size', 1024*1024)  # Default 1MB limit
        
        # Parse GitHub URL
        parsed = github_service.parse_github_url(repo_url)
        if not parsed:
            return jsonify({
                'error': 'Invalid GitHub repository URL format'
            }), 400
        
        owner, repo = parsed['owner'], parsed['repo']
        
        # Get token from session if available
        token = session.get('github_token')
        
        # Perform deep analysis
        logger.info(f"Starting deep analysis of {owner}/{repo}")
        analysis_result = github_service.deep_analyze_repository(owner, repo, token, max_file_size)
        
        if analysis_result.get('success'):
            logger.info(f"Deep analysis completed for {owner}/{repo}")
            return jsonify(analysis_result)
        else:
            return jsonify({
                'success': False,
                'error': analysis_result.get('error', 'Deep analysis failed')
            }), 400
            
    except Exception as e:
        logger.error(f"Deep analysis endpoint error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/repositories/<owner>/<repo>/explore', methods=['GET'])
def explore_repository_structure(owner, repo):
    """Get detailed repository structure with file contents (alternative endpoint)"""
    try:
        # Get optional parameters
        max_file_size = request.args.get('max_file_size', 1024*1024, type=int)
        
        # Get token from session if available
        token = session.get('github_token')
        
        # Perform deep analysis
        logger.info(f"Exploring repository structure: {owner}/{repo}")
        analysis_result = github_service.deep_analyze_repository(owner, repo, token, max_file_size)
        
        if analysis_result.get('success'):
            return jsonify(analysis_result)
        else:
            return jsonify({
                'error': analysis_result.get('error', 'Repository exploration failed')
            }), 400
            
    except Exception as e:
        logger.error(f"Repository exploration error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/repositories/clone', methods=['POST'])
def clone_repository():
    """Clone a GitHub repository to local storage"""
    try:
        # Better JSON parsing with error handling
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        if not data or 'url' not in data:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        repo_url = data['url'].strip()
        target_dir = data.get('target_dir', './my_repos')
        
        # Parse GitHub URL
        parsed = github_service.parse_github_url(repo_url)
        if not parsed:
            return jsonify({
                'error': 'Invalid GitHub repository URL format'
            }), 400
        
        owner, repo = parsed['owner'], parsed['repo']
        
        # Get token from session if available
        token = session.get('github_token')
        
        # Clone repository
        logger.info(f"Cloning repository: {owner}/{repo}")
        clone_result = github_service.clone_repository(owner, repo, token, target_dir)
        
        if clone_result.get('success'):
            logger.info(f"Repository cloned successfully: {clone_result['clone_path']}")
            return jsonify(clone_result)
        else:
            return jsonify({
                'success': False,
                'error': clone_result.get('error', 'Clone failed')
            }), 400
            
    except Exception as e:
        logger.error(f"Clone endpoint error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/repositories/clone-and-analyze', methods=['POST'])
def clone_and_analyze_repository():
    """Clone repository and perform local analysis - much faster than API approach"""
    try:
        # Better JSON parsing with error handling
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        if not data or 'url' not in data:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        repo_url = data['url'].strip()
        target_dir = data.get('target_dir', './my_repos')
        max_file_size = data.get('max_file_size', 1024*1024)  # Default 1MB
        cleanup_after = data.get('cleanup_after', False)  # Whether to delete after analysis
        
        # Parse GitHub URL
        parsed = github_service.parse_github_url(repo_url)
        if not parsed:
            return jsonify({
                'error': 'Invalid GitHub repository URL format'
            }), 400
        
        owner, repo = parsed['owner'], parsed['repo']
        
        # Get token from session if available
        token = session.get('github_token')
        
        # Step 1: Clone repository
        logger.info(f"Cloning repository: {owner}/{repo}")
        clone_result = github_service.clone_repository(owner, repo, token, target_dir)
        
        if not clone_result.get('success'):
            return jsonify({
                'success': False,
                'error': clone_result.get('error', 'Clone failed')
            }), 400
        
        repo_path = clone_result['clone_path']
        
        try:
            # Step 2: Analyze local repository
            logger.info(f"Analyzing local repository: {repo_path}")
            analysis_result = github_service.analyze_local_repository(repo_path, max_file_size)
            
            if analysis_result.get('success'):
                # Combine clone and analysis results
                combined_result = {
                    'success': True,
                    'clone_info': clone_result,
                    'analysis': analysis_result['analysis'],
                    'analyzed_at': analysis_result['analyzed_at']
                }
                
                # Cleanup if requested
                if cleanup_after:
                    try:
                        shutil.rmtree(repo_path)
                        combined_result['cleanup'] = 'Repository deleted after analysis'
                        logger.info(f"Cleaned up repository: {repo_path}")
                    except Exception as cleanup_error:
                        combined_result['cleanup_error'] = str(cleanup_error)
                        logger.warning(f"Failed to cleanup {repo_path}: {cleanup_error}")
                
                logger.info(f"Clone and analysis completed for {owner}/{repo}")
                return jsonify(combined_result)
            else:
                return jsonify({
                    'success': False,
                    'error': analysis_result.get('error', 'Analysis failed'),
                    'clone_info': clone_result
                }), 400
                
        except Exception as analysis_error:
            logger.error(f"Analysis error: {str(analysis_error)}")
            return jsonify({
                'success': False,
                'error': f'Analysis failed: {str(analysis_error)}',
                'clone_info': clone_result
            }), 500
            
    except Exception as e:
        logger.error(f"Clone and analyze endpoint error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)