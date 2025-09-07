#!/usr/bin/env python3
"""
Ultra-clean test with maximum warning suppression
"""

import os
import sys
import warnings
import subprocess

# Maximum suppression
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['ORT_DISABLE_ALL_LOGS'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

from pathlib import Path
import logging

# Suppress all logging
logging.disable(logging.CRITICAL)

sys.path.append(str(Path(__file__).parent))

def run_silent_test():
    """Run the test with maximum output suppression"""
    print("🔇 Running SILENT RAG test...")
    print("=" * 40)
    
    try:
        from services.rag_system import CPUOptimizedRAGSystem
        
        gitingest_file = "gitingest_outputs/Emon69420_HazMapApp_20250905_194000.txt"
        
        if not os.path.exists(gitingest_file):
            print(f"❌ File not found: {gitingest_file}")
            return
        
        print("🔧 Building index (silent)...")
        
        # Redirect ALL output during initialization
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            
            try:
                rag = CPUOptimizedRAGSystem(storage_path="./silent_rag")
                metrics = rag.build_rag_from_gitingest(gitingest_file, "silent_test")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        
        print(f"✅ Success! {metrics.total_chunks} chunks from {metrics.total_files} files")
        
        # Test key searches silently
        searches = [
            ("login authentication", "🔐 Login"),
            ("wildfire prediction", "🔥 Wildfire"),
            ("location GPS", "📍 Location"),
            ("map component", "🗺️  Map"),
            ("background task", "⏰ Background"),
            ("user profile", "👤 Profile")
        ]
        
        print(f"\n🎯 Testing {len(searches)} searches:")
        
        for query, emoji_desc in searches:
            # Silent query
            with open(os.devnull, 'w') as devnull:
                old_stderr = sys.stderr
                sys.stderr = devnull
                try:
                    result = rag.query(query, max_results=1, collection_name="silent_test")
                finally:
                    sys.stderr = old_stderr
            
            if result.chunks:
                chunk = result.chunks[0]
                confidence = result.confidence_scores[0]
                
                # Clean output
                file_name = Path(chunk.file_path).name
                func_name = chunk.metadata.get('function_name', 'N/A')
                
                status = "🎯" if confidence > 0.05 else "✅" if confidence > 0.01 else "📌"
                print(f"   {status} {emoji_desc}: {func_name} in {file_name}")
        
        print(f"\n📊 Index: {metrics.total_files} files, {metrics.total_chunks} chunks, {metrics.index_size_mb:.1f}MB")
        print("🎉 Silent test complete!")
        
        # Silent cleanup
        try:
            rag.chroma_client = None
            rag.collection = None
            import shutil
            import time
            time.sleep(0.5)
            if os.path.exists("./silent_rag"):
                shutil.rmtree("./silent_rag")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_silent_test()