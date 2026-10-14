"""Golden sets, metrics, judges, eval runner and judge calibration (the gate is `evalkit gate`)."""

from docs_rag.evals.golden import Expected, GoldenCase, is_relevant, load_golden, save_golden
from docs_rag.evals.judge import EvalkitJudge, Judge, LexicalJudge, get_judge
from docs_rag.evals.runner import run_eval, score_case

__all__ = [
    "EvalkitJudge",
    "Expected",
    "GoldenCase",
    "Judge",
    "LexicalJudge",
    "get_judge",
    "is_relevant",
    "load_golden",
    "run_eval",
    "save_golden",
    "score_case",
]
