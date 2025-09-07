#!/usr/bin/env python3
"""
Utility to suppress ONNX Runtime warnings and other verbose output
"""

import os
import sys
import warnings
import logging

def suppress_all_warnings():
    """Suppress all the annoying warnings from ML libraries"""
    
    # 1. Suppress TensorFlow warnings
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Only show errors
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN warnings
    
    # 2. Suppress ONNX Runtime warnings
    os.environ['ORT_DISABLE_ALL_LOGS'] = '1'
    
    # 3. Suppress Python warnings
    warnings.filterwarnings('ignore')
    
    # 4. Suppress specific library warnings
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
    logging.getLogger('onnxruntime').setLevel(logging.ERROR)
    logging.getLogger('transformers').setLevel(logging.ERROR)
    logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
    logging.getLogger('chromadb').setLevel(logging.ERROR)
    
    # 5. Redirect stderr temporarily to suppress C++ warnings
    import contextlib
    
    @contextlib.contextmanager
    def suppress_stderr():
        with open(os.devnull, "w") as devnull:
            old_stderr = sys.stderr
            sys.stderr = devnull
            try:
                yield
            finally:
                sys.stderr = old_stderr
    
    return suppress_stderr

# Call this at the start of any script
def setup_clean_environment():
    """Set up a clean environment without warnings"""
    suppress_all_warnings()
    
    # Also suppress the specific ONNX warnings by setting environment variables
    os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Force CPU-only
    os.environ['OMP_NUM_THREADS'] = '1'  # Reduce threading warnings
    
    print("🔇 Warnings suppressed - clean output enabled!")

if __name__ == "__main__":
    setup_clean_environment()
    print("✅ Warning suppression configured!")