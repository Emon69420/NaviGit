#!/usr/bin/env python3
"""
Simple test script to verify the API endpoints work correctly
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_repository_validation():
    """Test repository validation endpoint"""
    print("Testing repository validation...")
    
    url = f"{BASE_URL}/api/repositories/validate"
    data = {"url": "https://github.com/Emon69420/HazMapApp"}
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_repository_analysis():
    """Test repository analysis endpoint"""
    print("Testing repository analysis...")
    
    url = f"{BASE_URL}/api/repositories/analyze"
    data = {"url": "https://github.com/Emon69420/HazMapApp"}
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_repository_tree():
    """Test repository tree endpoint"""
    print("Testing repository tree...")
    
    url = f"{BASE_URL}/api/repositories/Emon69420/HazMapApp/tree"
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    result = response.json()
    if 'tree' in result:
        print(f"Files found: {result['tree']['total_files']}")
        print(f"Directories found: {result['tree']['total_directories']}")
        # Show first few files
        files = result['tree']['files'][:5]
        print("Sample files:")
        for file in files:
            print(f"  - {file['path']}")
    else:
        print(f"Response: {result}")
    print()

def test_file_content():
    """Test file content endpoint"""
    print("Testing file content...")
    
    url = f"{BASE_URL}/api/repositories/Emon69420/HazMapApp/files/README.md"
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    result = response.json()
    if 'file' in result:
        print(f"File: {result['file']['name']}")
        print(f"Size: {result['file']['size']} bytes")
        print(f"Encoding: {result['file']['encoding']}")
    else:
        print(f"Response: {result}")
    print()

if __name__ == "__main__":
    print("Testing AI Project Analyzer API endpoints")
    print("=" * 50)
    
    try:
        test_repository_validation()
        test_repository_analysis()
        test_repository_tree()
        test_file_content()
        
        print("All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Flask server.")
        print("Make sure the server is running with: python app.py")
    except Exception as e:
        print(f"Error: {e}")