# Method and soundness contract

Btor2Sieve implements property-only native implied-constraint extraction with
independent validation. The retired original `word-level` method and the earlier Boolean
literal method are preserved in the movable [archive](../archive/README.md).
It is a constraint extractor, not a reachability model checker. Model-checker
integration remains a separately measurable extension.

## Code boundaries

The package follows the data flow described in the [source walkthrough](../README.md#find-your-way-around-the-code). Pono parses every model; `read_model` in `pono.py` returns each property P as a Z3 formula. `property_scopes` in `validation.py` turns those into property hypotheses. The pipeline calls `discover_implied_candidates` in `implied.py`, then `Validator` checks each proposal independently. The pipeline records obligations and results, and the reporting module renders those plain dictionaries.

`implied.py` also defines `Candidate` and `GenerationOptions`.
`vocabulary.py` chooses the property's terms and predicates, including the
source-term and width selection used by bounded extraction.

Report replay is a separate operation: `replay(path, *, backend="z3", timeout_ms=5000, accepted_only=False)` in `replay.py` returns a result dictionary and an exit code. It verifies report artifacts and calls `validation.replay_smt2` for each query. The CLI supplies arguments and presents the result. This separation keeps argument parsing and report loading out of the proof checks.

## Research basis and alternatives

The selected architecture combines finite templates, solver-guided abstraction of a fixed predicate, and independent implication checks. [Cabodi et al. (DATE 2009)](https://past.date-conference.com/proceedings-archive/2009/DATE09/PDFFILES/12.6_3.PDF) supplies the property-constraint motivation; [Froleyks et al. (FM 2026)](https://link.springer.com/chapter/10.1007/978-3-032-26204-2_9) makes the different constraint classes and their safe use explicit. Their work is not evidence that this implementation speeds up a model checker.

[Houdini (FME 2001)](https://fastpl.doc.ic.ac.uk/SoftwareReliability/2016-2017/papers/Houdini.pdf) motivates finite candidate sets, but this implementation checks a fixed hypothesis, rather than mutually dependent inductive annotations. [Yao et al. (ASE 2023)](https://rainoftime.github.io/files/ASE23Invariant.pdf) studies richer bit-vector invariant templates; quantified synthesis was rejected for the first release because it adds cost and complexity beyond the implication task. The [July 2026 BII preprint](https://arxiv.org/abs/2607.26386) is relevant to progressive bound refinement, but its best-inductive-invariant problem is different from ours.

[Pono 2.0 (FM 2026)](https://www.sosy-lab.org/research/pub/2026-FM.Pono_2.0_A_Versatile_SMT-Based_Model_Checker_for_Safety_and_Liveness.pdf) offers mature engines and array reasoning. Pono reads each property (see [Pono reads the property](#pono-reads-the-property)) and runs the verification experiment. The [September 2026 LLM4PDR preprint](https://arxiv.org/abs/2609.30131) suggests a future untrusted hint backend. An external LLM is unnecessary for this product; any future hints must enter the same typed validation boundary.

The detailed reading notes, page references, opportunity comparison, and counterexamples are in [constraint-literature.md](research/constraint-literature.md). The current implementation is an engineering synthesis of these ideas, with no claim of a new state-of-the-art algorithm.

## Frontend

Pono is the only BTOR2 frontend, following C14 step 3 ("use the Pono parser"): see [Pono reads the property](#pono-reads-the-property). Btor2Sieve has no BTOR2 parser or encoder of its own. It only splits lines into words (`scan` in `pono.py`) to find line IDs, keywords and symbol names: which lines are `bad`, which lines to leave out before Pono reads the file, user symbols, and the counts in reports. It never interprets an expression; every expression's meaning comes from Pono.

Pono's variables are renamed to `s_<ID>` (states) and `i_<ID>` (inputs) after their BTOR2 line IDs. Fairness and justice lines are counted and disclosed but never given to Pono as assumptions. No liveness result is produced.

**Known Pono limitation.** The pinned HWMCC'25 Pono build misreads `rol` and `ror`: it rotates by the second operand's line ID instead of its value (a variable rotate amount becomes a fixed rotate). Models with `rol` or `ror` lines are therefore refused with an error rather than analyzed under the wrong meaning, and the BTOR2 writer expresses rotates with shifts. `tests/test_pono.py` demonstrates the problem. No bundled example or sampled benchmark uses these operators.

## Exact property hypothesis

For each selected bad directive, `P_j = not bad_j` is the complete hypothesis.
The definitions of all referenced expressions are expanded in the SMT DAG.
An accepted `P_j => C` holds over all valuations satisfying that safety predicate,
including unreachable ones. Model assumptions, initialization, and transition
relations are not added. Only property scopes are exposed by extraction.

Do not insert property-derived candidates as BTOR2 `constraint` lines. For example, a wrapping counter starting at zero reaches 2 and violates `P = x < 2`. Although `P => x != 2`, assuming `x != 2` removes the first bad state. A future property-preserving transformation needs its own first-failure argument and validation. The extractor performs no such transformation.

## Model-derived candidates (defined, not implemented)

C14 step 4 also asks for the obligation for candidates derived directly from
the model rather than from a property. It is defined here; extraction does not
generate or validate such candidates, and no reported count includes them.

Notation, all as Pono reads the model:

| Symbol | Meaning |
| --- | --- |
| `A` | Conjunction of the BTOR2 `constraint` directives |
| `I` | Conjunction of the `init` equations |
| `T` | Conjunction of the `next` equations (`s' = f(s, i)`) |
| `X'` | `X` with every state and input replaced by its fresh primed symbol |

A model-derived candidate `C` is **accepted** only when both queries are UNSAT,
each in a fresh solver:

1. Initiation: `I and A and not C`, so `C` holds in every initial state that satisfies `A`.
2. Consecution: `C and A and T and A' and not C'`, so every transition between
   states that satisfy `A` preserves `C`.

Non-vacuity mirrors the check on `P`: `I and A` and `A and T and A'` must each be
SAT, or the result is vacuous. A SAT initiation or consecution query rejects `C`
and yields a counterexample; UNKNOWN establishes nothing.

Together these make `C` a 1-inductive invariant: it holds on every reachable
state of the constrained model (a model constraint in Froleyks et al., FM 2026,
§3.1, Def. 3). Unlike `P_j => C`, such a `C` may be appended as a BTOR2
`constraint` without changing any property's verdict. A true invariant
that is not inductive by itself is rejected; mutual induction over a candidate
set (Houdini) would accept more, at the cost of each obligation depending on the
final set. Missing `init` or `next` assignments leave variables unconstrained,
so they can only cause rejection, never unsound acceptance.

## Property word-level implied constraints

The default method (`--method implied`) implements the property-derived part of [C14](C14.pdf),
page 1: preserve native bit-vector and array expressions, propose word-level
constraints, and formally validate each implication before use. The selected
hypothesis is exactly `P_j = not bad_j`. Initialization, transition equations,
environment constraints, and other properties are never discovery or validation
assumptions. Inputs occurring in the property remain free variables. Each
selected bad directive has its own extraction and validation scope.

This is a native word-level adaptation of the property-constraint idea in
Cabodi et al., *Speeding up Model Checking by Exploiting Explicit and Hidden
Verification Constraints*, DATE 2009. The paper's §V-B–C defines Boolean literal
implications and optional nearby combinational nodes. The current workflow is
not a literal reproduction of that Boolean algorithm. Its seven reporting keys
represent six conceptual families, with signed and unsigned bounds separated:

| Reporting family | Native constraint form |
| --- | --- |
| `unsigned_bound` | Unsigned bit-vector lower/upper bounds |
| `signed_bound` | Signed bit-vector lower/upper bounds |
| `equality` | Equalities between compatible word expressions or constants |
| `disequality` | Disequalities between compatible word expressions or constants |
| `implication` | Guarded relations over existing property-cone predicates |
| `masked_bits` | Native masked-word equalities describing fixed bits |
| `array` | Native array equalities/disequalities and read/write relations |

`vocabulary.py` uses the subterms of P as Pono printed it, which is the
property's dependency cone. Pono writes BTOR2 comparisons and gates as one-bit
circuits (for example `eq` as `bvcomp`); these are read back as plain
predicates such as `x == y`. In the bounded profile, `select_subterms` chooses
subterms deterministically within the term and width limits. Selection does not
recursively expand the chosen subterms back into the full cone. Expressions
containing nested word or array sorts beyond the width limit are excluded from
selection. Templates can use a selected subterm's own operands. The width limit
governs source selection, not every expression in the property. The uncapped
profile uses every subterm.
The finite generation procedure is:

1. Retain numeric terms and native array expressions in that cone. Comparison
   results and Boolean wrappers serve as predicates rather than numeric words;
   one-bit declarations, reads, and slices can still be numeric terms. An empty
   root set gives an empty vocabulary.
2. Propose both polarities of native relational and one-bit leaf predicates,
   plus the four signed implication clauses for each unordered predicate pair.
   Reduction and overflow predicates may appear within implications; unsupported
   standalone Boolean shapes are not relabeled as equalities. These predicates are existing expressions, not an
   expansion into all state-bit projections.
3. For each word, propose equality, disequality, and signed/unsigned lower and
   upper bounds against every same-sort cone constant, including complemented
   constant references, plus `0`, `1`, the unsigned maximum, the sign-bit value,
   and the signed maximum. Propose equality and disequality between same-sort
   operands local to each cone node.
4. For observed read indices, propose same-address and different-address
   read-over-write implications. Array equality operands also yield read
   equalities at observed indices of matching sort. All operations remain
   native `select`, `store`, and array equality expressions.
5. With a solver containing only `P`, refine whole-word known-bit masks using
   counterexamples, then search unsigned and signed minimum/maximum endpoints.
   Signed endpoint search uses the word's sign-bit-flipped ordering. A singleton
   range yields a word equality. UNKNOWN stops semantic discovery, preserves
   the syntax proposals, and marks coverage incomplete.

Expressions retain their widths and array sorts. Candidate expressions are
normalized for deduplication, while the native formula remains available in
the record; formulas simplifying to true or false are omitted. A property that
simplifies to true yields no proposals. Family, origin, and source-node metadata
remain attached to each proposal. The property itself may yield a candidate;
acceptance counts measure checked formulas, not novelty, logical independence,
or a minimal conjunction.

Discovery uses only `P`; every resulting proposal is rechecked by the unchanged
independent validator with `P and not C`. Neither solver assumes previously
accepted candidates. Cross-property reuse repeats the target property's proof
check and has separate status counts. Unsatisfiable hypotheses cannot establish
non-vacuous accepted facts; unknown queries cannot establish acceptance.

Evaluation uses the **unlimited profile** by default: one extraction process per
benchmark, limited to 4 GiB memory, 300 s CPU and 600 s wall time, with as many
concurrent workers as memory allows; property scopes; no candidate/source-term/
width/discovery-query caps; and 1,000 ms per discovery/validation query. Reuse is
limited to 30 checks per target property. Independent Z3/cvc5 replay uses 5,000 ms
per query. Reuse is separate from extraction.

Direct extraction is uncapped by default; `--unlimited` makes that policy explicit
and records `budget_policy = "unlimited"` with null values for all four limits.
UNKNOWN stops semantic discovery and remains inconclusive. Independent validation
and replay retain their own timeout behavior.

For bounded evaluation use `--budget-policy matched`: 80 proposals, 12 selected
source nodes, 64-bit selection width, and 96 discovery queries by default. Direct
extraction enables bounds with `--matched-budgets`; its defaults are 200 proposals,
16 selected source nodes, 64-bit width, and 256 discovery queries. Candidate caps
apply to distinct nontrivial proposals, not accepted results. Discovery queries
include the initial hypothesis check; independent validation and replay are
separate. Budget exhaustion never establishes UNSAT. The bounded workflow
identifier is `property-word-level-budgeted-v1`; uncapped extraction uses
`property-word-level-v1`. Evaluation's `--budget-policy method-defaults` retains
the extractor's uncapped defaults.

Search statistics include:

- `kind`, `term_count`, `predicate_count`, and `selected_nodes` for the vocabulary;
- `total_candidates` for proposals sent to independent validation;
- `discovery_queries`, `discovery_unknown`, `hypothesis_result`, and `reason`;
- `coverage`, either `budgeted` or `finite-cone`, and `budget_exhausted` for cutoffs;
- `validation_complete`: the hypothesis and every proposal validation were
  conclusive, including requested cross-property revalidation;
- `complete`: execution of the configured search finished with conclusive checks.

A completed **budgeted** search does not claim full dependency-cone coverage.
Even an uncapped finite-cone search does not enumerate all possible word-level
consequences. UNKNOWN leaves the run partial and yields exit code 1, retaining
completed checks and accepted evidence. Rejection and vacuity are resolved
outcomes. Counts alone do not measure logical strength, novelty, or downstream
model-checking speedup. Extraction can propose the property itself, and formulas
simplifying to true or false are omitted before validation.
Records expose `syntactically_same_as_hypothesis`. Accepted totals are validated
proposal counts, not counts of independent or equally informative constraints.

## Historical Boolean workflow

The earlier implementation is preserved in
`archive/boolean-implications-method-2026-11-10.tar.gz`.
It used all state-bit projections plus eligible state-only Boolean combinational
nodes and tested signed unit/binary clauses. SAT witnesses pruned false clauses
in batches, while proved units represented redundant implications. Its reports
used atom counts, a logical clause pool, unit redundancy, a validated basis,
equivalences, and discovery-witness artifacts. Existing reports keep their original
interpretation; to re-render one, use the archived snapshot.

The historical 225-model HWMCC run in
`results/hwmcc-expanded-implied/evaluation.json` recorded 624,400 accepted Boolean
basis formulas. Those counts do not measure the native `property-word-level-v1`
workflow. Old artifacts remain unchanged; a new native benchmark run needs a
fresh output directory and its own measurements. No full-corpus native results
are implied by this implementation change.

The paper's separate exploitation theorem (§V-B, Theorem 1) assumes `P => C`
and `I => P`, and constrains source transitions using `T_C = C(current) and T`,
retaining the original property. Extraction does not check that initiation
premise, rewrite circuits, merge conditional equivalents globally, or measure
model-checking speedup. Adding property consequences as global constraints or
requiring them of the next state can hide the first bad state.

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

The trusted computing base is Pono's BTOR2 frontend and the SMT backend. Cross-solver agreement reduces solver-specific risk but does not validate the frontend. SMT obligations are not proof certificates checked by a small proof kernel. Source provenance and frontend semantic tests address a different part of this trust boundary.

## Pono reads the property

The validator's hypothesis P comes from Pono, an external model checker with its own BTOR2 parser and SMT stack. For each model, Btor2Sieve writes a copy without its `init`, `constraint`, `fair`, and `justice` lines, so that only the property itself is assumed, as everywhere else in this method. It runs `pono -e bmc -k 0 -p <index> --printing-smt-solver --logging-smt-solver` on that copy, where `<index>` is the property's position among the `bad` lines. Pono prints every SMT query to standard error. The first assertion after the first `(push 1)` is "the selected bad holds at step 0", so P is its negation. Pono names variables `state<ID>@0` and `input<ID>@0` after the BTOR2 line IDs; they are renamed to `s_<ID>` and `i_<ID>`, and the sort of each must match. Any other free symbol, a missing assertion, or a timeout (`--pono-timeout`, default 300 s) is an error for that model. Btor2Sieve stops Pono as soon as the assertion has been read; Pono's verdict is not used.

Candidate discovery and validation both use Pono's P, and candidates are built from P's subterms, so every expression's meaning comes from Pono. Before the earlier builtin parser was removed, Pono's P and the builtin parser's P were checked to be logically equivalent for every property of the examples and of a 42-model, 216-property benchmark sample.

Every model is read by Pono even when it has no `bad` line, so a file Pono cannot parse is always an error. Each report records `frontend` with the Pono binary's path and SHA-256 (because `pono --version` prints only a build number). `shell.nix` pins the official prebuilt HWMCC'25 Pono binary. `scripts/split_properties.py` and `scripts/convert_legacy_btor2.py` also have Pono read every file they write.

## Verification experiment

`btor2sieve verify` checks each property with each selected Pono engine twice. The first run uses the original model with only that `bad` line; other `bad`, `fair`, and `justice` lines are removed, and `init`, `next`, and environment `constraint` lines are kept. The second run adds `constraint (b or C)` for every accepted C, where `b` is the bad term; that is, P implies C. Because P implies C is valid, the added constraints remove no state, and the verdicts must match; a mismatch between definite verdicts is reported as inconsistent.

To write C into BTOR2, its recorded expression is parsed back into Z3 over `s_<ID>` and `i_<ID>` (with the sorts Pono gives those variables). `s_<ID>` and `i_<ID>` become references to line `<ID>`; every operator gets a new line, numbered after the model's largest ID. Tests have Pono read the written lines back and prove, with Z3, that they denote the original formula.

The measurement is the change in wall time, which includes Pono's parsing, and in the number of solved properties. It does not show a speedup by itself, and a single run is not a robust timing estimate. Pono's `-k` bound applies to every engine, so the default bound is 1000 rather than Pono's default of 10.

## Cross-property reuse

An accepted candidate from property j is merely a proposal for property k. Reuse repeats `P_k and not C` in the target validator. Rejected reuse is retained. Reuse counts and timings are separate records and do not inflate ordinary candidate counts. A per-target reuse limit prevents an unbounded quadratic property comparison.

## Resource and reporting policy

Solver timeouts apply per query. They are not a process-wide timeout or memory limit. Parsing, encoding, formatting and report writing also take time. Large models and complex arrays can exceed practical memory or latency budgets. Evaluation records the exact local input list and hashes; results apply to that selected corpus.

Evaluation also limits each benchmark's extraction process: 4 GiB resident plus
swapped memory, 300 s CPU time and 600 s wall time by default. The limits are
enforced from outside the process. A benchmark that exceeds one is stopped and
reported as `memory-limit`, `cpu-limit` or `wall-limit` with its measured usage.
It contributes no accepted facts, because its partial evidence has no report and
is deleted. These outcomes describe resource exhaustion. Direct CLI extraction
has no process-wide limits.

Each model commits its records and summaries atomically to the run report. A malformed input or failed candidate aborts that model, records an error and removes its partial obligations; batch processing continues with other models and exits nonzero. Existing output directories are never overwritten. HTML is escaped, static, searchable, and usable directly from disk.
