"""
Auto-generate evaluation questions from indexed documents using the LLM.
Questions are grounded in actual parent chunks so they are answerable by the RAG system.
"""
from __future__ import annotations

import random
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
    num_questions: int = config.EVAL_NUM_QUESTIONS,
) -> list[dict]:
    """
    Sample parent chunks and generate questions from them.
    Returns list of {"question": str, "reference_context": str, "source": str}
    """
    llm = ChatOllama(
        model=config.LLM_MODEL,
        temperature=0.3,
        seed=config.LLM_SEED,
    )

    # Gather all parent chunk IDs
    all_ids = [
        p.stem
        for p in __import__("pathlib").Path(parent_store._ParentStoreManager__store_path).glob("*.json")
    ]

    if not all_ids:
        return []

    # Sample chunks — try to spread across different source docs
    sample_size = min(num_questions * 2, len(all_ids))
    sampled_ids = random.sample(all_ids, sample_size)

    qa_pairs = []
    questions_needed = num_questions

    for pid in sampled_ids:
        if questions_needed <= 0:
            break

        try:
            chunk = parent_store.load_content(pid)
        except Exception:
            continue

        content = chunk.get("content", "").strip()
        source = chunk.get("metadata", {}).get("source", "unknown")

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
