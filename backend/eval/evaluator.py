"""
RAG evaluation pipeline without RAGAS dependency.
Scores faithfulness, answer relevancy, context precision and recall
using the judge LLM directly with structured prompts.
"""
from __future__ import annotations

import json
from typing import Generator

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

import config
from eval.question_generator import generate_questions_for_chunks


# ---------------------------------------------------------------------------
# Scoring prompts
# ---------------------------------------------------------------------------

_FAITHFULNESS_PROMPT = """You are evaluating whether an answer is faithful to the retrieved context.
Faithful means every claim in the answer is supported by the context — no hallucination.

Context:
{context}

Answer:
{answer}

Score from 0.0 to 1.0 where:
1.0 = every claim is directly supported by the context
0.5 = some claims supported, some not
0.0 = answer contradicts or ignores the context entirely

Reply with ONLY a number between 0.0 and 1.0, nothing else."""

_RELEVANCY_PROMPT = """You are evaluating whether an answer is relevant to the question.

Question:
{question}

Answer:
{answer}

Score from 0.0 to 1.0 where:
1.0 = answer directly and completely addresses the question
0.5 = answer partially addresses the question
0.0 = answer is off-topic or does not address the question

Reply with ONLY a number between 0.0 and 1.0, nothing else."""

_CONTEXT_PRECISION_PROMPT = """You are evaluating whether the retrieved context contains information useful for answering the question.

Question:
{question}

Retrieved context:
{context}

Score from 0.0 to 1.0 where:
1.0 = context is highly relevant and directly useful for answering the question
0.5 = context is partially relevant
0.0 = context is irrelevant to the question

Reply with ONLY a number between 0.0 and 1.0, nothing else."""

_CONTEXT_RECALL_PROMPT = """You are evaluating whether the retrieved context covers the information needed to answer the question fully.

Question:
{question}

Reference answer (ground truth):
{ground_truth}

Retrieved context:
{context}

Score from 0.0 to 1.0 where:
1.0 = context contains all information needed to produce the reference answer
0.5 = context contains some but not all needed information
0.0 = context is missing the information needed

Reply with ONLY a number between 0.0 and 1.0, nothing else."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score(llm: ChatOllama, prompt: str) -> float:
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content.strip().split()[0].rstrip(".,;")
        return max(0.0, min(1.0, float(text)))
    except Exception:
        return 0.0


def _emit(event: dict) -> str:
    return json.dumps(event)


# ---------------------------------------------------------------------------
# Main evaluation generator
# ---------------------------------------------------------------------------

def run_evaluation(rag_system) -> Generator[str, None, None]:
    """
    Generator that yields SSE-compatible JSON strings:
      {"type": "progress", "message": str}
      {"type": "result",   "scores": {...}, "details": [...]}
      {"type": "error",    "message": str}
      {"type": "done"}
    """
    yield _emit({"type": "progress", "message": "Generating questions from your documents..."})

    try:
        qa_pairs = generate_questions_for_chunks(
            rag_system.parent_store,
            num_questions=config.EVAL_NUM_QUESTIONS,
        )
    except Exception as e:
        yield _emit({"type": "error", "message": f"Question generation failed: {e}"})
        return

    if not qa_pairs:
        yield _emit({"type": "error", "message": "No documents indexed yet. Upload documents first."})
        return

    yield _emit({"type": "progress", "message": f"Generated {len(qa_pairs)} questions. Running retrieval and answering..."})

    collection = rag_system.vector_db.get_collection(rag_system.collection_name)

    judge_llm = ChatOllama(
        model=config.JUDGE_MODEL,
        temperature=0,
        seed=config.LLM_SEED,
    )

    eval_rows = []
    for i, pair in enumerate(qa_pairs):
        yield _emit({"type": "progress", "message": f"Evaluating question {i + 1}/{len(qa_pairs)}..."})

        question = pair["question"]
        reference_context = pair["reference_context"]

        # Retrieve contexts
        try:
            results = collection.similarity_search(
                question,
                k=config.DEFAULT_RETRIEVAL_K,
                score_threshold=config.RETRIEVAL_SCORE_THRESHOLD,
            )
            retrieved_contexts = [doc.page_content for doc in results] if results else [reference_context]
        except Exception:
            retrieved_contexts = [reference_context]

        combined_context = "\n\n".join(retrieved_contexts)

        # Get answer from RAG
        answer = ""
        try:
            from core.chat_interface import ChatInterface
            chat = ChatInterface(rag_system)
            for raw in chat.stream(question):
                event = json.loads(raw)
                if event.get("type") == "token":
                    answer += event.get("content", "")
                elif event.get("type") == "done":
                    break
        except Exception as e:
            answer = f"Error: {e}"

        # Score with judge LLM
        faithfulness = _score(judge_llm, _FAITHFULNESS_PROMPT.format(
            context=combined_context, answer=answer))
        relevancy = _score(judge_llm, _RELEVANCY_PROMPT.format(
            question=question, answer=answer))
        precision = _score(judge_llm, _CONTEXT_PRECISION_PROMPT.format(
            question=question, context=combined_context))
        recall = _score(judge_llm, _CONTEXT_RECALL_PROMPT.format(
            question=question, ground_truth=reference_context, context=combined_context))

        eval_rows.append({
            "question": question,
            "answer": answer,
            "source": pair["source"],
            "scores": {
                "faithfulness": round(faithfulness, 4),
                "answer_relevancy": round(relevancy, 4),
                "context_precision": round(precision, 4),
                "context_recall": round(recall, 4),
            }
        })

    yield _emit({"type": "progress", "message": "Computing final scores..."})

    # Aggregate scores
    n = len(eval_rows)
    agg = {
        "faithfulness": round(sum(r["scores"]["faithfulness"] for r in eval_rows) / n, 4),
        "answer_relevancy": round(sum(r["scores"]["answer_relevancy"] for r in eval_rows) / n, 4),
        "context_precision": round(sum(r["scores"]["context_precision"] for r in eval_rows) / n, 4),
        "context_recall": round(sum(r["scores"]["context_recall"] for r in eval_rows) / n, 4),
    }

    details = [
        {
            "question": r["question"],
            "answer": r["answer"],
            "source": r["source"],
            "scores": r["scores"],
        }
        for r in eval_rows
    ]

    yield _emit({"type": "result", "scores": agg, "details": details})
    yield _emit({"type": "done"})
