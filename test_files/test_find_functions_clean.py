#!/usr/bin/env python3
"""
Clean test to find specific functions and components in HazMap app (no warnings)
"""

# SUPPRESS ALL WARNINGS FIRST
import os
import sys
import warnings

# Set environment variables before importing anything
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['ORT_DISABLE_ALL_LOGS'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
warnings.filterwarnings('ignore')

# Now import everything else
from pathlib import Path
import logging

# Suppress all ML library logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('onnxruntime').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)
logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
logging.getLogger('chromadb').setLevel(logging.ERROR)

# Add services to path
sys.path.append(str(Path(__file__).parent))

try:
    from services.rag_system import CPUOptimizedRAGSystem
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_find_specific_functions():
    """Test finding specific functions and components (clean output)"""
    print("🔍 Testing Function & Component Discovery (Clean)")
    print("=" * 55)
    
    gitingest_file = "gitingest_outputs/Samay1011_Project_ecommerce_React_20250906_104832.txt"
    
    if not os.path.exists(gitingest_file):
        print(f"❌ Gitingest file not found: {gitingest_file}")
        return
    
    try:
        # Initialize RAG system
        print("🔧 Building RAG index...")
        rag = CPUOptimizedRAGSystem(storage_path="./clean_rag_storage")
        
        # Build RAG system (suppress output during build)
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                metrics = rag.build_rag_from_gitingest(gitingest_file, "clean_test")
            finally:
                sys.stdout = old_stdout
        
        print(f"✅ Indexed {metrics.total_chunks} chunks from {metrics.total_files} files")
        
        # Test specific searches with clean output
        searches = [
            ("authentication login", "Login functions"),
            ("wildfire prediction", "Prediction algorithm"),
            ("location GPS", "Location services"),
            ("air quality API", "cart"),
            ("map component", "request"),
            ("background tasks", "Background services"),
            ("user profile", "Profile management"),
            ("evacuation routes", "fetch")
        ]
        
        print(f"\n🎯 Testing {len(searches)} searches:")
        print("=" * 40)
        
        for i, (query, description) in enumerate(searches, 1):
            print(f"\n🔎 {i}. {description}")
            
            # Query with suppressed warnings
            with open(os.devnull, 'w') as devnull:
                old_stderr = sys.stderr
                sys.stderr = devnull
                try:
                    result = rag.query(query, max_results=3, collection_name="clean_test")
                finally:
                    sys.stderr = old_stderr
            
            # Show clean results
            if result.chunks:
                best_chunk = result.chunks[0]
                confidence = result.confidence_scores[0]
                
                confidence_emoji = "🎯" if confidence > 0.05 else "📍" if confidence > 0.01 else "📌"
                print(f"   {confidence_emoji} Found: {best_chunk.chunk_type} in {best_chunk.file_path}")
                
                if 'function_name' in best_chunk.metadata:
                    print(f"      Function: {best_chunk.metadata['function_name']}")
                elif 'class_name' in best_chunk.metadata:
                    print(f"      Class: {best_chunk.metadata['class_name']}")
                
                print(f"      Confidence: {confidence:.3f}")
                
                # Show additional matches if they're good
                for j in range(1, min(3, len(result.chunks))):
                    if result.confidence_scores[j] > 0.01:
                        chunk = result.chunks[j]
                        print(f"   📋 Also: {chunk.chunk_type} in {Path(chunk.file_path).name}")
            else:
                print("   ❌ No matches found")
        
        # Quick summary
        print(f"\n📊 Summary:")
        print(f"   📁 Files: {metrics.total_files}")
        print(f"   🧩 Chunks: {metrics.total_chunks}")
        print(f"   🌐 Languages: {', '.join(metrics.languages_detected)}")
        print(f"   💾 Size: {metrics.index_size_mb:.1f}MB")
        
        print(f"\n🎉 Clean function discovery complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        return 1
    
    finally:
        # Clean up
        try:
            if 'rag' in locals():
                rag.chroma_client = None
                rag.collection = None
            
            import shutil
            import time
            time.sleep(0.5)
            if os.path.exists("./clean_rag_storage"):
                print("🧹 Cleaning up...")
                shutil.rmtree("./clean_rag_storage")
        except Exception:
            pass  # Ignore cleanup errors
    
    return 0


if __name__ == "__main__":
    print("🔇 Warnings suppressed for clean output")
    exit_code = test_find_specific_functions()
    sys.exit(exit_code)