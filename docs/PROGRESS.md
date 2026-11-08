# Btor2Sieve execution ledger

Plan: docs/superpowers/plans/2026-11-08-btor2sieve.md

2026-11-08: Read both supplied PDFs (text and rendered pages); workspace has no existing code or git repository. Quick memory search found no project-specific history.

Ruling: proceed without approval checkpoints because the user explicitly delegated the full research/design/build task while asleep.

Ruling: select Python/Z3 standalone architecture, with strict proof-scope separation and external SMT replay. Pono integration is optional per assignment and deferred unless core work leaves a compelling reason.

Research agents: research_constraints (soundness and methods), research_frontend (format and benchmarks). Root: design, validation, integration, evaluation.

Implemented frontend/encoder, syntax and semantic candidate discovery, independent validator, CLI, per-scope/family CSV, searchable HTML, provenance JSON, SMT exports, cross-property checks and optional cvc5 replay.

Ruling: initialized a new local Git repository on feat/btor2sieve; there was no existing branch/history to isolate. User PDFs preserved unchanged. No remote or publication was created.

Frontend review: 61 initial parser/encoding tests passed; all 13 licensed public corpus files accepted by upstream catbtor and local frontend. Research corpus includes 4 byte-identical HWMCC19 entries, 2 family examples, 7 upstream regressions.

Core independent review found omitted hypothesis replay and inconsistent partial-model counts. Both reproduced, fixed with regressions, and re-reviewed cleanly in docs/review-core.md.

Candidate refinement: full-cone selection reserves terms for word expressions beyond Boolean wrappers. Tests cover deep wrappers, zero budgets, signed/unsigned families, nontrivial array facts, partial queries and independent validation. Earlier baseline artifacts retained in results/public-evaluation; final extraction in results/final-evaluation.

Final public extraction: 13 models, 23 properties, 36 scopes; syntax 90/1912 accepted; semantic 92/1914 accepted. Independent Z3/cvc5 replay confirmed 126 and 128 accepted-implication/hypothesis checks respectively. Demo: 89 accepted, 363 rejected, 6 vacuous; reuse 23 accepted and 93 rejected.

Broader demo exposed cvc5 constant-array satisfiability configuration; added failing regression, enabled arrays-exp, replayed all 127 demo checks successfully in both solvers. Final reviewer found explicit-Z3-context API edge; added regression and made validator solvers context-aware.

Browser check: local HTML visually inspected; search and status filters showed the expected 2 matching records in the first demo. Current report uses the same tested layout. Source and hypothesis evidence downloads are plain local links.

Packaging: editable CLI worked outside the checkout; pure-Python wheel built and installed with cached Z3 into a fresh environment. Final smoke test and final review/test receipts recorded at completion.

Completion verification: 95 pytest tests passed; all corpus hashes passed; final reviewer reports no outstanding findings. Final replay receipts include solver versions/options. Rebuilt wheel installed into a fresh environment offline; extraction and replay exercised outside checkout. Keeping feat/btor2sieve locally; no remote push or merge.
