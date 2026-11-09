"""Compatibility imports; the original method lives in methods/word_level.py.

New code should import shared types from methods.common and generation from
methods.word_level. This module contains no extraction implementation.
"""

from .methods.common import Candidate, GenerationOptions
from .methods.word_level import generate_candidates, select_scope_candidates

__all__ = ["Candidate", "GenerationOptions", "generate_candidates", "select_scope_candidates"]
