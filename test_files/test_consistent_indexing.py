#!/usr/bin/env python3
"""
Test to check consistency of RAG indexing across multiple runs
"""

import sys
import os
from pathlib import Path

# Add services to path
sys.path.append(str(Path(__file__).parent))

try:
    from services.rag_system import CPUOptimizedRAGSystem
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def run_indexing_test(run_number):
    """Run a single indexing test and return metrics"""
    print(f"\n🔄 Run {run_number}:")
    print("-" * 30)
    
    gitingest_file = "gitingest_outputs/Samay1011_Project_ecommerce_React_20250906_104832.txt"
    
    if not os.path.exists(gitingest_file):
        print(f"❌ Gitingest file not found: {gitingest_file}")
        return None
    
    try:
        # Initialize RAG system with unique storage path
        storage_path = f"./temp_consistency_test_{run_number}"
        rag = CPUOptimizedRAGSystem(storage_path=storage_path)
        
        # Build RAG system
        metrics = rag.build_rag_from_gitingest(gitingest_file, f"consistency_test_{run_number}")
        print(f"✅ Indexed {metrics.total_chunks} chunks from {metrics.total_files} files")
        
        # Get all chunks to analyze
        all_results = rag.query("*", max_results=200, collection_name=f"consistency_test_{run_number}")
        
        # Count by file type
        file_types = {}
        chunk_types = {}
        python_files = []
        
        for chunk in all_results.chunks:
            # File extension
            ext = Path(chunk.file_path).suffix or 'no-ext'
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Chunk type
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
            
            # Track Python files specifically
            if ext == '.py':
                python_files.append({
                    'file': chunk.file_path,
                    'type': chunk.chunk_type,
                    'content_preview': chunk.content[:100].replace('\n', ' ')
                })
        
        print("📁 File types:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {ext}: {count}")
        
        print("🧩 Chunk types:")
        for chunk_type, count in sorted(chunk_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {chunk_type}: {count}")
        
        if python_files:
            print("🐍 Python files found:")
            for py_file in python_files:
                print(f"   {py_file['type']}: {py_file['file']}")
                print(f"      Preview: {py_file['content_preview']}...")
        
        return {
            'total_chunks': metrics.total_chunks,
            'total_files': metrics.total_files,
            'file_types': file_types,
            'chunk_types': chunk_types,
            'python_files': python_files
        }
        
    except Exception as e:
        print(f"❌ Run {run_number} failed: {str(e)}")
        return None
    
    finally:
        # Clean up
        try:
            if 'rag' in locals():
                rag.chroma_client = None
                rag.collection = None
            
            import shutil
            import time
            time.sleep(0.5)
            if os.path.exists(storage_path):
                shutil.rmtree(storage_path)
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up run {run_number}: {e}")


def test_consistency():
    """Test consistency across multiple runs"""
    print("🔍 Testing RAG Indexing Consistency")
    print("=" * 50)
    
    results = []
    num_runs = 3
    
    for i in range(1, num_runs + 1):
        result = run_indexing_test(i)
        if result:
            results.append(result)
    
    if len(results) < 2:
        print("❌ Not enough successful runs to compare")
        return
    
    print(f"\n📊 Consistency Analysis ({len(results)} runs):")
    print("=" * 40)
    
    # Compare total counts
    chunk_counts = [r['total_chunks'] for r in results]
    file_counts = [r['total_files'] for r in results]
    
    print(f"📦 Total chunks: {chunk_counts}")
    print(f"📁 Total files: {file_counts}")
    
    if len(set(chunk_counts)) == 1:
        print("✅ Chunk counts are consistent")
    else:
        print("⚠️  Chunk counts vary between runs")
    
    if len(set(file_counts)) == 1:
        print("✅ File counts are consistent")
    else:
        print("⚠️  File counts vary between runs")
    
    # Compare file type distributions
    print(f"\n📁 File Type Consistency:")
    all_extensions = set()
    for result in results:
        all_extensions.update(result['file_types'].keys())
    
    for ext in sorted(all_extensions):
        counts = [result['file_types'].get(ext, 0) for result in results]
        if len(set(counts)) == 1:
            print(f"   {ext}: {counts[0]} ✅")
        else:
            print(f"   {ext}: {counts} ⚠️")
    
    # Compare Python file detection
    print(f"\n🐍 Python File Detection:")
    py_file_counts = [len(r['python_files']) for r in results]
    print(f"Python chunks found: {py_file_counts}")
    
    if len(set(py_file_counts)) == 1:
        print("✅ Python file detection is consistent")
    else:
        print("⚠️  Python file detection varies")
        
        # Show what Python files were found in each run
        for i, result in enumerate(results, 1):
            print(f"  Run {i} Python files:")
            for py_file in result['python_files']:
                print(f"    - {py_file['file']} ({py_file['type']})")


if __name__ == "__main__":
    test_consistency()