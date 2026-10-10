from pathlib import Path
import shutil
import config
from utils import pdf_to_markdown, clear_directory_contents


class DocumentManager:

    def __init__(self, rag_system):
        self.rag_system = rag_system
        self.markdown_dir = Path(config.user_markdown_dir(rag_system.user_id))
        self.markdown_dir.mkdir(parents=True, exist_ok=True)

    def add_documents(self, document_paths, progress_callback=None):
        if not document_paths:
            return 0, 0

        document_paths = [document_paths] if isinstance(document_paths, str) else document_paths
        document_paths = [p for p in document_paths if p and Path(p).suffix.lower() in [".pdf", ".md"]]

        if not document_paths:
            return 0, 0

        added = 0
        skipped = 0

        for i, doc_path in enumerate(document_paths):
            if progress_callback:
                progress_callback((i + 1) / len(document_paths), f"Processing {Path(doc_path).name}")

            source_path = Path(doc_path)
            doc_name = source_path.stem
            md_path = self.markdown_dir / f"{doc_name}.md"

            if md_path.exists():
                skipped += 1
                continue

            parent_ids = []
            try:
                if source_path.suffix.lower() == ".md":
                    shutil.copy(source_path, md_path)
                else:
                    # Convert PDF → markdown directly into the user's markdown dir
                    pdf_to_markdown(str(source_path), str(self.markdown_dir))

                if not md_path.exists():
                    raise FileNotFoundError(f"Markdown conversion produced no output for {source_path.name}")

                parent_chunks, child_chunks = self.rag_system.chunker.create_chunks_single(
                    md_path,
                    source_name=source_path.name,
                )

                if not child_chunks:
                    raise ValueError("No child chunks were created — document may be empty or too short.")

                parent_ids = [parent_id for parent_id, _ in parent_chunks]
                self.rag_system.parent_store.save_many(parent_chunks)
                collection = self.rag_system.vector_db.get_collection(self.rag_system.collection_name)
                collection.add_documents(child_chunks)

                added += 1

            except Exception as e:
                import traceback
                print(f"ERROR processing {doc_path}: {e}")
                traceback.print_exc()
                self.rag_system.parent_store.delete_many(parent_ids)
                if md_path.exists():
                    md_path.unlink()
                skipped += 1

        return added, skipped

    def get_documents(self) -> list[dict]:
        sources = self.rag_system.parent_store.list_sources()
        if sources:
            return [{"name": s} for s in sources]
        return [{"name": p.name} for p in sorted(self.markdown_dir.glob("*.md"))]

    def clear_all(self):
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        self.rag_system.vector_db.delete_collection(self.rag_system.collection_name)
        clear_directory_contents(self.markdown_dir)
        self.rag_system.parent_store.clear_store()
        self.rag_system.vector_db.create_collection(self.rag_system.collection_name)
