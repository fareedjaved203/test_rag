import os

# --- Directory Configuration ---
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Per-user dirs are built at runtime as: <BASE>/<user_id>
MARKDOWN_DIR = os.path.join(_BASE_DIR, "markdown_docs")
PARENT_STORE_PATH = os.path.join(_BASE_DIR, "parent_store")
QDRANT_DB_PATH = os.path.join(_BASE_DIR, "qdrant_db")

# Auth / SQLite
AUTH_DB_PATH = os.path.join(_BASE_DIR, "auth.db")

# Chat history persistence
CHAT_DB_PATH = os.path.join(_BASE_DIR, "chat_history.db")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ---------------------------------------------------------------------------
# Vector Database
# ---------------------------------------------------------------------------
# Backend: "qdrant" (only supported option currently)
# To switch: replace VectorDbManager in backend/db/vector_db_manager.py
VECTOR_DB_BACKEND = "qdrant"
CHILD_COLLECTION_PREFIX = "document_child_chunks"  # suffixed with user_id at runtime
SPARSE_VECTOR_NAME = "sparse"

# ---------------------------------------------------------------------------
# LLM Provider
# ---------------------------------------------------------------------------
# Provider: "ollama" | "openai" | "anthropic" | "google"
# To switch provider:
#   1. Set LLM_PROVIDER below
#   2. Set the model name in LLM_MODEL
#   3. Add the API key to .env (not needed for ollama)
#   4. Install the matching package: pip install langchain-openai / langchain-anthropic / langchain-google-genai
#   5. Update the LLM initialisation in backend/core/rag_system.py (see comments there)
LLM_PROVIDER = "ollama"
LLM_MODEL = "granite4.1:8b"
LLM_TEMPERATURE = 0
LLM_SEED = 42

# Judge model used only during evaluation (can be a smaller/cheaper model)
JUDGE_PROVIDER = "ollama"
JUDGE_MODEL = "ministral-3:3b-instruct-2512-q8_0"

# ---------------------------------------------------------------------------
# Embedding Model
# ---------------------------------------------------------------------------
# Dense model: any HuggingFace sentence-transformer model name
# Sparse model: fastembed sparse model (BM25 recommended)
#
# ⚠️  Changing DENSE_MODEL after documents are indexed requires:
#     Clear All documents → re-upload → re-index
#     (vector dimensions will not match existing Qdrant collection)
#
# Popular alternatives:
#   "sentence-transformers/all-MiniLM-L6-v2"   — fast, 384 dims
#   "sentence-transformers/all-mpnet-base-v2"   — high quality, 768 dims
#   "BAAI/bge-large-en-v1.5"                    — best quality, 1024 dims
DENSE_MODEL = "Qwen/Qwen3-Embedding-0.6B"
SPARSE_MODEL = "Qdrant/bm25"

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
RETRIEVAL_SCORE_THRESHOLD = 0.3   # lower = more recall, higher = more precision
DEFAULT_RETRIEVAL_K = 7            # number of child chunks returned per search
CHILD_CHUNK_SEPARATOR = "\n\n<CHILD_CHUNK_BOUNDARY>\n\n"

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
MAX_TOOL_CALLS = 8
MAX_ITERATIONS = 10
GRAPH_RECURSION_LIMIT = 50
MAIN_HISTORY_MESSAGES_TO_KEEP = 4
BASE_TOKEN_THRESHOLD = 2000
TOKEN_GROWTH_FACTOR = 0.9

# ---------------------------------------------------------------------------
# Terminal Execution Logging
# ---------------------------------------------------------------------------
EXECUTION_LOGGING_ENABLED = False
EXECUTION_LOG_MAX_CHARS = 1200
EXECUTION_LOG_USE_COLOR = True

# ---------------------------------------------------------------------------
# Text Splitter
# ---------------------------------------------------------------------------
CHILD_CHUNK_SIZE = 500
CHILD_CHUNK_OVERLAP = 100
MIN_PARENT_SIZE = 2000
MAX_PARENT_SIZE = 4000
HEADERS_TO_SPLIT_ON = [
    ("#", "H1"),
    ("##", "H2"),
    ("###", "H3")
]

# ---------------------------------------------------------------------------
# Langfuse Observability (optional)
# ---------------------------------------------------------------------------
LANGFUSE_ENABLED = os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_BASE_URL = os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3000")

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
EVAL_QUESTIONS_PER_DOC = 3  # questions generated per document during evaluation


# ---------------------------------------------------------------------------
# Per-user path helpers
# ---------------------------------------------------------------------------
def user_markdown_dir(user_id: str) -> str:
    return os.path.join(MARKDOWN_DIR, user_id)

def user_parent_store_path(user_id: str) -> str:
    return os.path.join(PARENT_STORE_PATH, user_id)

def user_qdrant_db_path(user_id: str) -> str:
    return os.path.join(QDRANT_DB_PATH, user_id)

def user_collection_name(user_id: str) -> str:
    return f"{CHILD_COLLECTION_PREFIX}_{user_id}"
