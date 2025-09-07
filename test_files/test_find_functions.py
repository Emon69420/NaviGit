#!/usr/bin/env python3
"""

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


def test_find_specific_functions():
    """Test finding specific functions and components"""
    print("🔍 Testing Function & Component Discovery")
    print("=" * 50)
    
    gitingest_file = "https://github.com/Emon69420/MedMint"
    
    if not os.path.exists(gitingest_file):
        print(f"❌ Gitingest file not found: {gitingest_file}")
        return
    
    try:
        # Initialize RAG system
        print("🔧 Building RAG index...")
        rag = CPUOptimizedRAGSystem(storage_path="./temp_rag_storage")
        
        # Build RAG system
        metrics = rag.build_rag_from_gitingest(gitingest_file, "find_functions_test")
        print(f"✅ Indexed {metrics.total_chunks} chunks from {metrics.total_files} files")
        
        # Test specific function/component searches
        searches = [
            {
                "query": "authentication login function",
                "expect": "Should find login-related code"
            },
            {
                "query": "wildfire risk prediction algorithm",
                "expect": "Should find prediction functions in Flask backend"
            },
            {
                "query": "Flask backend get_wildfire_risk_prediction function",
                "expect": "Should find the main Python prediction function"
            },
            {
                "query": "gee_data Google Earth Engine API",
                "expect": "Should find the GEE data processing function"
            },
            {
                "query": "Python Flask route handler",
                "expect": "Should find Flask route functions like home and about"
            },
            {
                "query": "environmental data processing Python",
                "expect": "Should find Python functions that process environmental data"
            },
            {
                "query": "location tracking GPS coordinates",
                "expect": "Should find LocationContext and location services"
            },
            {
                "query": "air quality monitoring API calls",
                "expect": "Should find air quality related functions"
            },
            {
                "query": "React Native map component MapView",
                "expect": "Should find map implementation"
            },
            {
                "query": "background task notification system",
                "expect": "Should find background task services"
            },
            {
                "query": "user profile management settings",
                "expect": "Should find profile screen and user management"
            },
            {
                "query": "evacuation route planning emergency",
                "expect": "Should find evacuation-related components"
            },
            {
                "query": "Python test functions pytest",
                "expect": "Should find test functions in test_app.py"
            },
            {
                "query": "Flask app configuration setup",
                "expect": "Should find Flask app initialization and config"
            }
        ]
        
        print(f"\n🎯 Testing {len(searches)} specific searches:")
        print("=" * 50)
        
        for i, search in enumerate(searches, 1):
            print(f"\n🔎 Search {i}: '{search['query']}'")
            print(f"   Expected: {search['expect']}")
            
            # Query the RAG system
            result = rag.query(search['query'], max_results=3, collection_name="find_functions_test")
            
            print(f"   ⚡ Found {len(result.chunks)} results:")
            
            # Show results with confidence scores
            for j, (chunk, confidence) in enumerate(zip(result.chunks, result.confidence_scores)):
                confidence_emoji = "🎯" if confidence > 0.1 else "📍" if confidence > 0.05 else "📌"
                print(f"     {confidence_emoji} {chunk.chunk_type} in {chunk.file_path}")
                print(f"        Confidence: {confidence:.3f}")
                
                # Show content preview
                preview = chunk.content.replace('\n', ' ')[:80]
                print(f"        Preview: {preview}...")
                
                # Show metadata if available
                if chunk.metadata:
                    relevant_meta = {}
                    for key in ['function_name', 'class_name', 'method_name']:
                        if key in chunk.metadata and chunk.metadata[key]:
                            relevant_meta[key] = chunk.metadata[key]
                    if relevant_meta:
                        print(f"        Metadata: {relevant_meta}")
            
            # Show relationships if found
            if result.relationships and any(result.relationships.values()):
                related_info = []
                for rel_type, items in result.relationships.items():
                    if items:
                        related_info.append(f"{rel_type}: {len(items)}")
                if related_info:
                    print(f"   🔗 Related: {', '.join(related_info)}")
        
        # Test finding specific code patterns
        print(f"\n🧩 Testing Code Pattern Discovery:")
        print("=" * 30)
        
        pattern_searches = [
            "async function with await",
            "React useState hook",
            "API fetch request",
            "error handling try catch",
            "TypeScript interface definition",
            "Python Flask route decorator",
            "Python function with parameters",
            "Python import statement",
            "Python class definition",
            "Python exception handling try except"
        ]
        
        for pattern in pattern_searches:
            print(f"\n🔍 Pattern: '{pattern}'")
            result = rag.query(pattern, max_results=2, collection_name="find_functions_test")
            
            for chunk, confidence in zip(result.chunks[:2], result.confidence_scores[:2]):
                if confidence > 0.01:  # Only show if there's some relevance
                    print(f"   📄 {chunk.file_path} (confidence: {confidence:.3f})")
                    # Show a longer preview for code patterns
                    preview = chunk.content.replace('\n', ' ')[:120]
                    print(f"      {preview}...")
        
        # Summary of what we found
        print(f"\n📊 Discovery Summary:")
        print("=" * 20)
        
        # Get all chunks to analyze what we have
        all_results = rag.query("*", max_results=50, collection_name="find_functions_test")
        
        # Count by file type
        file_types = {}
        chunk_types = {}
        
        for chunk in all_results.chunks:
            # File extension
            ext = Path(chunk.file_path).suffix or 'no-ext'
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Chunk type
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
        
        print("📁 File types indexed:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {ext}: {count} chunks")
        
        print("\n🧩 Chunk types created:")
        for chunk_type, count in sorted(chunk_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {chunk_type}: {count} chunks")
        
        print(f"\n🎉 Function discovery test complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Clean up
        try:
            if 'rag' in locals():
                rag.chroma_client = None
                rag.collection = None
            
            import shutil
            import time
            time.sleep(1)
            if os.path.exists("./temp_rag_storage"):
                print("🧹 Cleaning up...")
                shutil.rmtree("./temp_rag_storage")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up: {e}")
    
    return 0


if __name__ == "__main__":
    exit_code = test_find_specific_functions()
    sys.exit(exit_code)