#!/usr/bin/env python3
import requests
import json

# Test with a well-known public repository
BASE_URL = "http://localhost:5000"

def test_with_known_repo():
    print("Testing with octocat/Hello-World (known public repo)...")
    
    url = f"{BASE_URL}/api/repositories/validate"
    data = {"url": "https://github.com/octocat/Hello-World"}
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_with_your_repo():
    print("Testing with Emon69420/HazMapApp...")
    
    url = f"{BASE_URL}/api/repositories/validate"
    data = {"url": "https://github.com/Emon69420/HazMapApp"}
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

if __name__ == "__main__":
    try:
        test_with_known_repo()
        test_with_your_repo()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Flask server.")
        print("Make sure the server is running with: python app.py")
    except Exception as e:
        print(f"Error: {e}")