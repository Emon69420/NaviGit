import unittest
from unittest.mock import patch, MagicMock
import json
from app import app, GitHubService

class TestGitHubService(unittest.TestCase):
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.github_service = GitHubService()
    
    @patch('requests.get')
    def test_validate_token_success(self, mock_get):
        """Test successful token validation"""
        # Mock successful GitHub API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'login': 'testuser',
            'id': 12345,
            'name': 'Test User',
            'email': 'test@example.com'
        }
        mock_response.headers = {'X-OAuth-Scopes': 'repo, user:email'}
        mock_get.return_value = mock_response
        
        result = self.github_service.validate_token('valid_token')
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['user']['login'], 'testuser')
        self.assertIn('repo', result['scopes'])
    
    @patch('requests.get')
    def test_validate_token_invalid(self, mock_get):
        """Test invalid token validation"""
        # Mock failed GitHub API response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = self.github_service.validate_token('invalid_token')
        
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
    
    def test_get_oauth_url(self):
        """Test OAuth URL generation"""
        with patch.dict('os.environ', {'GITHUB_CLIENT_ID': 'test_client_id'}):
            url = self.github_service.get_oauth_url('test_state')
            
            self.assertIn('github.com/login/oauth/authorize', url)
            self.assertIn('client_id=test_client_id', url)
            self.assertIn('state=test_state', url)
    
    def test_login_with_token(self):
        """Test login endpoint with personal access token"""
        with patch.object(self.github_service, 'validate_token') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'user': {'login': 'testuser', 'id': 12345},
                'scopes': ['repo', 'user:email']
            }
            
            response = self.app.post('/auth/github/login',
                                   data=json.dumps({'token': 'test_token'}),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertEqual(data['user']['login'], 'testuser')
    
    def test_login_with_oauth(self):
        """Test login endpoint OAuth flow initiation"""
        with patch.dict('os.environ', {'GITHUB_CLIENT_ID': 'test_client_id'}):
            response = self.app.post('/auth/github/login',
                                   data=json.dumps({'oauth': True}),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIn('oauth_url', data)
    
    def test_auth_status_authenticated(self):
        """Test auth status when user is authenticated"""
        with self.app.session_transaction() as sess:
            sess['github_token'] = 'test_token'
            sess['github_user'] = {'login': 'testuser', 'id': 12345}
        
        response = self.app.get('/auth/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['user']['login'], 'testuser')
    
    def test_auth_status_not_authenticated(self):
        """Test auth status when user is not authenticated"""
        response = self.app.get('/auth/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['authenticated'])
    
    def test_logout(self):
        """Test logout functionality"""
        with self.app.session_transaction() as sess:
            sess['github_token'] = 'test_token'
            sess['github_user'] = {'login': 'testuser'}
        
        response = self.app.post('/auth/logout')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    def test_parse_github_url(self):
        """Test GitHub URL parsing"""
        # Test various URL formats
        test_cases = [
            ('https://github.com/owner/repo', {'owner': 'owner', 'repo': 'repo'}),
            ('https://github.com/owner/repo.git', {'owner': 'owner', 'repo': 'repo'}),
            ('git@github.com:owner/repo.git', {'owner': 'owner', 'repo': 'repo'}),
            ('https://github.com/owner/repo/', {'owner': 'owner', 'repo': 'repo'}),
            ('invalid-url', None)
        ]
        
        for url, expected in test_cases:
            result = self.github_service.parse_github_url(url)
            self.assertEqual(result, expected)
    
    @patch('requests.get')
    def test_validate_repository_access_public(self, mock_get):
        """Test repository validation for public repo"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'test-repo',
            'full_name': 'owner/test-repo',
            'private': False,
            'description': 'Test repository'
        }
        mock_get.return_value = mock_response
        
        result = self.github_service.validate_repository_access('owner', 'test-repo')
        
        self.assertTrue(result['accessible'])
        self.assertEqual(result['repo_info']['name'], 'test-repo')
        self.assertFalse(result['repo_info']['private'])
    
    def test_validate_repository_endpoint(self):
        """Test repository validation endpoint"""
        with patch.object(self.github_service, 'parse_github_url') as mock_parse, \
             patch.object(self.github_service, 'validate_repository_access') as mock_validate:
            
            mock_parse.return_value = {'owner': 'owner', 'repo': 'repo'}
            mock_validate.return_value = {
                'accessible': True,
                'repo_info': {'name': 'repo', 'private': False}
            }
            
            response = self.app.post('/api/repositories/validate',
                                   data=json.dumps({'url': 'https://github.com/owner/repo'}),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertEqual(data['repository']['name'], 'repo')
    
    def test_analyze_repository_endpoint(self):
        """Test repository analysis endpoint"""
        with patch.object(self.github_service, 'parse_github_url') as mock_parse, \
             patch.object(self.github_service, 'validate_repository_access') as mock_validate, \
             patch.object(self.github_service, 'get_repository_tree') as mock_tree:
            
            mock_parse.return_value = {'owner': 'owner', 'repo': 'repo'}
            mock_validate.return_value = {
                'accessible': True,
                'repo_info': {'name': 'repo', 'private': False}
            }
            mock_tree.return_value = {
                'success': True,
                'tree': {'files': [], 'directories': [], 'total_files': 0}
            }
            
            response = self.app.post('/api/repositories/analyze',
                                   data=json.dumps({'url': 'https://github.com/owner/repo'}),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIn('analysis', data)

if __name__ == '__main__':
    unittest.main()