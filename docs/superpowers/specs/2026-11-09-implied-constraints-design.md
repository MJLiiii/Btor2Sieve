# Paper implied-constraint extraction

Implement the implied-constraint family from Cabodi et al., *Speeding up
Model Checking by Exploiting Explicit and Hidden Verification Constraints*,
DATE 2009, §V-B–C (PDF page 4 / proceedings page 1689), alongside the existing
word-level method. Preserve the existing method and its default CLI behavior.

## Approach

The paper enumerates implications between Boolean state literals and checks
`P ∧ li ∧ ¬lj`; UNSAT establishes `P ⇒ (li ⇒ lj)`. Mutual implications
identify equivalence. Use state bits, including both polarities, as the
BTOR2 adaptation. Optional nearby combinational nodes and circuit merging
are outside this extraction-only change. The paper leaves enumeration and
resource policies unspecified; the choices below are implementation choices.

Alternatives considered: mixing literal candidates into the existing pool
would prevent a clean comparison; circuit rewriting would require separate
first-failure verification. A separate generator feeding the current
independent validator meets the request with the smallest sound boundary.

## Interface and semantics

- Append `method="word-level"` to GenerationOptions; CLI accepts
  `--method word-level|implied`. Existing calls retain current behavior.
- Implied mode analyzes property scopes only, always with `P=¬bad` and no
  initialization, transition or environment assumptions. Its default scope
  is `property`; incompatible scopes and `--syntax-only` are rejected.
- Select Boolean bits deterministically across eligible state words,
  prioritizing states in the property cone. `max_terms` bounds selected bits,
  `max_width` bounds eligible word widths, `max_candidates` bounds implication
  proposals, and `timeout_ms` bounds each independent validation query.
  There is no discovery solver, so `max_queries` is unused for this method.
- Generate unary opposite-polarity implications and binary implications of
  both polarities. Remove tautologies and contrapositive duplicates.
- Record proved same/complemented equivalences with links to the two accepted
  implication records. They do not inflate candidate counts or consume extra
  solver calls. Keep report schema version and existing CSV columns stable.
- Array states are not Boolean literal candidates. Disclose skipped arrays,
  word-width filtering, and the bounded state-bit vocabulary in reports.
- Do not rewrite models or insert extracted facts as BTOR2 constraints.
  The paper's transition restriction requires its own theorem premises;
  extraction alone establishes neither reachability nor model-checking speedup.

## Benchmark experience

`scripts/evaluate.py` defaults to `--methods semantic implied`, comparing
existing semantic word-level extraction against the paper method on the same
property scopes and inputs. `--methods syntax semantic` retains the prior
ablation. Support method selection, path filtering and a model limit for
quick trials; preserve recursive discovery and non-overwriting outputs.
Write per-method evidence plus a combined comparison CSV. Record failed
extractions and replay failures without losing the other method's results;
return nonzero if any run fails.

## Validation

Start from the existing 143 passing tests. Test literal polarity, unit facts,
equivalences, array/width/term/candidate bounds, no assumptions or reachable
state filtering, vacuity and UNKNOWN, CLI dispatch/replay and evaluator
selection/failures. Compare default word-level records with explicit method
selection. Run representative BV and array benchmark smoke tests with both
Z3 and cvc5 replay, then obtain an independent code review.
