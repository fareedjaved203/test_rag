import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Suppress OTel "Failed to detach context" warning
class _SuppressOtelDetachWarning(logging.Filter):
    def filter(self, record):
        return "Failed to detach context" not in record.getMessage()

logging.getLogger("opentelemetry.context").addFilter(_SuppressOtelDetachWarning())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from auth.models import create_tables
from api.auth import router as auth_router
from api.documents import router as documents_router
from api.chat import router as chat_router
from api.eval import router as eval_router
from dependencies import shutdown_all

create_tables()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    shutdown_all()


app = FastAPI(title="Agentic RAG API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(eval_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["."])
