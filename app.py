from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import os
import requests
from datetime import datetime
import logging
import re
from urllib.parse import urlparse
import subprocess
import shutil
from pathlib import Path
import tempfile
from collections import defaultdict
from ingest import RepoIngestor
from rag_repo import build_or_load, find_ingest_file
import rag_repo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "your_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", manage_session=False)

# Cache loaded models per repo for efficiency
loaded_repos = {}
# Store per-session context: { sid: { 'repo': ..., 'history': [...] } }
session_context = {}
# Per-session WebSocket context
ws_session_context = {}

def get_repo_objects(repo):
    if repo not in loaded_repos:
        ingest_file = rag_repo.find_ingest_file(repo)
        if not ingest_file:
            raise Exception(f"Ingest file not found for {repo}")
        loaded_repos[repo] = rag_repo.build_or_load(repo, ingest_file)
    return loaded_repos[repo]

def nested_dict():
    return defaultdict(nested_dict)

def build_tree_from_local(repo_path: str):
    """
    Walk the local repo and return a nested dict {folder: {sub: {files}}}.
    """
    tree = nested_dict()
    for root, dirs, files in os.walk(repo_path):
        rel_path = os.path.relpath(root, repo_path)
        if rel_path == ".":
            current = tree
        else:
            parts = rel_path.split(os.sep)
            current = tree
            for p in parts:
                current = current[p]

        for f in files:
            try:
                with open(os.path.join(root, f), "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except Exception as e:
                content = f"⚠️ Error reading file: {e}"
            current[f] = content
    return tree
    
def list_available_repos(output_dir="gitingest_outputs"):
    repos = {}
    for f in os.listdir(output_dir):
        if f.endswith(".txt") and not f.endswith("_structured.json"):
            match = re.match(r"(.+?)_(.+?)_\d{8}_\d{6}\.txt", f)
            if match:
                owner, repo = match.groups()
                repo_key = f"{owner}/{repo}"
                repos[repo_key] = os.path.join(output_dir, f)
    return repos

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        github_link = request.form["repo_link"].strip()
        repo_name = github_link.split("/")[-1].replace(".git", "")
        # TODO: trigger repo ingest + RAG build here
        return redirect(url_for("loading", repo=repo_name))

    # dynamically list repos
    repos = list_available_repos()
    return render_template("index.html", repos=repos)

@app.route('/loading/<owner>/<repo>')
def loading(owner, repo):
    return render_template('loading.html', owner=owner, repo=repo)

@app.route("/workspace/<owner>/<repo>")
def workspace(owner, repo):
    repo_path = os.path.join("my_repos", owner, repo)
    if not os.path.exists(repo_path):
        return f"❌ Repo {owner}/{repo} not found locally", 404

    file_tree = build_tree_from_local(repo_path)
    return render_template("workspace.html", owner=owner, repo=repo, file_tree=file_tree)

# --- WebSocket Chat ---
@socketio.on('connect')
def ws_connect():
    wsid = request.sid
    ws_session_context[wsid] = {"repo": None, "history": []}
    emit('connected', {'message': 'WebSocket connected.'})

@socketio.on('init_repo')
def ws_init_repo(data):
    wsid = request.sid
    repo = data.get('repo')
    if not repo:
        emit('error', {'error': 'No repo specified.'})
        return
    try:
        # Load and cache repo objects for this session
        model, index, chunks, graph = get_repo_objects(repo)
        ws_session_context[wsid]["repo"] = repo
        ws_session_context[wsid]["model"] = model
        ws_session_context[wsid]["index"] = index
        ws_session_context[wsid]["chunks"] = chunks
        ws_session_context[wsid]["graph"] = graph
        ws_session_context[wsid]["history"] = []
        emit('repo_initialized', {'status': 'ok'})
    except Exception as e:
        emit('error', {'error': str(e)})

@socketio.on('chat_message')
def ws_chat_message(data):
    wsid = request.sid
    message = data.get('message', '')
    ctx = ws_session_context.get(wsid)
    if not ctx or not ctx.get('repo'):
        emit('error', {'error': 'Repo not initialized for this session.'})
        return
    # Maintain chat history (last 5)
    history = ctx.get('history', [])
    history.append({"role": "user", "content": message})
    history = history[-5:]
    ctx['history'] = history
    # Build chat history context
    chat_history = "\n".join([f"{m['role']}: {m['content']}" for m in history])
    # Extended context: repo description and chat summary
    repo_name = ctx['repo']
    repo_desc = f"You are an expert code assistant helping with the repository '{repo_name}'. Answer questions about the codebase, its structure, and best practices."
    style_instruction = "Please answer paragraphs, without sections, comparison tables, tables , can use headings and codeblocks. Use the chat history below for context. Be concise to what user asks!"
    # Retrieve relevant chunks and build prompt
    model = ctx['model']
    index = ctx['index']
    chunks = ctx['chunks']
    graph = ctx['graph']
    retrieved = rag_repo.retrieve(message, model, index, chunks, graph, top_k=5)
    prompt = f"{repo_desc}\n\nChat history:\n{chat_history}\n\n{style_instruction}\n" + rag_repo.build_prompt(message, retrieved)
    answer = rag_repo.ask_llm(prompt)
    # Add bot reply to history
    history.append({"role": "assistant", "content": answer})
    ctx['history'] = history[-5:]
    emit('chat_reply', {'reply': answer})

@socketio.on('disconnect')
def ws_disconnect():
    wsid = request.sid
    ws_session_context.pop(wsid, None)

@app.route("/api/chat/<owner>/<repo>", methods=["POST"])
def chat_api(owner, repo):
    # You can use owner/repo to load the right vectorstore / ingest file
    data = request.get_json()
    user_message = data.get("message", "")
    # TODO: handle LLM query here with the repo context
    return jsonify({"reply": f"🤖 (LLM would answer about {owner}/{repo}): {user_message}"})

@app.route('/ingest', methods=['POST'])
def ingest_repo():
    data = request.get_json()
    repo_link = data.get('repo_link')
    processor = RepoIngestor()  # Add token if needed
    result = processor.ingest_repo(repo_link)
    return jsonify(result)

@app.route('/api/build_index/<owner>/<repo>', methods=['POST'])
def build_index(owner, repo):
    repo_ingestor = RepoIngestor()
    if not repo_ingestor.repo_index_exists(repo):
        ingest_file = find_ingest_file(repo)
        if ingest_file:
            build_or_load(repo, ingest_file)
            return jsonify({'started': True, 'status': 'built'})
        else:
            return jsonify({'started': False, 'error': 'No ingest file found'}), 404
    return jsonify({'started': False, 'status': 'already exists'})

@app.route('/api/index_status/<owner>/<repo>')
def index_status(owner, repo):
    repo_ingestor = RepoIngestor()
    ready = repo_ingestor.repo_index_exists(repo)
    return jsonify({'ready': ready})

@app.route("/chat/<repo>", methods=["POST"])
def chat(repo):
    data = request.get_json()
    message = data.get("message", "")

    # Maintain chat history in session per repo
    session_key = f"chat_history_{repo}"
    history = session.get(session_key, [])
    history.append({"role": "user", "content": message})
    history = history[-5:]
    session[session_key] = history

    # Build context from last 5 messages
    context = "\n".join([f"{m['role']}: {m['content']}" for m in history])

    # Load RAG objects for this repo
    try:
        model, index, chunks, graph = get_repo_objects(repo)
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

    # Retrieve relevant chunks and build prompt
    retrieved = rag_repo.retrieve(message, model, index, chunks, graph, top_k=5)
    prompt = f"Chat history:\n{context}\n\n" + rag_repo.build_prompt(message, retrieved)
    answer = rag_repo.ask_llm(prompt)

    # Add bot reply to history
    history.append({"role": "assistant", "content": answer})
    session[session_key] = history[-5:]

    return jsonify({"reply": answer})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)