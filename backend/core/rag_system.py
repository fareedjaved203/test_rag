import uuid
import sqlite3
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
import config
from db.vector_db_manager import VectorDbManager
from db.parent_store_manager import ParentStoreManager
from document_chunker import DocumentChunker
from rag_agent.tools import ToolFactory
from rag_agent.graph import create_agent_graph
from core.observability import Observability


class RAGSystem:

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.collection_name = config.user_collection_name(user_id)
        self.vector_db = VectorDbManager(qdrant_path=config.user_qdrant_db_path(user_id))
        self.parent_store = ParentStoreManager(store_path=config.user_parent_store_path(user_id))
        self.chunker = DocumentChunker()
        self.observability = Observability()
        self.agent_graph = None
        self._db_conn = None
        # Each user gets a thread_id namespaced to their user_id so
        # SQLite checkpoints from different users never collide.
        self.thread_id = f"{user_id}_{uuid.uuid4()}"
        self.recursion_limit = config.GRAPH_RECURSION_LIMIT

    def initialize(self):
        self.vector_db.create_collection(self.collection_name)
        collection = self.vector_db.get_collection(self.collection_name)

        llm = ChatOllama(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            seed=config.LLM_SEED,
        )
        tools = ToolFactory(collection).create_tools()

        # Keep the SQLite connection open for the lifetime of this RAGSystem.
        # SqliteSaver requires check_same_thread=False for FastAPI's thread pool.
        self._db_conn = sqlite3.connect(
            config.CHAT_DB_PATH,
            check_same_thread=False,
        )
        checkpointer = SqliteSaver(self._db_conn)

        self.agent_graph = create_agent_graph(llm, tools, checkpointer=checkpointer)

    def get_config(self):
        cfg = {
            "configurable": {"thread_id": self.thread_id},
            "recursion_limit": self.recursion_limit,
        }
        handler = self.observability.get_handler()
        if handler:
            cfg["callbacks"] = [handler]
        return cfg

    def reset_thread(self):
        """Start a new conversation thread (keeps history of old thread in DB)."""
        self.thread_id = f"{self.user_id}_{uuid.uuid4()}"

    def close(self):
        """Close the SQLite connection — called on app shutdown."""
        if self._db_conn:
            try:
                self._db_conn.close()
            except Exception:
                pass
