#!/usr/bin/env python3
"""
Test script for CPU-optimized RAG system.
This tests the complete pipeline from gitingest file to queryable RAG system.
"""

import asyncio
import sys
import os
from pathlib import Path
import time

# Add services to path
sys.path.append(str(Path(__file__).parent))

try:
    from services.rag_system import CPUOptimizedRAGSystem, GitingestParser
    from services.code_analyzer import MultiLanguageCodeAnalyzer
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure to install dependencies: pip install chromadb sentence-transformers networkx")
    sys.exit(1)


def test_gitingest_parsing():
    """Test parsing of gitingest files"""
    print("🧪 Testing gitingest parsing...")
    
    # Create a sample gitingest content
    sample_content = """
Directory structure:
├── main.py
├── utils.py
└── README.md

================================================================================

FILE: main.py
def hello_world():
    \"\"\"Simple hello world function\"\"\"
    print("Hello, World!")
    return "success"

if __name__ == "__main__":
    hello_world()

================================================================================

FILE: utils.py
import os
import sys

def get_file_size(filepath):
    \"\"\"Get file size in bytes\"\"\"
    return os.path.getsize(filepath)

class FileManager:
    def __init__(self, base_path):
        self.base_path = base_path
    
    def list_files(self):
        return os.listdir(self.base_path)

================================================================================

FILE: README.md
# Test Project

This is a test project for RAG system.
"""
    
    files = GitingestParser.parse_gitingest_content(sample_content)
    
    print(f"✅ Parsed {len(files)} files:")
    for file_path, content in files.items():
        print(f"  - {file_path} ({len(content)} chars)")
    
    return files


def test_code_analysis():
    """Test multi-language code analysis"""
    print("\n🧪 Testing code analysis...")
    
    # Get sample files from gitingest parsing
    files = test_gitingest_parsing()
    
    analyzer = MultiLanguageCodeAnalyzer()
    project_structure = analyzer.analyze_project(files)
    
    print(f"✅ Analyzed {len(project_structure)} files:")
    for file_path, structure in project_structure.items():
        print(f"  - {file_path}: {structure.language.value}")
        print(f"    Functions: {len(structure.functions)}")
        print(f"    Classes: {len(structure.classes)}")
        print(f"    Imports: {len(structure.imports)}")
    
    return project_structure


def test_rag_system():
    """Test complete RAG system"""
    print("\n🧪 Testing RAG system...")
    
    import tempfile
    
    # Use a temporary directory that gets cleaned up automatically
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize RAG system
        rag = CPUOptimizedRAGSystem(storage_path=temp_dir)
    
        # Create a temporary gitingest file
        temp_file = "temp_gitingest.txt"
    sample_content = """
Directory structure:
├── main.py
├── utils.py
└── calculator.py

================================================================================

FILE: main.py
def hello_world():
    \"\"\"Simple hello world function\"\"\"
    print("Hello, World!")
    return "success"

def main():
    \"\"\"Main entry point\"\"\"
    result = hello_world()
    calc = Calculator()
    sum_result = calc.add(5, 3)
    print(f"5 + 3 = {sum_result}")

if __name__ == "__main__":
    main()

================================================================================

FILE: utils.py
import os
import sys
from pathlib import Path

def get_file_size(filepath):
    \"\"\"Get file size in bytes\"\"\"
    return os.path.getsize(filepath)

def read_config(config_path):
    \"\"\"Read configuration file\"\"\"
    with open(config_path, 'r') as f:
        return f.read()

class FileManager:
    def __init__(self, base_path):
        self.base_path = base_path
    
    def list_files(self):
        \"\"\"List all files in base path\"\"\"
        return os.listdir(self.base_path)
    
    def create_file(self, filename, content):
        \"\"\"Create a new file\"\"\"
        filepath = Path(self.base_path) / filename
        with open(filepath, 'w') as f:
            f.write(content)

================================================================================

FILE: calculator.py
class Calculator:
    \"\"\"Simple calculator class\"\"\"
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        \"\"\"Add two numbers\"\"\"
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def subtract(self, a, b):
        \"\"\"Subtract two numbers\"\"\"
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
    
    def multiply(self, a, b):
        \"\"\"Multiply two numbers\"\"\"
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
    
    def get_history(self):
        \"\"\"Get calculation history\"\"\"
        return self.history.copy()
"""
    
    # Write temporary file
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    try:
        # Build RAG system
        print("Building RAG system...")
        metrics = rag.build_rag_from_gitingest(temp_file, "test_collection")
        
        print(f"✅ RAG system built successfully!")
        print(f"  - Total chunks: {metrics.total_chunks}")
        print(f"  - Total files: {metrics.total_files}")
        print(f"  - Languages: {', '.join(metrics.languages_detected)}")
        print(f"  - Build time: {metrics.build_time:.2f}s")
        print(f"  - Index size: {metrics.index_size_mb:.2f}MB")
        
        # Test queries
        test_queries = [
            "How do I add two numbers?",
            "Show me file management functions",
            "What is the main entry point?",
            "Find calculator methods"
        ]
        
        print(f"\n🔍 Testing queries...")
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            result = rag.query(query, max_results=3, collection_name="test_collection")
            
            print(f"  Found {len(result.chunks)} results in {result.query_time:.3f}s")
            for i, (chunk, confidence) in enumerate(zip(result.chunks, result.confidence_scores)):
                print(f"  {i+1}. {chunk.chunk_type} in {chunk.file_path} (confidence: {confidence:.2f})")
                print(f"     {chunk.content[:100]}...")
        
        # Test context generation
        print(f"\n📝 Testing context generation...")
        result = rag.query("calculator functions", max_results=5, collection_name="test_collection")
        context = rag.get_context_for_llm(result, max_tokens=1000)
        print(f"Generated context ({len(context)} chars):")
        print(context[:500] + "..." if len(context) > 500 else context)
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Clean up test storage - close ChromaDB first
        try:
            if 'rag' in locals():
                rag.cleanup()
            
            import shutil
            import time
            import gc
            
            # Force garbage collection to release file handles
            gc.collect()
            time.sleep(2)  # Give more time for file handles to close
            
            if os.path.exists("./test_rag_storage"):
                shutil.rmtree("./test_rag_storage")
        except Exception as e:
            print(f"Warning: Could not clean up test storage: {e}")
            print("You may need to manually delete the ./test_rag_storage folder")


def main():
    """Run all tests"""
    print("🚀 Starting RAG System Tests")
    print("=" * 50)
    
    try:
        # Test individual components
        test_gitingest_parsing()
        test_code_analysis()
        
        # Test complete system
        test_rag_system()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)