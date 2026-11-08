# Methods and soundness contract

Btor2Sieve implements a bounded, word-level generate-and-validate pipeline. It is a constraint extractor, not a reachability model checker. The project decision is to make the core C14 deliverable easy to install, inspect, and reproduce, then leave model-checker integration as a separately measurable extension.

## Research basis and alternatives

The selected architecture combines finite templates, solver-guided abstraction of a fixed predicate, and independent implication checks. [Cabodi et al. (DATE 2009)](https://past.date-conference.com/proceedings-archive/2009/DATE09/PDFFILES/12.6_3.PDF) supplies the property-constraint motivation; [Froleyks et al. (FM 2026)](https://link.springer.com/chapter/10.1007/978-3-032-26204-2_9) makes the different constraint classes and their safe use explicit. Their work is not evidence that this implementation speeds up a model checker.

[Houdini (FME 2001)](https://fastpl.doc.ic.ac.uk/SoftwareReliability/2016-2017/papers/Houdini.pdf) motivates finite candidate sets, but this implementation checks a fixed hypothesis, rather than mutually dependent inductive annotations. [Yao et al. (ASE 2023)](https://rainoftime.github.io/files/ASE23Invariant.pdf) studies richer bit-vector invariant templates; quantified synthesis was rejected for the first release because it adds cost and complexity beyond the implication task. The [July 2026 BII preprint](https://arxiv.org/abs/2607.26386) is relevant to progressive bound refinement, but its best-inductive-invariant problem is different from ours.

[Pono 2.0 (FM 2026)](https://www.sosy-lab.org/research/pub/2026-FM.Pono_2.0_A_Versatile_SMT-Based_Model_Checker_for_Safety_and_Liveness.pdf) offers mature engines and array reasoning for a future integration. The [September 2026 LLM4PDR preprint](https://arxiv.org/abs/2609.30131) suggests a future untrusted hint backend. An external LLM is unnecessary for this product; any future hints must enter the same typed validation boundary.

The detailed reading notes, page references, opportunity comparison, and counterexamples are in [constraint-literature.md](research/constraint-literature.md). The current implementation is an engineering synthesis of these ideas, with no claim of a new state-of-the-art algorithm.

## Frontend

BTOR2 is parsed into a typed DAG and encoded iteratively into Z3. Native fixed-size bit-vectors preserve modular arithmetic, signed/unsigned order, shifts, overflow and bitwise operations. Arrays remain SMT arrays with `select`, `store`, equality and constant-array initialization. Predicates inside the BTOR2 DAG are one-bit words; scope hypotheses convert them to Boolean formulas explicitly.

Negative references are bitwise complement, not arithmetic negation. Negative array references are rejected. Missing initial and next assignments leave the corresponding variables unconstrained; missing next is not implicit stuttering. Primed input symbols are fresh. User symbols are retained as metadata, while solver symbols use deterministic `s_ID`, `i_ID`, and `_next` names to avoid collisions.

The reader checks ordering, arity, sorts, bit widths, constants, directives, and initial/next assignments. See [frontend research](research/btor2-frontend.md) for upstream references and exact compatibility limits. Fairness and justice nodes are retained and disclosed, but are not converted to finite safety assumptions. No liveness result is produced.

## Four exact hypotheses

Let `A` be original BTOR2 constraints, `I` initialization, `T` next equations, and `P_j = not bad_j`. The definitions of all referenced expressions are expanded in the SMT DAG.

| Scope | Hypothesis H | Meaning of accepted H => C |
| --- | --- | --- |
| `property:j` | `P_j` | Consequence of this safety predicate over all valuations, even unreachable ones |
| `model` | `A` | Consequence of original assumptions and combinational semantics |
| `initial` | `I and A` | Initial-frame fact only |
| `transition` | `T and A` | One-step relation with the source-frame environment |

`model` is a CLI label, not a claim of having inferred a reachable invariant in the FM2026 terminology. Transition scope does not add next-frame `A'`. Its templates include primed states; a total functional transition would otherwise impose no additional condition on current-state words.

Do not insert property-derived candidates as BTOR2 `constraint` lines. For example, a wrapping counter starting at zero reaches 2 and violates `P = x < 2`. Although `P => x != 2`, assuming `x != 2` removes the first bad state. A future property-preserving transformation needs its own first-failure argument and validation. The extractor performs no such transformation.

## Candidate generation

Generation is deliberately untrusted. The syntax baseline proposes existing comparison atoms and negations, local guarded implications, same-sort equalities/disequalities, signed/unsigned comparisons with constants and neighboring values, masks/slices, and native array read/write relations. Bounds are fixed-width comparisons, not mathematical-integer approximations. The full dependency cone is walked iteratively, then the term budget is shared among word declarations/reads, nearby predicates/guards, word operations, and literals, with Boolean scaffolding filling remaining slots. This reaches useful word terms behind deep Boolean wrappers; the configured term budget limits the proposal vocabulary, not parsing or DAG traversal.

Semantic discovery additionally queries the original hypothesis in a separate incremental solver. For an unsigned word of width `w`, search the finite range `[0, 2^w-1]`:

* Minimum: ask whether `H and x <=u middle` is satisfiable. SAT lowers the search ceiling; UNSAT raises the guaranteed lower bound.
* Maximum: ask whether `H and x >u middle` is satisfiable. SAT raises the search floor; UNSAT lowers the guaranteed upper bound.
* Known bits: obtain one satisfying assignment of H. For each sampled word bit with model value b, ask whether `H and bit != b` is satisfiable. Only UNSAT justifies adding that bit to a known-bit mask.

Complete binary searches use at most `w` queries per endpoint. Partial search may return a weaker bound already justified by completed UNSAT checks. Discovery stops on UNKNOWN or query exhaustion. A finite candidate/query/term/width budget makes extraction incomplete by design. Syntax and semantic candidates share the candidate budget; therefore semantic mode is not necessarily a superset of the baseline.

Deduplication uses normalized expressions; obvious tautologies and the normalized hypothesis itself are suppressed. This is not an expensive logical independence or minimality test. Accepted constraints can overlap or be semantically equivalent; counts measure validated formulas, not independent information or novelty. Structural array identities retained by the generator are suppressed by the pipeline when they simplify to true.

## Independent validation and replay

The validator first asks whether H is satisfiable. It then creates a fresh solver for every candidate, asserting only `H` and `not C`. It never receives the discovery solver or any previously accepted candidate as an extra assumption.

| Implication result | H result | Reported status |
| --- | --- | --- |
| SAT | any | rejected, with an SMT counterexample |
| UNSAT | SAT | accepted |
| UNSAT | UNSAT | vacuous, excluded from accepted counts |
| UNKNOWN | any | unknown, with reason |
| UNSAT | UNKNOWN | unknown: implication proved, non-vacuity unresolved |

All query artifacts are self-contained SMT-LIB2 with explicit logic. JSON stores source hashes, exact hypotheses, candidate expressions, source node IDs, solver/version/configuration, status, timing, and artifact hashes. Replay checks hashes and solves both implications and hypotheses in fresh solver instances. A separate CLI invocation gives process separation; optional cvc5 gives solver diversity. `--accepted-only` still replays hypotheses so non-vacuity evidence is included. A failed, empty, or mismatched replay exits nonzero.

The trusted computing base includes the BTOR2 parser/encoder and the SMT backend. Cross-solver agreement reduces solver-specific risk but does not independently validate the frontend. SMT obligations are not proof certificates checked by a small proof kernel. Source provenance and frontend semantic tests address a different part of this trust boundary.

## Cross-property reuse

An accepted candidate from property j is merely a proposal for property k. Reuse repeats `P_k and not C` in the target validator. Rejected reuse is retained. Reuse counts and timings are separate records and do not inflate ordinary candidate counts. A per-target reuse limit prevents an unbounded quadratic property comparison.

## Resource and reporting policy

Solver timeouts apply per query. They are not a process-wide timeout or memory limit. Parsing, encoding, formatting and report writing also take time. Large models and complex arrays can exceed practical memory or latency budgets; this release is validated on a small public corpus, not all HWMCC instances.

Each model commits its records and summaries atomically to the run report. A malformed input or failed candidate aborts that model, records an error and removes its partial obligations; batch processing continues with other models and exits nonzero. Existing output directories are never overwritten. HTML is escaped, static, searchable, and usable directly from disk.
