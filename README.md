# AI Project Analyzer - Flask Backend

A Flask-based backend for analyzing GitHub repositories using AI-powered insights.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Configure your GitHub credentials in `.env` (optional for OAuth, not needed for personal access tokens)

4. Run the application:
```bash
python app.py
```

## GitHub Authentication

The API supports two authentication methods:

### 1. Personal Access Token (Recommended)

Send a POST request to `/auth/github/login` with your GitHub personal access token:

```bash
curl -X POST http://localhost:5000/auth/github/login \
  -H "Content-Type: application/json" \
  -d '{"token": "your_github_personal_access_token"}'
```

### 2. OAuth Flow

Initiate OAuth flow:

```bash
curl -X POST http://localhost:5000/auth/github/login \
  -H "Content-Type: application/json" \
  -d '{"oauth": true}'
```

This returns an `oauth_url` that users should visit to authorize the application.

### Repository Analysis

Validate a repository:

**Windows (PowerShell):**
```powershell
curl -X POST http://localhost:5000/api/repositories/validate -H "Content-Type: application/json" -d "{\"url\": \"https://github.com/owner/repo\"}"
```

**Linux/Mac:**
```bash
curl -X POST http://localhost:5000/api/repositories/validate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/owner/repo"}'
```

Analyze a repository (get full structure):

**Windows (PowerShell):**
```powershell
curl -X POST http://localhost:5000/api/repositories/analyze -H "Content-Type: application/json" -d "{\"url\": \"https://github.com/Emon69420/HazMap\"}"
```

**Linux/Mac:**
```bash
curl -X POST http://localhost:5000/api/repositories/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/Emon69420/HazMap"}'
```

**Alternative (using Python test script):**
```bash
python test_api.py
```

Get repository file tree:

```bash
curl http://localhost:5000/api/repositories/owner/repo/tree
```

Get specific file content:

```bash
curl http://localhost:5000/api/repositories/owner/repo/files/README.md
```

### Deep Repository Analysis (NEW!)

Get complete repository with all file contents:

**Windows (PowerShell):**
```powershell
curl -X POST http://localhost:5000/api/repositories/deep-analyze -H "Content-Type: application/json" -d "{\"url\": \"https://github.com/Emon69420/HazMapApp\", \"max_file_size\": 524288}"
```

**Alternative endpoint:**
```bash
curl "http://localhost:5000/api/repositories/Emon69420/HazMapApp/explore?max_file_size=524288"
```

**Using Python test script:**
```bash
python test_deep_analysis.py
```

This will:
- ✅ Fetch all text files with their complete source code
- 📊 Provide detailed statistics and file structure
- 🚫 Skip binary files and files that are too large
- 💾 Save complete analysis to JSON file
- 📈 Show processing progress and results

### Repository Cloning (FASTEST! - NEW!)

Clone and analyze repository locally (much faster than API):

**Clone and analyze in one step:**
```powershell
curl -X POST http://localhost:5000/api/repositories/clone-and-analyze -H "Content-Type: application/json" -d "{\"url\": \"https://github.com/Emon69420/HazMapApp\", \"cleanup_after\": false}"
```

**Just clone repository:**
```powershell
curl -X POST http://localhost:5000/api/repositories/clone -H "Content-Type: application/json" -d "{\"url\": \"https://github.com/Emon69420/HazMapApp\"}"
```

**Using Python test script:**
```bash
python test_clone.py
```

**Benefits of Cloning Approach:**
- ⚡ **10-50x faster** than API approach for large repositories
- 🚫 **No rate limits** - process unlimited files
- 📁 **Local storage** in `./my_repos/owner/repo/` folder
- 🔄 **Reusable** - analyze multiple times without re-downloading
- 🧹 **Optional cleanup** - delete after analysis if desired

**Requirements:**
- Git must be installed and in PATH
- Sufficient disk space for repositories

## API Endpoints

### Authentication
- `POST /auth/github/login` - Authenticate with GitHub (token or OAuth)
- `GET /auth/github/callback` - OAuth callback handler
- `GET /auth/status` - Check authentication status
- `POST /auth/logout` - Clear authentication session

### Repository Operations
- `POST /api/repositories/validate` - Validate repository URL and check access
- `GET /api/repositories/<owner>/<repo>/tree` - Get repository file structure
- `GET /api/repositories/<owner>/<repo>/files/<path>` - Get specific file content
- `POST /api/repositories/analyze` - Analyze repository structure and metadata
- `POST /api/repositories/deep-analyze` - Deep analysis with all file contents (API-based)
- `GET /api/repositories/<owner>/<repo>/explore` - Alternative deep analysis endpoint
- `POST /api/repositories/clone` - **NEW!** Clone repository to local storage
- `POST /api/repositories/clone-and-analyze` - **NEW!** Clone and analyze locally (FASTEST!)

## Testing

Run the test suite:

```bash
python -m pytest test_github_auth.py -v
```

## Security Features

- Tokens stored in session memory only (not persisted)
- Automatic session cleanup on logout
- HTTPS enforcement in production
- Input validation and sanitization
- Rate limiting protection