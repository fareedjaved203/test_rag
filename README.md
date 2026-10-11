# Agentic RAG

A full-stack Agentic RAG system with per-user document isolation, hybrid search, streaming chat, and built-in evaluation.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| Agent | LangGraph |
| LLM | Ollama (local) — `granite4.1:8b` |
| Embeddings | `Qwen/Qwen3-Embedding-0.6B` (HuggingFace, auto-downloaded) |
| Vector DB | Qdrant (local, file-based) |
| Auth | JWT + bcrypt + SQLite |
| Frontend | React + Tailwind CSS (Vite) |
| Evaluation | LLM-as-judge (no external eval dependency) |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) installed and running

### Pull required models

```bash
ollama pull granite4.1:8b
ollama pull ministral-3:3b-instruct-2512-q8_0
```

> `granite4.1:8b` is the main chat model (~5GB).
> `ministral-3` is only used during evaluation runs.

### Start Ollama

On Windows, Ollama runs as a background tray app after installation — check your system tray. If it's not running:

```bash
ollama serve
```

---

## Running the Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# Start the server (auto-reloads on file changes)
python app.py
```

Server runs at **http://localhost:8000**

> On first run, the embedding model (~1.2GB) downloads automatically from HuggingFace and is cached for all future runs.

---

## Running the Frontend

Open a second terminal:

```bash
cd frontend
npm install       # only needed once
npm run dev
```

App runs at **http://localhost:5173**

---

## Usage

1. Open **http://localhost:5173**
2. **Sign up** with email and password (min 8 characters)
3. Go to **Documents** → upload PDF or Markdown files
4. Go to **Chat** → ask questions about your documents
5. Go to **Evaluation** → click **Run Evaluation** to score the RAG pipeline

> Each user account has completely isolated documents, vector store, and chat history.

---

## Project Structure

```
test_rag/
├── backend/                  # FastAPI backend
│   ├── api/                  # Route handlers (auth, chat, documents, eval)
│   ├── auth/                 # JWT auth + SQLite user model
│   ├── core/                 # RAG system, document manager, chat interface
│   ├── db/                   # Qdrant and parent store managers
│   ├── eval/                 # Evaluator + question generator
│   ├── rag_agent/            # LangGraph agent (graph, nodes, prompts, tools)
│   ├── app.py                # FastAPI entry point
│   ├── config.py             # All configuration — start here to customise
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # React + Tailwind frontend
│   └── src/
│       ├── pages/            # Login, Signup, Chat, Documents, Eval
│       ├── components/       # Layout, ProtectedRoute
│       └── context/          # AuthContext + API client
├── qdrant_db/                # Created at runtime — vector store (per user)
├── parent_store/             # Created at runtime — parent chunks (per user)
├── markdown_docs/            # Created at runtime — converted docs (per user)
└── auth.db                   # Created at runtime — user accounts
```

---

## Configuration

All settings live in `backend/config.py`. The sections below cover the most common customisations.

### Switching LLM Provider

Set `LLM_PROVIDER` and `LLM_MODEL` in `config.py`, then update the LLM initialisation in `backend/core/rag_system.py`:

```python
# Ollama (default — local, no API key needed)
LLM_PROVIDER = "ollama"
LLM_MODEL    = "granite4.1:8b"

# OpenAI
LLM_PROVIDER = "openai"
LLM_MODEL    = "gpt-4o-mini"
# pip install langchain-openai
# .env: OPENAI_API_KEY=sk-...

# Anthropic
LLM_PROVIDER = "anthropic"
LLM_MODEL    = "claude-sonnet-4-5"
# pip install langchain-anthropic
# .env: ANTHROPIC_API_KEY=sk-ant-...

# Google
LLM_PROVIDER = "google"
LLM_MODEL    = "gemini-2.5-flash"
# pip install langchain-google-genai
# .env: GOOGLE_API_KEY=...
```

Then in `backend/core/rag_system.py` replace the LLM init block:

```python
# OpenAI example
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE)
```

Same pattern applies to `JUDGE_PROVIDER` / `JUDGE_MODEL` in the eval pipeline (`backend/eval/evaluator.py`).

---

### Switching Embedding Model

Change `DENSE_MODEL` in `config.py`:

```python
DENSE_MODEL = "Qwen/Qwen3-Embedding-0.6B"          # default — multilingual, 1024 dims
DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # faster, 384 dims
DENSE_MODEL = "BAAI/bge-large-en-v1.5"              # best quality, 1024 dims
```

> ⚠️ After changing `DENSE_MODEL`, use **Clear All** in Documents and re-upload everything. The new model produces different vector dimensions and the existing Qdrant collection won't be compatible.

---

### Switching Vector Database

The vector DB is fully encapsulated in `backend/db/vector_db_manager.py`. Replace `VectorDbManager` with any LangChain-compatible vector store (Pinecone, Weaviate, pgvector, etc). The rest of the codebase only calls `create_collection`, `delete_collection`, and `get_collection`.

---

### Key Settings Reference

| Setting | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | LLM provider |
| `LLM_MODEL` | `granite4.1:8b` | Chat model name |
| `JUDGE_MODEL` | `ministral-3:3b-instruct-2512-q8_0` | Eval scoring model |
| `DENSE_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | Embedding model |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.3` | Min similarity score for retrieval |
| `DEFAULT_RETRIEVAL_K` | `7` | Chunks retrieved per query |
| `EVAL_QUESTIONS_PER_DOC` | `3` | Questions generated per document during eval |
| `JWT_EXPIRE_MINUTES` | `1440` | Token expiry (24 hours) |

---

## Notes

- **Updating a document** — no per-file replace yet. Use Clear All in Documents, then re-upload everything including the updated file.
- **Evaluation** generates `EVAL_QUESTIONS_PER_DOC` questions per indexed document, answers them through the RAG pipeline, and scores each answer using the judge LLM on four metrics: faithfulness, answer relevancy, context precision, context recall.
- **Windows symlinks warning** from HuggingFace is harmless — add `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to `.env` to silence it.
