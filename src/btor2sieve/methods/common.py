"""Candidate representation and budgets shared by both extraction methods."""

from __future__ import annotations

from dataclasses import dataclass

import z3


@dataclass(frozen=True)
class Candidate:
    expr: z3.BoolRef
    family: str
    origin: str
    source_nodes: tuple[int, ...] = ()


@dataclass(frozen=True)
class GenerationOptions:
    max_candidates: int = 200
    max_terms: int = 16
    max_width: int = 64
    semantic: bool = True
    timeout_ms: int = 1000
    max_queries: int = 256
    method: str = "word-level"
