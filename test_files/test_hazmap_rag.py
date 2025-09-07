#!/usr/bin/env python3
"""
Test RAG system with HazMap app gitingest output
"""

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
    sys.exit(1)


def test_hazmap_rag():
    """Test RAG system with HazMap app"""
    print("🚀 Testing RAG System with HazMap App")
    print("=" * 60)
    
    gitingest_file = "gitingest_outputs/Emon69420_HazMapApp_20250905_194000.txt"
    
    if not os.path.exists(gitingest_file):
        print(f"❌ Gitingest file not found: {gitingest_file}")
        return
    
    try:
        # Initialize RAG system
        print("🔧 Initializing RAG system...")
        rag = CPUOptimizedRAGSystem(storage_path="./hazmap_rag_storage")
        
        # Build RAG system from HazMap gitingest
        print("📊 Building RAG system from HazMap codebase...")
        start_time = time.time()
        
        metrics = rag.build_rag_from_gitingest(gitingest_file, "hazmap_collection")
        
        build_time = time.time() - start_time
        
        print(f"\n✅ RAG system built successfully!")
        print(f"  📁 Total files: {metrics.total_files}")
        print(f"  🧩 Total chunks: {metrics.total_chunks}")
        print(f"  🌐 Languages: {', '.join(metrics.languages_detected)}")
        print(f"  ⏱️  Build time: {build_time:.2f}s")
        print(f"  💾 Index size: {metrics.index_size_mb:.2f}MB")
        
        # Test queries relevant to HazMap
        test_queries = [
            "How do I implement location tracking?",
            "Show me authentication code",
            "How is the map component implemented?",
            "Find air quality monitoring functions",
            "How does wildfire risk prediction work?",
            "Show me background task implementation",
            "How is user profile managed?",
            "Find evacuation route planning code",
            "How are notifications handled?",
            "Show me the database configuration",
            "How is the Google Maps API integrated?",
            "Find React Native navigation setup",
            "How are environmental data fetched?",
            "Show me TypeScript interfaces",
            "How is the app styled?"
        ]
        
        print(f"\n🔍 Testing {len(test_queries)} queries...")
        print("=" * 60)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔎 Query {i}: '{query}'")
            
            query_start = time.time()
            result = rag.query(query, max_results=5, collection_name="hazmap_collection")
            query_time = time.time() - query_start
            
            print(f"  ⚡ Found {len(result.chunks)} results in {query_time:.3f}s")
            
            # Show top 3 results
            for j, (chunk, confidence) in enumerate(zip(result.chunks[:3], result.confidence_scores[:3])):
                print(f"    {j+1}. {chunk.chunk_type} in {chunk.file_path} (confidence: {confidence:.2f})")
                # Show a snippet of the content
                content_preview = chunk.content.replace('\n', ' ')[:100]
                print(f"       Preview: {content_preview}...")
            
            if result.relationships and any(result.relationships.values()):
                print(f"    🔗 Related: {', '.join([f'{k}: {len(v)}' for k, v in result.relationships.items() if v])}")
        
        # Test context generation for LLM
        print(f"\n📝 Testing context generation...")
        test_context_query = "How does the HazMap app handle real-time wildfire monitoring and user notifications?"
        
        result = rag.query(test_context_query, max_results=8, collection_name="hazmap_collection")
        context = rag.get_context_for_llm(result, max_tokens=2000)
        
        print(f"  📄 Generated context ({len(context)} chars):")
        print(f"  Preview: {context[:300]}...")
        
        # Show some interesting statistics
        print(f"\n📊 HazMap Codebase Analysis:")
        
        # Parse the gitingest file to get file breakdown
        files = GitingestParser.parse_gitingest_file(gitingest_file)
        analyzer = MultiLanguageCodeAnalyzer()
        project_structure = analyzer.analyze_project(files)
        
        # Language breakdown
        lang_stats = {}
        for structure in project_structure.values():
            lang = structure.language.value
            if lang not in lang_stats:
                lang_stats[lang] = {'files': 0, 'functions': 0, 'classes': 0, 'lines': 0}
            lang_stats[lang]['files'] += 1
            lang_stats[lang]['functions'] += len(structure.functions)
            lang_stats[lang]['classes'] += len(structure.classes)
            lang_stats[lang]['lines'] += structure.total_lines
        
        for lang, stats in sorted(lang_stats.items(), key=lambda x: x[1]['lines'], reverse=True):
            if stats['files'] > 0:
                print(f"  🔤 {lang.upper()}: {stats['files']} files, {stats['functions']} functions, {stats['classes']} classes, {stats['lines']} lines")
        
        # Find key components
        key_files = []
        for file_path, structure in project_structure.items():
            if any(keyword in file_path.lower() for keyword in ['map', 'auth', 'profile', 'air-quality', 'evacuation']):
                key_files.append((file_path, len(structure.functions), len(structure.classes)))
        
        if key_files:
            print(f"\n🎯 Key Components Found:")
            for file_path, func_count, class_count in sorted(key_files, key=lambda x: x[1] + x[2], reverse=True)[:10]:
                print(f"  📄 {file_path}: {func_count} functions, {class_count} classes")
        
        print(f"\n🎉 HazMap RAG analysis complete!")
        
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
            time.sleep(1)
            if os.path.exists("./hazmap_rag_storage"):
                print("🧹 Cleaning up storage...")
                shutil.rmtree("./hazmap_rag_storage")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up storage: {e}")
    
    return 0


if __name__ == "__main__":
    exit_code = test_hazmap_rag()
    sys.exit(exit_code)