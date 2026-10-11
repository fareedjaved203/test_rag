"""
Auto-generate evaluation questions from indexed documents using the LLM.
Generates EVAL_QUESTIONS_PER_DOC questions per source document so every
document is represented in the evaluation regardless of corpus size.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

import config


_GENERATION_PROMPT = """You are a question generator for evaluating a RAG system.
Given a document excerpt, generate {n} factual questions that:
- Can be answered directly from the excerpt
- Are specific and concrete (not vague or generic)
- Cover different facts or topics within the excerpt
- Are standalone questions (no pronouns like "it" or "this")

Return ONLY the questions, one per line, no numbering, no extra text."""


def generate_questions_for_chunks(
    parent_store,
    num_questions_per_doc: int = config.EVAL_QUESTIONS_PER_DOC,
) -> list[dict]:
    """
    Generate questions spread evenly across all indexed source documents.
    Returns list of {"question": str, "reference_context": str, "source": str}
    """
    llm = ChatOllama(
        model=config.LLM_MODEL,
        temperature=0.3,
        seed=config.LLM_SEED,
    )

    store_path = Path(parent_store._ParentStoreManager__store_path)
    all_ids = [p.stem for p in store_path.glob("*.json")]

    if not all_ids:
        return []

    # Group chunk IDs by source document
    chunks_by_source: dict[str, list[str]] = defaultdict(list)
    for pid in all_ids:
        try:
            chunk = parent_store.load_content(pid)
            source = chunk.get("metadata", {}).get("source", "unknown")
            chunks_by_source[source].append(pid)
        except Exception:
            continue

    qa_pairs = []

    for source, chunk_ids in chunks_by_source.items():
        questions_needed = num_questions_per_doc
        # Try each chunk until we have enough questions for this doc
        for pid in chunk_ids:
            if questions_needed <= 0:
                break
            try:
                chunk = parent_store.load_content(pid)
            except Exception:
                continue

            content = chunk.get("content", "").strip()
            if len(content) < 200:
                continue

            n_to_gen = min(2, questions_needed)
            prompt = _GENERATION_PROMPT.format(n=n_to_gen)

            try:
                response = llm.invoke([
                    SystemMessage(content=prompt),
                    HumanMessage(content=f"Document excerpt:\n\n{content[:3000]}"),
                ])
                lines = [l.strip() for l in response.content.strip().splitlines() if l.strip()]
                for question in lines[:n_to_gen]:
                    qa_pairs.append({
                        "question": question,
                        "reference_context": content,
                        "source": source,
                    })
                    questions_needed -= 1
            except Exception as e:
                print(f"Question generation failed for {pid}: {e}")
                continue

    return qa_pairs
