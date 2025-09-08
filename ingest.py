#!/usr/bin/env python3
"""
Repo ingestion with gitingest + local clone.

This script:
  1. Runs gitingest and saves the structured repo text into gitingest_outputs/.
  2. Clones the repo locally into my_repos/owner/repo/.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import shutil
import re
import stat

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def handle_remove_readonly(func, path, exc):
    # Clear the readonly flag and retry
    os.chmod(path, stat.S_IWRITE)
    func(path)


class RepoIngestor:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token

    # ------------------------------
    # Utility: parse repo url
    # ------------------------------
    def parse_github_url(self, url: str):
        """Extract owner and repo from GitHub URL."""
        match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", url)
        if not match:
            raise ValueError(f"❌ Invalid GitHub URL: {url}")
        return match.group("owner"), match.group("repo")

    # ------------------------------
    # Local cloning
    # ------------------------------
    def clone_repo(self, url: str, target_dir="my_repos", fresh=True):
        """
        Clone GitHub repo locally under my_repos/owner/repo.
        If fresh=True, delete old copy before cloning.
        """
        owner, repo = self.parse_github_url(url)
        repo_path = Path(target_dir) / owner / repo

        if fresh and repo_path.exists():
            logger.info(f"🗑️ Removing old repo at {repo_path}")
            shutil.rmtree(repo_path, onerror=handle_remove_readonly)

        repo_path.parent.mkdir(parents=True, exist_ok=True)

        # Use token if provided
        clone_url = url
        if self.github_token and "@" not in url:
            clone_url = url.replace("https://", f"https://{self.github_token}@")

        logger.info(f"🔄 Cloning {owner}/{repo} into {repo_path}")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(repo_path)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"❌ Git clone failed: {result.stderr.strip()}")

        logger.info(f"✅ Cloned {owner}/{repo} successfully")
        return str(repo_path)

    # ------------------------------
    # Run gitingest
    # ------------------------------
    def run_gitingest(self, repo_url: str, output_file: str) -> Dict[str, Any]:
        """Run gitingest and return structured text."""
        temp_file = None
        try:
            if not output_file:
                fd, temp_file = tempfile.mkstemp(suffix='.txt', prefix='gitingest_')
                os.close(fd)
                output_file = temp_file

            cmd = ["gitingest", repo_url, "--output", output_file]
            if self.github_token:
                cmd.extend(["--token", self.github_token])

            env = os.environ.copy()
            if self.github_token:
                env["GITHUB_TOKEN"] = self.github_token

            logger.info(f"📦 Running gitingest on {repo_url}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
                encoding="utf-8",
                errors="replace"
            )

            if result.returncode != 0:
                return {"success": False, "error": result.stderr.strip(), "repo_url": repo_url}

            with open(output_file, "r", encoding="utf-8", errors="replace") as f:
                structured_text = f.read()

            return {"success": True, "structured_text": structured_text, "repo_url": repo_url}

        except Exception as e:
            return {"success": False, "error": str(e), "repo_url": repo_url}
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    # ------------------------------
    # High level API
    # ------------------------------
    def ingest_repo(self, repo_url: str, output_dir="gitingest_outputs", clone=True) -> Dict[str, Any]:
        """Save gitingest output and optionally clone repo locally."""
        Path(output_dir).mkdir(exist_ok=True)
        owner, repo = self.parse_github_url(repo_url)
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/{owner}_{repo}_{timestamp}.txt"

        # Run gitingest
        result = self.run_gitingest(repo_url, output_file)
        if not result["success"]:
            return result

        result["output_file"] = output_file
        logger.info(f"💾 Structured output saved: {output_file}")

        if clone:
            try:
                local_path = self.clone_repo(repo_url)
                result["local_repo"] = local_path
            except Exception as e:
                logger.warning(f"⚠️ Repo cloned skipped: {e}")
                result["local_repo"] = None

        return result


# ------------------------------
# CLI for testing
# ------------------------------
def main():
    github_token = os.getenv("GITHUB_API_TOKEN") or os.getenv("GITHUB_TOKEN")
    processor = RepoIngestor(github_token)

    repo_url = input("Enter GitHub repo URL: ").strip()
    result = processor.ingest_repo(repo_url, clone=True)

    if result["success"]:
        print("\n✅ Ingestion successful!")
        print(f"💾 Structured output: {result['output_file']}")
        if result.get("local_repo"):
            print(f"📂 Local repo clone: {result['local_repo']}")
        preview = result["structured_text"][:200].replace("\n", " ") + "..."
        print(f"📄 Preview: {preview}")
    else:
        print(f"\n❌ Failed: {result['error']}")


if __name__ == "__main__":
    main()
