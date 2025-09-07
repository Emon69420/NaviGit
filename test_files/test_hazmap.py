#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:5000"

def test_hazmap_analysis():
    print("Analyzing HazMapApp repository...")
    
    url = f"{BASE_URL}/api/repositories/analyze"
    data = {"url": "https://github.com/Emon69420/HazMapApp"}
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        analysis = result['analysis']
        
        print(f"Repository: {analysis['repository']['full_name']}")
        print(f"Description: {analysis['repository']['description']}")
        print(f"Language: {analysis['repository']['language']}")
        print(f"Size: {analysis['repository']['size']} KB")
        print(f"Stars: {analysis['repository']['stargazers_count']}")
        print(f"Default branch: {analysis['repository']['default_branch']}")
        print()
        
        structure = analysis['structure']
        print(f"Total files: {structure['total_files']}")
        print(f"Total directories: {structure['total_directories']}")
        print()
        
        print("File structure (first 10 files):")
        for file in structure['files'][:10]:
            print(f"  - {file['path']} ({file['size']} bytes)")
        
        if len(structure['files']) > 10:
            print(f"  ... and {len(structure['files']) - 10} more files")
        
    else:
        print(f"Error: {response.json()}")

def test_get_readme():
    print("\nGetting README.md content...")
    
    url = f"{BASE_URL}/api/repositories/Emon69420/HazMapApp/files/README.md"
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        file_info = result['file']
        
        print(f"File: {file_info['name']}")
        print(f"Size: {file_info['size']} bytes")
        print(f"Encoding: {file_info['encoding']}")
        print(f"Download URL: {file_info['download_url']}")
        
        # Decode base64 content if available
        if file_info['content'] and file_info['encoding'] == 'base64':
            import base64
            content = base64.b64decode(file_info['content']).decode('utf-8')
            print("\nREADME content (first 500 chars):")
            print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print(f"Error: {response.json()}")

if __name__ == "__main__":
    try:
        test_hazmap_analysis()
        test_get_readme()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Flask server.")
        print("Make sure the server is running with: python app.py")
    except Exception as e:
        print(f"Error: {e}")