#!/usr/bin/env python3
"""
Multi-Repo RAG pipeline with FAISS + Graph + HuggingFace OSS LLM
"""

import os, re, json, pickle, faiss, numpy as np, networkx as nx
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
import glob


INDEX_BASE = "indexes"   # root folder for all repos

# -------------------------------
# 1. Load + Chunk repo ingest
# -------------------------------

# 1.1 ingestion of stuff
def find_ingest_file(repo_name: str, folder="gitingest_outputs"):
    pattern = os.path.join(folder, f"*{repo_name}*.txt")
    files = glob.glob(pattern)
    if not files:
        return None
    # sort by modification time (latest first)
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def load_and_chunk(ingest_file: str, chunk_size=800, overlap=100) -> List[Dict]:
    with open(ingest_file, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

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

        for match in re.finditer(r"import .* from ['\"](.*)['\"]", c["content"]):
            G.add_edge(file, match.group(1), type="IMPORTS")

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
    if retrieved:
        context = "\n\n".join([f"From {r['file']}:\n{r['content']}" for r in retrieved])
        return f"Look into these files if attached!\n{context}\n\nQuestion: {query}"
    else:
        return f"Question: {query}"

# -------------------------------
# 5. LLM call
# -------------------------------

def ask_llm(prompt: str):
    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key="...",  # replace with your token
    )
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content

# -------------------------------
# 6. Build or Load per repo
# -------------------------------

def build_or_load(repo_name: str, ingest_file: str):
    repo_dir = os.path.join(INDEX_BASE, repo_name)
    os.makedirs(repo_dir, exist_ok=True)

    index_file = os.path.join(repo_dir, "repo.index")
    chunks_file = os.path.join(repo_dir, "chunks.json")
    graph_file = os.path.join(repo_dir, "graph.pkl")

    build_mode = not (os.path.exists(index_file) and os.path.exists(chunks_file) and os.path.exists(graph_file))

    if build_mode:
        print(f" Building FAISS + Graph for {repo_name}...")
        chunks = load_and_chunk(ingest_file)
        model, embeddings = embed_chunks(chunks)
        index = build_faiss(embeddings)
        graph = build_graph(chunks)

        faiss.write_index(index, index_file)
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f)
        with open(graph_file, "wb") as f:
            pickle.dump(graph, f)

        print(f" Saved index for {repo_name}")
    else:
        print(f" Loading saved index for {repo_name}...")
        index = faiss.read_index(index_file)
        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        with open(graph_file, "rb") as f:
            graph = pickle.load(f)
        model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    return model, index, chunks, graph

# -------------------------------
# Main
# -------------------------------

if __name__ == "__main__":
    repo_name = input(" Enter repo name: ").strip()
    ingest_file = find_ingest_file(repo_name)

    if not os.path.exists(ingest_file):
        print(f" Ingest file not found: {ingest_file}")
        exit(1)
    
    print(f" Using ingest file: {ingest_file}")
    model, index, chunks, graph = build_or_load(repo_name, ingest_file)

    print(f" Ready! Ask me questions about {repo_name}.")
    while True:
        q = input("\n❓ Ask about the repo (or 'exit'): ").strip()
        if q.lower() in ["exit", "quit"]:
            break

        retrieved = retrieve(q, model, index, chunks, graph, top_k=5)
        if not retrieved:
            print(" No relevant chunks found.")
            continue

        prompt = build_prompt(q, retrieved)
        answer = ask_llm(prompt)
        print("\n Answer:\n", answer)

        # Ask user if they want to save the answer
        save = input("\n Save this answer as markdown? (y/n): ").strip().lower()
        if save == 'y':
            filename = input("Enter filename (without .md): ").strip()
            if not filename:
                print(" No filename given, skipping save.")
                continue
            # Make sure folder exists
            repo_dir = os.path.join(INDEX_BASE, repo_name)
            chat_dir = os.path.join(repo_dir, "saved_chats")
            os.makedirs(chat_dir, exist_ok=True)
            md_path = os.path.join(chat_dir, filename + ".md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# Q: {q}\n\n")
                f.write(answer)
            print(f"Saved to {md_path}")
