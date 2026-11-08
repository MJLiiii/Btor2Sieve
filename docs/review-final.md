# Independent final review

Reviewed 2026-11-08 against `C14.pdf`, the approved design, and `docs/METHODS.md`. All production modules under `src/btor2sieve/`, the packaging configuration, evaluation/fetch scripts, relevant tests, and final evaluation artifacts were inspected. No production code was edited by this reviewer.

## Verdict

**Spec compliance: the core C14 deliverable is met in the reviewed implementation and small-corpus evidence.** The frontend preserves word and array sorts; generation covers the requested candidate families; validation checks each exact scoped implication independently; reports distinguish accepted, rejected, unknown, and vacuous results. Property scope does not silently assume the environment. Initial and transition consequences have explicit, limited meanings. Reuse is independently revalidated. Per-model/per-property tables and replayable SMT artifacts are present.

**Code quality: suitable for this bounded research prototype, with no outstanding findings after the scoped repair below.** Responsibilities are separated into compact modules, the parser rejects malformed typed expressions, candidate discovery is kept outside the validation trust boundary, model publication is transactional, and replay checks both hashes and hypothesis satisfiability. No P0/P1/P2 correctness finding was identified in this review. This is a review verdict, not a proof of frontend or solver correctness.

The HWMCC-derived examples are single-property; multiple-property coverage comes from explicitly labeled upstream regression examples. This exercises the requested functionality but does not establish performance on a representative multi-property competition corpus. Pono integration and verification speedup are optional in C14 and remain unclaimed.

## Resolved P3: Validator rejected valid formulas from an explicit Z3 context

Location: `src/btor2sieve/validation.py`, `_solver` and its calls in `Validator.__init__` and `Validator.check` (lines 60–61, 84–85, and 95–96 at review).

The initial reviewed validator accepted a `BoolRef` but created every solver in the default context. A valid hypothesis created in an explicit context failed before validation:

```python
import z3
from btor2sieve.validation import Validator

ctx = z3.Context()
x = z3.BitVec("x", 4, ctx=ctx)
Validator(x == 3).check(x != 0)
# Before repair: Z3Exception: Value cannot be converted into a Z3 Boolean value
```

This affected direct API consumers using separate contexts, for example to isolate independent solver work. The encoder and CLI use the default context, so existing extraction and replay results were unaffected. The recommended repair was to allow `_solver` to receive a context and construct both validator solvers with `hypothesis.ctx`. The main implementer applied that repair and added `test_validator_accepts_formulas_from_an_explicit_z3_context`. This reviewer inspected the change and independently reran the reproducer with both a valid and invalid consequence; it now returns accepted and rejected respectively. Cross-context operands still fail through Z3 rather than being silently mixed. This finding is closed.

## Independent checks performed

- Tested 199 semantic candidates generated from small finite word domains with query budgets deliberately ending during bound and bit discovery. Each `H and not C` was independently UNSAT. This specifically probes the weaker-bound behavior after incomplete binary searches.
- Compared 3,060 small-width overflow and rotation evaluations against concrete Python integer calculations over all input pairs at widths 1–4. No mismatch occurred.
- Inspected full-cone selection: traversal reaches dependencies beneath deep Boolean structure, prioritizes word anchors while reserving slots for atoms/intermediate words/literals, and caps selected vocabulary. Reviewed the existing deep-cone and guarded-implication regressions rather than rerunning the full suite.
- Checked `results/final-evaluation` JSON consistency: syntax has 1,912 ordinary records, semantic has 1,914, each with 36 scope summaries. Candidate and accepted totals match summaries. Recorded replay check totals equal all accepted records, including reuse, plus all scope hypotheses, and the stored Z3/cvc5 replay receipts have zero mismatches. These are artifact-consistency checks; this reviewer did not rerun the entire evaluation.
- Inspected the final cvc5 `arrays-exp` change and independently replayed a nested constant-array SAT hypothesis and its UNSAT read implication with both Z3 and cvc5. All four checks passed. Solver metadata records the array option.
- Confirmed the earlier core-review issues are repaired structurally: hypotheses now have hashes and are replayed, while a failing model discards its staged records/summaries and partial obligations. Relevant regression tests are present.

## Scope limitations

The full test suite and full benchmark evaluation were being run by the main implementer and were deliberately not duplicated. This review does not certify all legal BTOR2 inputs, all solver/package versions allowed by the dependency ranges, large-model resource behavior, liveness semantics, or speedup in a model checker. Replay depends on the parser/encoder and SMT backends; it is not a kernel-checked proof certificate. Query timeouts and finite candidate budgets do not impose a whole-process time or memory limit. The reviewed reporting and methods documentation state those boundaries.
