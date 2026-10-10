import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth.models import User
from auth.utils import get_current_user
from core.document_manager import DocumentManager
from core.rag_system import RAGSystem
from dependencies import get_rag_system
import config

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(
    current_user: User = Depends(get_current_user),
    rag_system: RAGSystem = Depends(get_rag_system),
):
    doc_manager = DocumentManager(rag_system)
    return {"documents": doc_manager.get_documents()}


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    rag_system: RAGSystem = Depends(get_rag_system),
):
    doc_manager = DocumentManager(rag_system)

    # Save uploads to a staging subdir inside the user's own folder
    # so pymupdf can open them without temp-dir cleanup issues on Windows
    staging_dir = Path(config.user_markdown_dir(rag_system.user_id)) / "_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    try:
        for upload in files:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in (".pdf", ".md"):
                continue
            dest = staging_dir / upload.filename
            with dest.open("wb") as f:
                shutil.copyfileobj(upload.file, f)
            saved_paths.append(str(dest))

        if not saved_paths:
            raise HTTPException(status_code=400, detail="No valid PDF or Markdown files provided")

        added, skipped = doc_manager.add_documents(saved_paths)

    finally:
        # Clean up staging dir after processing is fully done
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)

    return {"added": added, "skipped": skipped}


@router.delete("")
def clear_documents(
    current_user: User = Depends(get_current_user),
    rag_system: RAGSystem = Depends(get_rag_system),
):
    doc_manager = DocumentManager(rag_system)
    try:
        doc_manager.clear_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "All documents cleared"}
