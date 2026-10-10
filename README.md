# Agentic RAG

A full-stack Agentic RAG system with per-user document isolation, hybrid search, streaming chat, and RAGAS evaluation.

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
| Evaluation | RAGAS |

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
5. Go to **Evaluation** → click **Run Evaluation** to auto-generate questions and score the RAG pipeline with RAGAS

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
│   ├── eval/                 # RAGAS evaluator + question generator
│   ├── rag_agent/            # LangGraph agent (graph, nodes, prompts, tools)
│   ├── app.py                # FastAPI entry point
│   ├── config.py             # All configuration
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

All backend settings are in `backend/config.py`. Key values:

| Setting | Default | Description |
|---|---|---|
| `LLM_MODEL` | `granite4.1:8b` | Ollama chat model |
| `DENSE_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | Embedding model |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.3` | Minimum similarity score for retrieval |
| `DEFAULT_RETRIEVAL_K` | `7` | Number of chunks retrieved per query |
| `EVAL_NUM_QUESTIONS` | `5` | Questions auto-generated per eval run |
| `JWT_EXPIRE_MINUTES` | `1440` | Token expiry (24 hours) |

To switch LLM provider (OpenAI, Anthropic, Google), see `backend/README.md`.

---

## Notes

- **Updating a document** — no per-file replace yet. Use Clear All in the Documents page, then re-upload everything including the updated file.
