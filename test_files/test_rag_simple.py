#!/usr/bin/env python3
"""
Simple test for CPU-optimized RAG system.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add services to path
sys.path.append(str(Path(__file__).parent))

try:
    from services.rag_system import CPUOptimizedRAGSystem, GitingestParser
    from services.code_analyzer import MultiLanguageCodeAnalyzer
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_simple_rag():
    """Test basic RAG functionality"""
    print("🚀 Testing CPU-Optimized RAG System")
    print("=" * 50)
    
    # Sample gitingest content
    sample_content = """
Directory structure:
├── calculator.py
└── main.py

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
    
    def multiply(self, a, b):
        \"\"\"Multiply two numbers\"\"\"
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

================================================================================

FILE: main.py
from calculator import Calculator

def main():
    \"\"\"Main function\"\"\"
    calc = Calculator()
    result = calc.add(5, 3)
    print(f"5 + 3 = {result}")
    
    product = calc.multiply(4, 6)
    print(f"4 * 6 = {product}")

if __name__ == "__main__":
    main()
"""
    
    # Use a persistent directory instead of temp
    storage_dir = "./rag_test_storage"
    
    try:
        # Clean up any existing storage
        if os.path.exists(storage_dir):
            import shutil
            try:
                shutil.rmtree(storage_dir)
            except:
                pass
        
        # Create gitingest file
        gitingest_file = "test_sample.txt"
        with open(gitingest_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        print("📝 Created sample gitingest file")
        
        # Initialize RAG system
        print("🔧 Initializing RAG system...")
        rag = CPUOptimizedRAGSystem(storage_path=storage_dir)
        
        # Build RAG system
        print("🏗️ Building RAG system...")
        metrics = rag.build_rag_from_gitingest(gitingest_file, "test_collection")
        
        print(f"✅ RAG system built successfully!")
        print(f"  - Total chunks: {metrics.total_chunks}")
        print(f"  - Total files: {metrics.total_files}")
        print(f"  - Languages: {', '.join(metrics.languages_detected)}")
        print(f"  - Build time: {metrics.build_time:.2f}s")
        print(f"  - Index size: {metrics.index_size_mb:.2f}MB")
        
        # Test queries
        test_queries = [
            "How do I add two numbers?",
            "Show me calculator methods",
            "What is the main function?",
            "Find multiplication function"
        ]
        
        print(f"\n🔍 Testing queries...")
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            result = rag.query(query, max_results=3, collection_name="test_collection")
            
            print(f"  Found {len(result.chunks)} results in {result.query_time:.3f}s")
            for i, (chunk, confidence) in enumerate(zip(result.chunks, result.confidence_scores)):
                print(f"  {i+1}. {chunk.chunk_type} in {chunk.file_path} (confidence: {confidence:.2f})")
                print(f"     {chunk.content[:80]}...")
        
        # Test context generation
        print(f"\n📝 Testing context generation...")
        result = rag.query("calculator functions", max_results=5, collection_name="test_collection")
        context = rag.get_context_for_llm(result, max_tokens=1000)
        print(f"Generated context ({len(context)} chars):")
        print(context[:300] + "..." if len(context) > 300 else context)
        
        print(f"\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up files
        try:
            if os.path.exists(gitingest_file):
                os.remove(gitingest_file)
        except:
            pass
        
        # Note: We'll leave the storage directory for manual cleanup
        # since Windows file locking makes automatic cleanup difficult
        print(f"\n💡 Note: Test storage left at '{storage_dir}' for manual cleanup if needed")


if __name__ == "__main__":
    success = test_simple_rag()
    sys.exit(0 if success else 1)