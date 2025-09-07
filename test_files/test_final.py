#!/usr/bin/env python3
"""
Final clean RAG test - no warnings, no Unicode issues
"""

import os
import sys
import warnings

# Suppress everything
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

from pathlib import Path
import logging
logging.disable(logging.CRITICAL)

sys.path.append(str(Path(__file__).parent))

def main():
    print("Running Clean RAG Test")
    print("=" * 30)
    
    try:
        from services.rag_system import CPUOptimizedRAGSystem
        
        gitingest_file = "gitingest_outputs/Emon69420_HazMapApp_20250905_194000.txt"
        
        if not os.path.exists(gitingest_file):
            print(f"File not found: {gitingest_file}")
            return
        
        print("Building RAG index...")
        
        # Silent build
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            
            try:
                rag = CPUOptimizedRAGSystem(storage_path="./final_rag")
                metrics = rag.build_rag_from_gitingest(gitingest_file, "final_test")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        
        print(f"SUCCESS: {metrics.total_chunks} chunks from {metrics.total_files} files")
        
        # Test searches
        searches = [
            ("login authentication", "Login"),
            ("wildfire prediction", "Wildfire"),
            ("location GPS", "Location"),
            ("map component", "Map"),
            ("background task", "Background"),
            ("user profile", "Profile")
        ]
        
        print(f"\nTesting {len(searches)} searches:")
        
        for query, desc in searches:
            # Silent query
            with open(os.devnull, 'w') as devnull:
                old_stderr = sys.stderr
                sys.stderr = devnull
                try:
                    result = rag.query(query, max_results=1, collection_name="final_test")
                finally:
                    sys.stderr = old_stderr
            
            if result.chunks:
                chunk = result.chunks[0]
                file_name = Path(chunk.file_path).name
                func_name = chunk.metadata.get('function_name', 'N/A')
                print(f"  {desc}: {func_name} in {file_name}")
        
        print(f"\nSummary: {metrics.total_files} files, {metrics.total_chunks} chunks")
        print("Test complete!")
        
        # Cleanup
        try:
            rag.chroma_client = None
            rag.collection = None
            import shutil
            import time
            time.sleep(0.5)
            if os.path.exists("./final_rag"):
                shutil.rmtree("./final_rag")
        except:
            pass
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()