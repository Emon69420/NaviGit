#!/usr/bin/env python3
"""
Repo-RAG pipeline with FAISS + Graph + HuggingFace OSS LLM
"""

import os
import re
import faiss
import pickle
import numpy as np
import networkx as nx
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI

# -------------------------------
# 1. Load + Chunk repo ingest
# -------------------------------

def load_and_chunk(ingest_file: str, chunk_size=800, overlap=100) -> List[Dict]:
    with open(ingest_file, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    # split at FILE markers
    sections = re.split(r"=+\nFILE:\s+", raw_text)
    chunks = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\nclass ", "\ndef ", "\n## ", "\n### ", "\n", " "],
    )

    for section in sections:
        if not section.strip():
            continue
        lines = section.splitlines()
        filename = lines[0].strip()
        content = "\n".join(lines[1:])

        subchunks = splitter.split_text(content)
        for i, ch in enumerate(subchunks):
            chunks.append({
                "id": f"{filename}_{i}",
                "file": filename,
                "content": ch
            })

    return chunks

# -------------------------------
# 2. Embeddings + FAISS
# -------------------------------

def embed_chunks(chunks: List[Dict], model_name="all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name, device="cpu")
    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, convert_to_tensor=False, show_progress_bar=True)
    return model, np.array(embeddings, dtype="float32")

def build_faiss(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index

# -------------------------------
# 3. Graph builder
# -------------------------------

def build_graph(chunks: List[Dict]):
    G = nx.DiGraph()
    for c in chunks:
        file = c["file"]
        G.add_node(file, type="file")

        # detect imports
        for match in re.finditer(r"import .* from ['\"](.*)['\"]", c["content"]):
            G.add_edge(file, match.group(1), type="IMPORTS")

        # detect functions/classes
        for match in re.finditer(r"(?:def|class|function)\s+(\w+)", c["content"]):
            node_id = f"{file}:{match.group(1)}"
            G.add_node(node_id, type="symbol")
            G.add_edge(file, node_id, type="CONTAINS")

    return G

# -------------------------------
# 4. Query pipeline
# -------------------------------

def retrieve(query: str, model, index, chunks, graph, top_k=5):
    query_emb = model.encode([query], convert_to_tensor=False)
    D, I = index.search(np.array(query_emb, dtype="float32"), k=top_k)

    results = [chunks[i] for i in I[0]]

    # expand with graph neighbors
    expanded = []
    for r in results:
        f = r["file"]
        if f in graph:
            for n in nx.neighbors(graph, f):
                for c in chunks:
                    if c["file"] == n:
                        expanded.append(c)
    return results + expanded

def build_prompt(query: str, retrieved: List[Dict]):
    context = "\n\n".join([f"From {r['file']}:\n{r['content']}" for r in retrieved])
    return f"Context:\n{context}\n\nQuestion: {query}"

# -------------------------------
# 5. LLM call (OSS via HuggingFace router)
# -------------------------------

def ask_llm(prompt: str):
    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key="hf token",
    )
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content

# -------------------------------
# Main
# -------------------------------

if __name__ == "__main__":
    INGEST_FILE = "gitingest_outputs/Emon69420_MedMint_20250906_195028.txt"  # <-- update path

    if not os.path.exists(INGEST_FILE):
        print(f"❌ Ingest file not found: {INGEST_FILE}")
        exit(1)

    print("📂 Loading repo ingest...")
    chunks = load_and_chunk(INGEST_FILE)
    print(f"✅ {len(chunks)} chunks created")

    if not chunks:
        print("❌ No chunks created. Check ingest file format.")
        exit(1)

    print("🔎 Embedding chunks...")
    model, embeddings = embed_chunks(chunks)

    print("📦 Building FAISS + Graph...")
    index = build_faiss(embeddings)
    graph = build_graph(chunks)

    print("✅ Setup complete! Ask me questions about the repo.")
    while True:
        q = input("\n❓ Ask about the repo (or 'exit'): ").strip()
        if q.lower() in ["exit", "quit"]:
            break

        retrieved = retrieve(q, model, index, chunks, graph, top_k=5)
        if not retrieved:
            print("⚠️ No relevant chunks found.")
            continue

        prompt = build_prompt(q, retrieved)
        answer = ask_llm(prompt)
        print("\n🤖 Answer:\n", answer)