# NaviGit: AI-Powered Codebase Navigator

NaviGit is a Flask-based web application that allows you to ingest, index, and chat with your code repositories using large language models (LLMs) such as GPT-OSS (via Hugging Face or Ollama). It provides a modern UI for exploring code, saving chat history, and leveraging retrieval-augmented generation (RAG) for code understanding.

---

## Features

- **Repository Ingestion:** Add public or private GitHub repositories for analysis.
- **Code Indexing:** Automatically chunk, embed, and index code for semantic search.
- **Chat with Code:** Ask questions about your codebase and get context-aware answers from an LLM.
- **Saved Chats:** Save and organize chat responses as markdown files for future reference.
- **Modern UI:** File explorer, chat interface, and saved chat management.
- **Supports Multiple LLM Backends:** Use Hugging Face API or run models locally with Ollama.

---

## Requirements

- Python 3.9 or newer
- Git (for repo ingestion)
- [Ollama](https://ollama.com/) (optional, for local LLM inference)
- Windows machine (due to limited availability of different Machines And OS, I Could only test this for windows)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root for sensitive configuration:

```
HF_API_KEY=your_huggingface_api_key_here
```

- `HF_API_KEY` is required if you use Hugging Face's hosted LLMs.
- For Ollama, no API key is needed.

---

## Usage

### 1. Start the Flask App

```bash
python app.py
```

The app will be available at `http://localhost:5000`.

### 2. Ingest a Repository

- Enter a GitHub repository URL in the UI.
- (Optional) Provide a GitHub Personal Access Token for private repos.
- Click "Ingest" to process and index the repository.

### 3. Chat with Your Codebase

- Select the ingested repository from the dashboard.
- Use the chat interface to ask questions about the codebase.
- The LLM will answer using context from the indexed code.

### 4. Save and Manage Chats

- Save any AI response as a markdown file.
- View, search, and reuse saved chats from the sidebar.

---

## Shell Mode

Beauty of NaviGit is that it let's the user go totally offline, does not even need a browser to interact with it, Most of larger codespaces have a shared server that can be only accessed with cli, so NaviGit is inbuilt with its own CLI support without the need of even turning on the flask App

### 1. Run the command -> python ingest.py

- Terminal will prompt you to enter the github repo url, and PAT only needed for private repos
- After successful ingestion move on to next step

### 2. Run the command -> python rag_repo.py

- This will start building the indexes if not already built
- Once built you can directly chat with GPT OSS for your queries related to the codebase!



## Switching LLM Backend

### Using Hugging Face (default)

- Ensure `HF_API_KEY` is set in your `.env`.
- The app will use Hugging Face's GPT-OSS endpoint.

### Using Ollama (local)

- Install and run [Ollama](https://ollama.com/).
- Pull a model, e.g.:
  ```bash
  ollama pull gpt-oss:20b
  ```
- In `rag_repo.py`, comment out the Hugging Face `ask_llm` function and uncomment the Ollama version:
    ```python
    def ask_llm(prompt: str):
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # Any string, not used by Ollama
        )
        completion = client.chat.completions.create(
            model="gpt-oss:20b",  # Or your preferred model
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    ```
- Restart the Flask app.

---

## Troubleshooting

- **WebSocket Disconnects:** In development, the chat may disconnect on code changes. This is normal due to Flask's auto-reload. Run on gunicorn rather than Werkzeug
- **Indexing Errors:** Ensure the repository URL is correct and accessible. For private repos, use a valid GitHub token. Timeouts may occur if your Network speed is a bottleneck
- **LLM Errors:** Check your API key, model name, and backend availability.
- **Torch Errors** During installing sentence transformers, you may run into pyTorch errors, you can fix them by just installing the appropriate torch versions!
---

## Project Structure

```
noodl/
├── app.py
├── rag_repo.py
├── requirements.txt
├── .env
├── static/
│   └── index.css
├── templates/
│   ├── index.html
│   └── workspace.html
├── indexes/
│   └── <repo>/
│       ├── repo.index
│       ├── chunks.json
│       ├── graph.pkl
│       └── saved_chats/
└── ...
```

---

## License

This project is Open Sourced, feel free to contribute, expand and fork this project into something amazing. Review the licenses of any LLMs or datasets you use with this tool.

---

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/)
- [Ollama](https://ollama.com/)
- [Hugging Face](https://huggingface.co/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
