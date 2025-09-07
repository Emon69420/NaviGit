# Design Document

## Overview

The Streamlit frontend will provide a modern, dark-themed interface for the AI Project Analyzer. It will communicate with the Flask backend via REST API calls to display existing repositories and clone new ones. The interface will be responsive, user-friendly, and provide real-time feedback on operations.

## Architecture

### Component Structure
```
streamlit_app.py (Main application)
├── UI Components
│   ├── Header/Navigation
│   ├── Repository List Display
│   ├── Add Repository Form
│   └── Status/Notification System
├── API Client
│   ├── Flask Backend Communication
│   ├── Error Handling
│   └── Response Processing
└── State Management
    ├── Session State for UI
    ├── Repository Cache
    └── Operation Status Tracking
```

### Technology Stack
- **Frontend Framework**: Streamlit
- **HTTP Client**: requests library
- **Styling**: Custom CSS for dark theme
- **State Management**: Streamlit session state
- **Icons**: Streamlit built-in icons and Unicode symbols

## Components and Interfaces

### 1. Main Application (streamlit_app.py)
**Purpose**: Entry point and main UI orchestration

**Key Functions**:
- `main()`: Main application entry point
- `load_custom_css()`: Apply dark theme styling
- `initialize_session_state()`: Set up session variables
- `render_header()`: Display app title and navigation
- `render_repository_list()`: Show existing repositories
- `render_add_repository_form()`: Input form for new repos
- `render_notifications()`: Display status messages

### 2. API Client Module
**Purpose**: Handle all communication with Flask backend

**Key Functions**:
- `get_local_repositories()`: Fetch list of cloned repositories
- `clone_repository(repo_url, token=None)`: Clone new repository
- `validate_github_url(url)`: Client-side URL validation
- `handle_api_response(response)`: Process API responses

**API Endpoints Used**:
- `GET /api/repositories/local` - List local repositories
- `POST /api/repositories/clone` - Clone repository
- `POST /api/repositories/clone-and-analyze` - Clone and analyze

### 3. Repository Display Component
**Purpose**: Show repository cards with metadata

**Features**:
- Repository name and description
- Last modified date
- File count and size statistics
- Language breakdown
- Quick action buttons

### 4. Add Repository Form
**Purpose**: Input interface for new repositories

**Features**:
- URL input with validation
- Optional GitHub token input
- Clone options (analyze immediately)
- Progress indicators
- Error handling and display

## Data Models

### Repository Data Structure
```python
{
    "name": str,
    "owner": str,
    "path": str,
    "description": str,
    "last_modified": str,
    "stats": {
        "total_files": int,
        "total_directories": int,
        "size_bytes": int,
        "languages": dict,
        "file_types": dict
    },
    "clone_info": {
        "cloned_at": str,
        "clone_url": str
    }
}
```

### UI State Model
```python
{
    "repositories": list,
    "loading": bool,
    "current_operation": str,
    "notifications": list,
    "github_token": str,
    "last_refresh": datetime
}
```

## Error Handling

### Client-Side Validation
- GitHub URL format validation
- Token format validation (if provided)
- Input sanitization

### API Error Handling
- Network connectivity errors
- HTTP status code handling
- Timeout management
- Rate limiting responses

### User Feedback
- Loading spinners for operations
- Success/error notifications
- Progress indicators for long operations
- Clear error messages with suggested actions

## Testing Strategy

### Unit Tests
- URL validation functions
- API client methods
- Data processing functions
- State management utilities

### Integration Tests
- Flask backend communication
- End-to-end repository cloning
- UI component interactions
- Error scenario handling

### Manual Testing
- UI responsiveness across screen sizes
- Dark theme consistency
- User workflow validation
- Performance with multiple repositories

## User Interface Design

### Dark Theme Specifications
- **Primary Background**: #0E1117 (Streamlit dark)
- **Secondary Background**: #262730
- **Text Primary**: #FAFAFA
- **Text Secondary**: #A6A6A6
- **Accent Color**: #FF4B4B (Streamlit red)
- **Success Color**: #00CC88
- **Warning Color**: #FFD700
- **Error Color**: #FF6B6B

### Layout Structure
```
┌─────────────────────────────────────┐
│ 🚀 AI Project Analyzer              │
├─────────────────────────────────────┤
│ Add New Repository                  │
│ ┌─────────────────────────────────┐ │
│ │ GitHub URL: [input field]       │ │
│ │ Token (optional): [input field] │ │
│ │ [Clone Repository] [Analyze]    │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ Your Repositories (2)               │
│ ┌─────────────────────────────────┐ │
│ │ 📁 owner/repo-name              │ │
│ │ Description here...             │ │
│ │ 🗓️ Modified: 2 days ago        │ │
│ │ 📊 Files: 45 | Size: 2.3MB     │ │
│ │ 🔤 Python 60% | JS 30% | CSS 10%│ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 📁 owner/another-repo           │ │
│ │ Another description...          │ │
│ │ 🗓️ Modified: 1 week ago        │ │
│ │ 📊 Files: 123 | Size: 5.7MB    │ │
│ │ 🔤 JavaScript 80% | HTML 20%   │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Interactive Elements
- Hover effects on repository cards
- Loading animations during operations
- Expandable sections for detailed stats
- Responsive button states
- Toast notifications for feedback

## Performance Considerations

### Caching Strategy
- Repository list caching with TTL
- Session state optimization
- Lazy loading of repository details

### API Optimization
- Batch requests where possible
- Request debouncing for user input
- Connection pooling for HTTP requests

### UI Performance
- Efficient state updates
- Minimal re-renders
- Progressive loading for large lists

## Security Considerations

### Token Handling
- Secure storage in session state
- No token logging or exposure
- Optional token usage

### Input Validation
- URL sanitization
- XSS prevention
- CSRF protection via API design

### API Communication
- HTTPS enforcement
- Request timeout limits
- Error message sanitization