"""
CPU-Optimized RAG System for Code Analysis

This module provides a complete RAG (Retrieval-Augmented Generation) system
optimized for CPU-only environments. It combines ChromaDB vector storage with
NetworkX relationship graphs for intelligent code analysis.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("Sentence Transformers not available, using basic embeddings")

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("NetworkX not available")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken not available")

from .code_analyzer import MultiLanguageCodeAnalyzer, CodeStructure, ProgrammingLanguage

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """Represents a chunk of code for RAG processing"""
    chunk_id: str
    content: str
    file_path: str
    chunk_type: str  # function, class, file, import, etc.
    language: str
    start_line: int
    end_line: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class QueryResult:
    """Result from RAG query"""
    chunks: List[CodeChunk]
    relationships: Dict[str, Any]
    confidence_scores: List[float]
    query_time: float
    total_chunks_searched: int


@dataclass
class RAGMetrics:
    """Metrics for RAG system performance"""
    total_chunks: int
    total_files: int
    languages_detected: List[str]
    build_time: float
    index_size_mb: float
    last_updated: str


class GitingestParser:
    """Parses gitingest output into structured format"""
    
    @staticmethod
    def parse_gitingest_file(file_path: str) -> Dict[str, str]:
        """Parse gitingest .txt file and extract all files with content"""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return GitingestParser.parse_gitingest_content(content)
    
    @staticmethod
    def parse_gitingest_content(content: str) -> Dict[str, str]:
        """Parse gitingest content and extract files"""
        files = {}
        lines = content.split('\n')
        
        current_file = None
        current_content = []
        in_file_section = False
        
        for line in lines:
            # Detect file headers
            if line.startswith('FILE: '):
                # Save previous file
                if current_file and current_content:
                    # Remove empty lines at the end
                    while current_content and not current_content[-1].strip():
                        current_content.pop()
                    files[current_file] = '\n'.join(current_content)
                
                # Start new file
                current_file = line.replace('FILE: ', '').strip()
                current_content = []
                in_file_section = True
                
            elif line.startswith('=') and len(line) > 10:
                # Skip separator lines
                continue
                
            elif line.startswith('Directory structure:'):
                # Skip directory structure section
                in_file_section = False
                current_file = None
                
            elif in_file_section and current_file:
                # Add content line
                current_content.append(line)
        
        # Add last file
        if current_file and current_content:
            while current_content and not current_content[-1].strip():
                current_content.pop()
            files[current_file] = '\n'.join(current_content)
        
        return files


class CodeChunker:
    """Creates intelligent chunks from code structure"""
    
    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size
        if TIKTOKEN_AVAILABLE:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        else:
            self.tokenizer = None
    
    def create_chunks(self, project_structure: Dict[str, CodeStructure]) -> List[CodeChunk]:
        """Create intelligent chunks from project structure"""
        chunks = []
        
        for file_path, structure in project_structure.items():
            # Create chunks for functions
            for func in structure.functions:
                chunk = self._create_function_chunk(func, file_path, structure.language)
                chunks.append(chunk)
            
            # Create chunks for classes
            for cls in structure.classes:
                chunk = self._create_class_chunk(cls, file_path, structure.language)
                chunks.append(chunk)
                
                # Create chunks for methods
                for method in cls.methods:
                    chunk = self._create_method_chunk(method, cls.name, file_path, structure.language)
                    chunks.append(chunk)
            
            # Create chunks for imports
            if structure.imports:
                chunk = self._create_imports_chunk(structure.imports, file_path, structure.language)
                chunks.append(chunk)
            
            # Create file-level chunk for small files
            if structure.total_lines < 50:
                chunk = self._create_file_chunk(structure, file_path)
                chunks.append(chunk)
        
        return chunks
    
    def _create_function_chunk(self, func, file_path: str, language: ProgrammingLanguage) -> CodeChunk:
        """Create chunk for a function"""
        chunk_id = self._generate_chunk_id(file_path, func.name, "function")
        
        # Build content with context
        content_parts = [
            f"Function: {func.name}",
            f"File: {file_path}",
            f"Language: {language.value}",
            f"Parameters: {', '.join(func.parameters)}",
        ]
        
        if func.docstring:
            content_parts.append(f"Description: {func.docstring}")
        
        if func.calls:
            content_parts.append(f"Calls: {', '.join(func.calls)}")
        
        content = '\n'.join(content_parts)
        
        return CodeChunk(
            chunk_id=chunk_id,
            content=content,
            file_path=file_path,
            chunk_type="function",
            language=language.value,
            start_line=func.start_line,
            end_line=func.end_line,
            metadata={
                "function_name": func.name,
                "parameters": func.parameters,
                "calls": func.calls,
                "complexity": func.complexity,
                "is_async": func.is_async,
                "return_type": func.return_type
            }
        )
    
    def _create_class_chunk(self, cls, file_path: str, language: ProgrammingLanguage) -> CodeChunk:
        """Create chunk for a class"""
        chunk_id = self._generate_chunk_id(file_path, cls.name, "class")
        
        content_parts = [
            f"Class: {cls.name}",
            f"File: {file_path}",
            f"Language: {language.value}",
            f"Methods: {', '.join([m.name for m in cls.methods])}",
        ]
        
        if cls.docstring:
            content_parts.append(f"Description: {cls.docstring}")
        
        if cls.inherits_from:
            content_parts.append(f"Inherits from: {', '.join(cls.inherits_from)}")
        
        content = '\n'.join(content_parts)
        
        return CodeChunk(
            chunk_id=chunk_id,
            content=content,
            file_path=file_path,
            chunk_type="class",
            language=language.value,
            start_line=cls.start_line,
            end_line=cls.end_line,
            metadata={
                "class_name": cls.name,
                "methods": [m.name for m in cls.methods],
                "inherits_from": cls.inherits_from,
                "implements": cls.implements,
                "is_abstract": cls.is_abstract
            }
        )
    
    def _create_method_chunk(self, method, class_name: str, file_path: str, language: ProgrammingLanguage) -> CodeChunk:
        """Create chunk for a class method"""
        chunk_id = self._generate_chunk_id(file_path, f"{class_name}.{method.name}", "method")
        
        content_parts = [
            f"Method: {class_name}.{method.name}",
            f"File: {file_path}",
            f"Language: {language.value}",
            f"Parameters: {', '.join(method.parameters)}",
        ]
        
        if method.docstring:
            content_parts.append(f"Description: {method.docstring}")
        
        content = '\n'.join(content_parts)
        
        return CodeChunk(
            chunk_id=chunk_id,
            content=content,
            file_path=file_path,
            chunk_type="method",
            language=language.value,
            start_line=method.start_line,
            end_line=method.end_line,
            metadata={
                "class_name": class_name,
                "method_name": method.name,
                "parameters": method.parameters,
                "calls": method.calls,
                "complexity": method.complexity,
                "is_async": method.is_async,
                "visibility": method.visibility
            }
        )
    
    def _create_imports_chunk(self, imports, file_path: str, language: ProgrammingLanguage) -> CodeChunk:
        """Create chunk for imports"""
        chunk_id = self._generate_chunk_id(file_path, "imports", "imports")
        
        import_descriptions = []
        for imp in imports:
            if imp.items:
                import_descriptions.append(f"From {imp.module} imports: {', '.join(imp.items)}")
            else:
                import_descriptions.append(f"Imports: {imp.module}")
        
        content = f"File: {file_path}\nLanguage: {language.value}\nImports:\n" + '\n'.join(import_descriptions)
        
        return CodeChunk(
            chunk_id=chunk_id,
            content=content,
            file_path=file_path,
            chunk_type="imports",
            language=language.value,
            start_line=1,
            end_line=len(imports),
            metadata={
                "imports": [{
                    "module": imp.module,
                    "items": imp.items,
                    "alias": imp.alias,
                    "is_relative": imp.is_relative
                } for imp in imports]
            }
        )
    
    def _create_file_chunk(self, structure: CodeStructure, file_path: str) -> CodeChunk:
        """Create chunk for entire small file"""
        chunk_id = self._generate_chunk_id(file_path, "file", "file")
        
        content_parts = [
            f"File: {file_path}",
            f"Language: {structure.language.value}",
            f"Lines: {structure.total_lines}",
            f"Functions: {len(structure.functions)}",
            f"Classes: {len(structure.classes)}",
        ]
        
        if structure.entry_points:
            content_parts.append(f"Entry points: {', '.join(structure.entry_points)}")
        
        content = '\n'.join(content_parts)
        
        return CodeChunk(
            chunk_id=chunk_id,
            content=content,
            file_path=file_path,
            chunk_type="file",
            language=structure.language.value,
            start_line=1,
            end_line=structure.total_lines,
            metadata={
                "total_lines": structure.total_lines,
                "complexity_score": structure.complexity_score,
                "entry_points": structure.entry_points,
                "function_count": len(structure.functions),
                "class_count": len(structure.classes)
            }
        )
    
    def _generate_chunk_id(self, file_path: str, name: str, chunk_type: str) -> str:
        """Generate unique chunk ID"""
        content = f"{file_path}:{name}:{chunk_type}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class RelationshipGraphBuilder:
    """Builds relationship graphs using NetworkX"""
    
    def __init__(self):
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX is required for relationship graphs")
        
        self.graph = nx.DiGraph()
    
    def build_graph(self, project_structure: Dict[str, CodeStructure], chunks: List[CodeChunk]) -> nx.DiGraph:
        """Build relationship graph from project structure"""
        # Add nodes for files, functions, classes
        for file_path, structure in project_structure.items():
            # Add file node
            self.graph.add_node(file_path, type="file", language=structure.language.value)
            
            # Add function nodes
            for func in structure.functions:
                func_id = f"{file_path}::{func.name}"
                self.graph.add_node(func_id, type="function", name=func.name, file=file_path)
                self.graph.add_edge(file_path, func_id, relationship="contains")
            
            # Add class nodes
            for cls in structure.classes:
                cls_id = f"{file_path}::{cls.name}"
                self.graph.add_node(cls_id, type="class", name=cls.name, file=file_path)
                self.graph.add_edge(file_path, cls_id, relationship="contains")
        
        return self.graph
    
    def find_related_nodes(self, node_id: str, max_depth: int = 2) -> List[str]:
        """Find nodes related to given node within max_depth"""
        if not self.graph.has_node(node_id):
            return []
        
        related = set()
        
        # Get neighbors at different depths
        for depth in range(1, max_depth + 1):
            try:
                # Outgoing edges (what this node calls/uses)
                successors = list(nx.single_source_shortest_path_length(self.graph, node_id, cutoff=depth).keys())
                related.update(successors)
                
                # Incoming edges (what calls/uses this node)
                predecessors = list(nx.single_source_shortest_path_length(self.graph.reverse(), node_id, cutoff=depth).keys())
                related.update(predecessors)
            except nx.NetworkXError:
                continue
        
        # Remove the original node
        related.discard(node_id)
        return list(related)


class CPUOptimizedRAGSystem:
    """Main RAG system optimized for CPU-only environments"""
    
    def __init__(self, storage_path: str = "./rag_storage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.code_analyzer = MultiLanguageCodeAnalyzer()
        self.chunker = CodeChunker()
        self.graph_builder = RelationshipGraphBuilder()
        
        # Initialize ChromaDB
        if CHROMADB_AVAILABLE:
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.storage_path / "chroma_db"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.collection = None
        else:
            raise ImportError("ChromaDB is required for RAG system")
        
        # Initialize embedding model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            # Use small, CPU-optimized model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            # Use ChromaDB's default embeddings
            self.embedding_model = None
            self.logger.warning("Using ChromaDB default embeddings instead of sentence transformers")
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def build_rag_from_gitingest(self, gitingest_file_path: str, collection_name: str = "code_rag") -> RAGMetrics:
        """Build complete RAG system from gitingest file"""
        start_time = datetime.now()
        
        self.logger.info(f"Building RAG system from {gitingest_file_path}")
        
        # Step 1: Parse gitingest file
        self.logger.info("Parsing gitingest file...")
        files = GitingestParser.parse_gitingest_file(gitingest_file_path)
        self.logger.info(f"Parsed {len(files)} files")
        
        # Step 2: Analyze code structure
        self.logger.info("Analyzing code structure...")
        project_structure = self.code_analyzer.analyze_project(files)
        
        # Step 3: Create chunks
        self.logger.info("Creating intelligent chunks...")
        chunks = self.chunker.create_chunks(project_structure)
        self.logger.info(f"Created {len(chunks)} chunks")
        
        # Step 4: Build relationship graph
        self.logger.info("Building relationship graph...")
        self.graph_builder.build_graph(project_structure, chunks)
        
        # Step 5: Generate embeddings and store in ChromaDB
        self.logger.info("Generating embeddings and storing in vector database...")
        self._store_chunks_in_chromadb(chunks, collection_name)
        
        # Step 6: Save metadata and graphs
        self._save_metadata(project_structure, chunks)
        
        build_time = (datetime.now() - start_time).total_seconds()
        
        # Calculate metrics
        languages = list(set(structure.language.value for structure in project_structure.values()))
        
        metrics = RAGMetrics(
            total_chunks=len(chunks),
            total_files=len(files),
            languages_detected=languages,
            build_time=build_time,
            index_size_mb=self._calculate_storage_size(),
            last_updated=datetime.now().isoformat()
        )
        
        self.logger.info(f"RAG system built successfully in {build_time:.2f} seconds")
        return metrics
    
    def query(self, question: str, max_results: int = 10, collection_name: str = "code_rag") -> QueryResult:
        """Query the RAG system with enhanced function discovery"""
        start_time = datetime.now()
        
        # Get or create collection
        if not self.collection or self.collection.name != collection_name:
            self.collection = self.chroma_client.get_collection(collection_name)
        
        # Perform semantic search
        results = self.collection.query(
            query_texts=[question],
            n_results=max_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert results to CodeChunk objects
        chunks = []
        confidence_scores = []
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0], 
            results['distances'][0]
        )):
            chunk = CodeChunk(
                chunk_id=results['ids'][0][i],
                content=doc,
                file_path=metadata.get('file_path', ''),
                chunk_type=metadata.get('chunk_type', ''),
                language=metadata.get('language', ''),
                start_line=metadata.get('start_line', 0),
                end_line=metadata.get('end_line', 0),
                metadata=metadata
            )
            chunks.append(chunk)
            
            # Convert distance to confidence (lower distance = higher confidence)
            confidence = max(0, 1 - distance)
            confidence_scores.append(confidence)
        
        # Get relationship information
        relationships = self._get_relationships_for_chunks(chunks)
        
        query_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResult(
            chunks=chunks,
            relationships=relationships,
            confidence_scores=confidence_scores,
            query_time=query_time,
            total_chunks_searched=self.collection.count()
        )
    
    def discover_functions(self, search_queries: List[Dict[str, str]], max_results: int = 3, collection_name: str = "code_rag") -> Dict[str, QueryResult]:
        """
        Enhanced function discovery system for comprehensive code analysis
        
        Args:
            search_queries: List of dictionaries with 'query' and 'expect' keys
            max_results: Maximum results per query
            collection_name: ChromaDB collection name
            
        Returns:
            Dictionary mapping query strings to QueryResult objects
        """
        results = {}
        
        for search_item in search_queries:
            query = search_item['query']
            expected = search_item.get('expect', '')
            
            self.logger.info(f"Searching for: '{query}' - Expected: {expected}")
            
            # Perform the query
            result = self.query(query, max_results=max_results, collection_name=collection_name)
            results[query] = result
            
            # Log results for debugging
            self.logger.debug(f"Found {len(result.chunks)} results for '{query}'")
            for chunk, confidence in zip(result.chunks, result.confidence_scores):
                self.logger.debug(f"  - {chunk.chunk_type} in {chunk.file_path} (confidence: {confidence:.3f})")
        
        return results
    
    def analyze_code_patterns(self, pattern_queries: List[str], max_results: int = 2, collection_name: str = "code_rag") -> Dict[str, QueryResult]:
        """
        Analyze specific code patterns across the codebase
        
        Args:
            pattern_queries: List of pattern search strings
            max_results: Maximum results per pattern
            collection_name: ChromaDB collection name
            
        Returns:
            Dictionary mapping pattern strings to QueryResult objects
        """
        results = {}
        
        for pattern in pattern_queries:
            self.logger.info(f"Analyzing pattern: '{pattern}'")
            
            result = self.query(pattern, max_results=max_results, collection_name=collection_name)
            
            # Filter results by confidence threshold
            filtered_chunks = []
            filtered_scores = []
            
            for chunk, confidence in zip(result.chunks, result.confidence_scores):
                if confidence > 0.01:  # Only include results with some relevance
                    filtered_chunks.append(chunk)
                    filtered_scores.append(confidence)
            
            # Create filtered result
            filtered_result = QueryResult(
                chunks=filtered_chunks,
                relationships=result.relationships,
                confidence_scores=filtered_scores,
                query_time=result.query_time,
                total_chunks_searched=result.total_chunks_searched
            )
            
            results[pattern] = filtered_result
            
            self.logger.debug(f"Found {len(filtered_chunks)} relevant results for pattern '{pattern}'")
        
        return results
    
    def get_comprehensive_analysis(self, collection_name: str = "code_rag") -> Dict[str, Any]:
        """
        Get comprehensive analysis of the indexed codebase including:
        - File type distribution
        - Chunk type distribution  
        - Language distribution
        - Function discovery results
        - Code pattern analysis
        
        Returns:
            Dictionary with comprehensive analysis results
        """
        start_time = datetime.now()
        
        # Get all chunks for analysis
        all_results = self.query("*", max_results=50, collection_name=collection_name)
        
        # Analyze file types
        file_types = {}
        chunk_types = {}
        languages = {}
        
        for chunk in all_results.chunks:
            # File extension analysis
            file_path = Path(chunk.file_path)
            ext = file_path.suffix or 'no-ext'
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Chunk type analysis
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
            
            # Language analysis
            languages[chunk.language] = languages.get(chunk.language, 0) + 1
        
        # Enhanced function discovery searches
        function_searches = [
            {"query": "authentication login function", "expect": "Should find login-related code"},
            {"query": "wildfire risk prediction algorithm", "expect": "Should find prediction functions in Flask backend"},
            {"query": "Flask backend get_wildfire_risk_prediction function", "expect": "Should find the main Python prediction function"},
            {"query": "gee_data Google Earth Engine API", "expect": "Should find the GEE data processing function"},
            {"query": "Python Flask route handler", "expect": "Should find Flask route functions like home and about"},
            {"query": "environmental data processing Python", "expect": "Should find Python functions that process environmental data"},
            {"query": "location tracking GPS coordinates", "expect": "Should find LocationContext and location services"},
            {"query": "air quality monitoring API calls", "expect": "Should find air quality related functions"},
            {"query": "React Native map component MapView", "expect": "Should find map implementation"},
            {"query": "background task notification system", "expect": "Should find background task services"},
            {"query": "user profile management settings", "expect": "Should find profile screen and user management"},
            {"query": "evacuation route planning emergency", "expect": "Should find evacuation-related components"},
            {"query": "Python test functions pytest", "expect": "Should find test functions in test_app.py"},
            {"query": "Flask app configuration setup", "expect": "Should find Flask app initialization and config"}
        ]
        
        # Code pattern searches
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
        
        # Perform function discovery
        function_results = self.discover_functions(function_searches, max_results=3, collection_name=collection_name)
        
        # Perform pattern analysis
        pattern_results = self.analyze_code_patterns(pattern_searches, max_results=2, collection_name=collection_name)
        
        analysis_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'analysis_metadata': {
                'total_chunks_analyzed': len(all_results.chunks),
                'analysis_time_seconds': analysis_time,
                'timestamp': datetime.now().isoformat()
            },
            'file_type_distribution': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)),
            'chunk_type_distribution': dict(sorted(chunk_types.items(), key=lambda x: x[1], reverse=True)),
            'language_distribution': dict(sorted(languages.items(), key=lambda x: x[1], reverse=True)),
            'function_discovery_results': function_results,
            'code_pattern_results': pattern_results,
            'summary_stats': {
                'unique_file_types': len(file_types),
                'unique_chunk_types': len(chunk_types),
                'unique_languages': len(languages),
                'successful_function_searches': sum(1 for result in function_results.values() if result.chunks),
                'successful_pattern_searches': sum(1 for result in pattern_results.values() if result.chunks)
            }
        }
    
    def get_context_for_llm(self, query_result: QueryResult, max_tokens: int = 4000) -> str:
        """Format query results as context for LLM"""
        context_parts = []
        current_tokens = 0
        
        # Add chunks in order of confidence
        sorted_chunks = sorted(
            zip(query_result.chunks, query_result.confidence_scores),
            key=lambda x: x[1],
            reverse=True
        )
        
        for chunk, confidence in sorted_chunks:
            chunk_text = f"\n--- {chunk.chunk_type.upper()}: {chunk.file_path} ---\n{chunk.content}\n"
            
            # Simple token estimation if tiktoken not available
            if self.chunker.tokenizer:
                chunk_tokens = len(self.chunker.tokenizer.encode(chunk_text))
            else:
                chunk_tokens = len(chunk_text.split()) * 1.3  # Rough estimate
            
            if current_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            current_tokens += chunk_tokens
        
        return ''.join(context_parts)
    
    def _store_chunks_in_chromadb(self, chunks: List[CodeChunk], collection_name: str) -> None:
        """Store chunks in ChromaDB with embeddings"""
        # Create or get collection
        try:
            self.collection = self.chroma_client.create_collection(collection_name)
        except Exception:
            # Collection might already exist
            self.collection = self.chroma_client.get_collection(collection_name)
        
        # Process chunks in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Prepare batch data
            ids = [chunk.chunk_id for chunk in batch]
            documents = [chunk.content for chunk in batch]
            metadatas = []
            
            for chunk in batch:
                # Convert metadata to ChromaDB-compatible format (no lists/dicts)
                metadata = {
                    'file_path': chunk.file_path,
                    'chunk_type': chunk.chunk_type,
                    'language': chunk.language,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                }
                
                # Add simple metadata fields, converting lists to strings
                for key, value in chunk.metadata.items():
                    if value is None:
                        # Skip None values as ChromaDB doesn't like them
                        continue
                    elif isinstance(value, (list, dict)):
                        # Convert lists/dicts to JSON strings
                        if value:  # Only if not empty
                            metadata[f"{key}_json"] = json.dumps(value)
                    elif isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                    else:
                        metadata[key] = str(value)
                
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            self.logger.debug(f"Stored batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
    
    def _save_metadata(self, project_structure: Dict[str, CodeStructure], chunks: List[CodeChunk]) -> None:
        """Save metadata and relationship graph"""
        # Save project structure
        structure_path = self.storage_path / "project_structure.json"
        with open(structure_path, 'w', encoding='utf-8') as f:
            serializable_structure = {}
            for file_path, structure in project_structure.items():
                serializable_structure[file_path] = {
                    'language': structure.language.value,
                    'total_lines': structure.total_lines,
                    'complexity_score': structure.complexity_score,
                    'function_count': len(structure.functions),
                    'class_count': len(structure.classes),
                    'entry_points': structure.entry_points
                }
            json.dump(serializable_structure, f, indent=2)
        
        # Save chunks metadata
        chunks_path = self.storage_path / "chunks_metadata.json"
        with open(chunks_path, 'w', encoding='utf-8') as f:
            chunks_data = [{
                'chunk_id': chunk.chunk_id,
                'file_path': chunk.file_path,
                'chunk_type': chunk.chunk_type,
                'language': chunk.language,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'metadata': chunk.metadata
            } for chunk in chunks]
            json.dump(chunks_data, f, indent=2)
    
    def _get_relationships_for_chunks(self, chunks: List[CodeChunk]) -> Dict[str, List[str]]:
        """Get relationship information for chunks"""
        relationships = {
            'calls': [],
            'called_by': [],
            'imports': [],
            'imported_by': [],
            'related_files': []
        }
        
        for chunk in chunks:
            # Get related nodes from graph
            node_patterns = [
                f"{chunk.file_path}::{chunk.metadata.get('function_name', '')}",
                f"{chunk.file_path}::{chunk.metadata.get('class_name', '')}",
                chunk.file_path
            ]
            
            for pattern in node_patterns:
                if self.graph_builder.graph.has_node(pattern):
                    related = self.graph_builder.find_related_nodes(pattern, max_depth=2)
                    
                    for related_node in related:
                        if '::' in related_node:
                            file_path, item_name = related_node.split('::', 1)
                            relationships['related_files'].append(file_path)
        
        # Remove duplicates and limit results
        for key in relationships:
            relationships[key] = list(set(relationships[key]))[:10]
        
        return relationships
    
    def _calculate_storage_size(self) -> float:
        """Calculate total storage size in MB"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.storage_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
        except Exception:
            pass  # Ignore errors during size calculation
        return total_size / (1024 * 1024)  # Convert to MB
    
    def run_enhanced_function_discovery_test(self, collection_name: str = "code_rag") -> Dict[str, Any]:
        """
        Run the enhanced function discovery test similar to test_find_functions.py
        This provides a comprehensive analysis of the codebase with detailed results
        
        Returns:
            Dictionary with detailed test results and analysis
        """
        print("🔍 Running Enhanced Function & Component Discovery")
        print("=" * 50)
        
        # Get comprehensive analysis
        analysis = self.get_comprehensive_analysis(collection_name)
        
        # Print results in a user-friendly format
        print(f"\n📊 Analysis Summary:")
        print(f"   Total chunks analyzed: {analysis['analysis_metadata']['total_chunks_analyzed']}")
        print(f"   Analysis time: {analysis['analysis_metadata']['analysis_time_seconds']:.2f} seconds")
        
        print(f"\n📁 File types indexed:")
        for ext, count in list(analysis['file_type_distribution'].items())[:10]:
            print(f"   {ext}: {count} chunks")
        
        print(f"\n🧩 Chunk types created:")
        for chunk_type, count in analysis['chunk_type_distribution'].items():
            print(f"   {chunk_type}: {count} chunks")
        
        print(f"\n🌐 Languages detected:")
        for language, count in analysis['language_distribution'].items():
            print(f"   {language}: {count} chunks")
        
        print(f"\n🎯 Function Discovery Results:")
        print("=" * 30)
        
        for i, (query, result) in enumerate(analysis['function_discovery_results'].items(), 1):
            print(f"\n🔎 Search {i}: '{query}'")
            print(f"   ⚡ Found {len(result.chunks)} results:")
            
            for chunk, confidence in zip(result.chunks, result.confidence_scores):
                confidence_emoji = "🎯" if confidence > 0.1 else "📍" if confidence > 0.05 else "📌"
                print(f"     {confidence_emoji} {chunk.chunk_type} in {chunk.file_path}")
                print(f"        Confidence: {confidence:.3f}")
                
                # Show metadata if available
                if chunk.metadata:
                    relevant_meta = {}
                    for key in ['function_name', 'class_name', 'method_name']:
                        if key in chunk.metadata and chunk.metadata[key]:
                            relevant_meta[key] = chunk.metadata[key]
                    if relevant_meta:
                        print(f"        Metadata: {relevant_meta}")
        
        print(f"\n🧩 Code Pattern Analysis:")
        print("=" * 25)
        
        for pattern, result in analysis['code_pattern_results'].items():
            if result.chunks:  # Only show patterns with results
                print(f"\n🔍 Pattern: '{pattern}'")
                for chunk, confidence in zip(result.chunks[:2], result.confidence_scores[:2]):
                    print(f"   📄 {chunk.file_path} (confidence: {confidence:.3f})")
        
        print(f"\n✅ Enhanced Function Discovery Complete!")
        print(f"   Successful function searches: {analysis['summary_stats']['successful_function_searches']}")
        print(f"   Successful pattern searches: {analysis['summary_stats']['successful_pattern_searches']}")
        
        return analysis
    
    def cleanup(self):
        """Properly cleanup ChromaDB resources"""
        try:
            if hasattr(self, 'collection') and self.collection:
                self.collection = None
            if hasattr(self, 'chroma_client') and self.chroma_client:
                # Force close the client
                self.chroma_client = None
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")