# Btor2Sieve design

## Intent and success criteria

Deliver a usable, reproducible research tool for assignment C14: extract word-level constraints from BTOR2 safety models, validate each candidate independently, and report per-model/per-property results with replayable SMT evidence. The workspace initially contained only C14.pdf and C14_Project_Proposal.pdf. The user explicitly delegated research, design, planning, and development while unavailable; implementation decisions below are the builder's decisions.

Success means a documented install, working CLI, bit-vector and array examples, multi-property reuse analysis, public benchmark evaluation, automated semantic tests, and honest limitations. Candidate acceptance alone is not a claim of model-checking speedup or proof of the original safety property.

## Approaches considered

1. Extend Pono: strong existing frontend and verification engines, but native build/binding complexity and coupling make the assignment's independent extractor harder to reproduce.
2. Standalone Python/Z3 extraction and proof artifacts (selected): small dependency surface, precise per-candidate scope, easy experiments and external SMT replay. The frontend becomes trusted code and therefore needs particularly careful validation.
3. Full invariant synthesis or LLM-guided PDR: potentially stronger results but a larger research project, external model cost, and difficult performance evaluation. Keep as future integrations; take useful ideas (templates, solver-guided bounds, proof-checked hints) into option 2.

## Proof scopes

Let A be the conjunction of BTOR2 constraint nodes, I the initial equations, T the next-state equations, and P_j = not bad_j. Current inputs are unconstrained except where explicitly in A.

* property:j: H = P_j. Do not silently conjoin A, I, or other properties.
* model: H = A, interpreted through the encoded combinational DAG.
* initial: H = I and A. This proves initial facts only.
* transition: H = T and A. This proves a one-step relation only, not reachability.

Every accepted candidate C requires H and not C to be UNSAT in a fresh validator solver. Check satisfiability of H separately. An UNSAT H is reported as vacuous, excluded from ordinary accepted counts. SAT counterexamples and UNKNOWN reasons are retained. No property constraints are written back into BTOR2 assumptions. No claim of inductive invariance follows from these scopes. Optional invariants require explicit base and step checks and are a later increment, not a core completion requirement.

## Architecture and fixed interfaces

Python >=3.11 with z3-solver; pytest for development. A src layout and console command `btor2sieve`.

`btor2sieve/btor2.py`: dataclasses `Sort(id, kind, width=None, index=None, element=None)`, `Node(id, op, sort_id=None, args=(), params=(), symbol=None, line=0)`, `Model(sorts, nodes, source='<string>')`. Model.nodes includes directives, not sort definitions. `Model.states`, `.inputs`, `.bads`, `.constraints`, `.inits`, `.nexts` are lists of Node. `parse(text, source='<string>')->Model`, `parse_file(path)->Model`, errors are `Btor2Error(ValueError)`. Validate ordering, references, arity, widths, sorts, duplicate init/next, directive restrictions. Fair/justice are parsed with a clear safety-only limitation; unsupported semantics must fail explicitly.

`btor2sieve/encoding.py`: `Encoder(model)` has `.model`, `.terms` mapping expression IDs to Z3 expressions, `.states` and `.inputs` dicts mapping node IDs to symbols, `.next_states` dict of primed state symbols. `.expr(ref)` resolves an expression, `.bool_expr(ref)` converts a BV1 to Bool, `.property(bad_id)` returns Not(bad argument), `.assumptions`, `.initial`, `.transition` are BoolRefs. `.prime(expr)` substitutes state and input symbols with fresh primed symbols, for future checking. Bit vectors remain BitVecs, arrays remain Arrays; predicate results become BV1. Encode iteratively for deep hardware DAGs. Use deterministic ID-based names independent of user symbols.

`btor2sieve/candidates.py`: `Candidate(expr: BoolRef, family: str, origin: str, source_nodes: tuple[int,...]=())`. `GenerationOptions(max_candidates=200, max_terms=16, max_width=64, semantic=True, timeout_ms=1000, max_queries=256)`. `generate_candidates(encoder, hypothesis, roots, options=None)->list[Candidate]`. Deterministic deduplication; preserve origin and explicit rejected guesses. Families: unsigned/signed bounds, equality/disequality, implication, masked bits, array reads/writes. Syntactic atom mining and word-level structural templates are the cheap baseline. Optional SMT-guided binary bound search and known-bit discovery generate additional candidates, each revalidated independently. Cap work with term/candidate/query/time budgets; candidate budgets do not mean completeness.

`btor2sieve/validation.py`: scope construction and independent validator; validator accepts arbitrary Candidate, never trusts generator metadata. Results include exact hypothesis, expression, family, source, SAT/UNSAT/UNKNOWN, duration, counterexample or reason, and self-contained SMT-LIB2 obligation. Replay parses artifacts into a new solver or invokes an explicit external executable without a shell. Obligation replay is evidence under the solver trust assumption, not a proof certificate checked by a proof kernel.

`btor2sieve/pipeline.py`, `reporting.py`, `cli.py`: analyze model, scopes, all candidates; optional cross-property revalidation; aggregate CSV and JSON and local HTML report; `inspect`, `extract`, `batch`, `replay` commands. Stable filenames, escaped HTML, source hashes, runtime/software configuration, failures explicit. Existing output directories are not silently overwritten. Batch records errors and continues, returning a nonzero code if any model failed.

## Evaluation

Hand-written regressions cover arrays, multiple properties, wraparound, contradictory hypotheses, invalid candidates, input constraints, uninitialized and missing-next states, signed operations, overflow, malformed sorts, and deep DAGs. Public benchmarks come from verified upstream sources with URLs, hashes, and licensing/provenance, separately labeled from synthetic examples. Report theory features, candidate families, accepted/rejected/unknown/vacuous counts, extraction/validation times. Replay every accepted benchmark obligation in a new process and, if available, a second solver. Compare syntax-only and semantic extraction on the same selection and budgets; avoid speedup claims from tiny smoke tests.

## Risks and limits

SMT and frontend correctness are trusted. Solver timeout is per query, not a complete wall-clock guarantee. Extraction is bounded and incomplete. Safety properties only: fair/justice declarations do not become safety assumptions. Large array or nonlinear BV instances may return unknown/timeout. No Pono integration or full HWMCC performance claim is required to meet the core assignment. Public benchmark access and licensing may constrain redistributable examples; fetch scripts and manifests are acceptable.
