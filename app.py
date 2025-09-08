from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_cors import CORS
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

@app.route("/loading/<repo>")
def loading(repo):
    # You can add async RAG build logic here
    return render_template("loading.html", repo=repo)

@app.route("/workspace/<owner>/<repo>")
def workspace(owner, repo):
    repo_path = os.path.join("my_repos", owner, repo)
    if not os.path.exists(repo_path):
        return f"❌ Repo {owner}/{repo} not found locally", 404

    file_tree = build_tree_from_local(repo_path)
    return render_template("workspace.html", owner=owner, repo=repo, file_tree=file_tree)

@app.route("/api/chat/<owner>/<repo>", methods=["POST"])
def chat_api(owner, repo):
    # You can use owner/repo to load the right vectorstore / ingest file
    data = request.get_json()
    user_message = data.get("message", "")
    # TODO: handle LLM query here with the repo context
    return jsonify({"reply": f"🤖 (LLM would answer about {owner}/{repo}): {user_message}"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)