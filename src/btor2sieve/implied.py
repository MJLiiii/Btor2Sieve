"""Compatibility imports; the paper method lives in methods/implied_constraints.py.

New code should import from methods.implied_constraints. This module contains
no extraction implementation.
"""

from .methods.implied_constraints import find_equivalences, generate_implied_candidates

__all__ = ["find_equivalences", "generate_implied_candidates"]
