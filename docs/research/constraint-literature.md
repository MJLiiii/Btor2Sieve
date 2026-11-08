# Constraint extraction: literature and soundness notes

Research date: 2026-11-08. Primary papers and standards were read directly; page numbers below refer to the linked PDF unless a proceedings page is also stated. This note separates literature findings from proposed Btor2Sieve design decisions. It does not claim that a constraint miner or transformed model has been verified.

## Main decision

For the requested first version, extract **property consequences** and validate every candidate `C` using a fresh query for `P ∧ ¬C`, where `P = ¬bad` for the selected property. `UNSAT` establishes only `P ⇒ C`. It does **not** establish that `C` holds on every reachable state, and does not authorize adding `C` as a Btor2 `constraint`.

Keep structural identities, initial facts, transition facts, reachable invariants, and property consequences as different result kinds. A formula can have several independently established kinds. An extractor that reports these distinctions and exports replayable obligations is more useful than one that emits untyped “invariants.”

## Primary-source findings

### Cabodi et al., DATE 2009

[Official proceedings PDF](https://past.date-conference.com/proceedings-archive/2009/DATE09/PDFFILES/12.6_3.PDF), *Speeding up Model Checking by Exploiting Explicit and Hidden Verification Constraints*, pp. 1686–1691, DOI `10.1109/DATE.2009.5090934`.

- §V-A, PDF p. 4 / proceedings p. 1689: find a transition-closed region implying safety; remove that safe region from the verification task. Initiation is not required for that region.
- §V-B, same page, Eq. (7) and Theorem 1: find `P ⇒ C`; constrain **source transitions**, while preserving the original property. The theorem states `I ⇒ P` as a premise. The circuit alternative uses `ite(C, next, current)`.
- §V-C, same page: test literal implications and equivalences with SAT, focusing on state variables and nearby combinational nodes to bound cost. Two opposite implications permit merging nodes in the appropriately constrained circuit. Reachability simulation is not their preliminary filter because the obligations do not start from initial states.
- §VI, PDF pp. 5–6: evaluation uses PdTrav and Boolean circuits; reported speedups do not establish a word-level Btor2 result.

The useful transfer is candidate generation followed by exact semantic checks, with reintegration tied to the constraint’s meaning.

### Froleyks, Yu, Biere, Heljanko, FM 2026

[Publisher paper and full text](https://link.springer.com/chapter/10.1007/978-3-032-26204-2_9), [PDF](https://link.springer.com/content/pdf/10.1007/978-3-032-26204-2_9.pdf), *Certifying Constraints in Hardware Model Checking*, pp. 170–188.

- §3.1, Definition 3 (p. 175): model constraints hold on all reachable states. Their certificates can be composed with the certificate obtained after constraining the model.
- §3.2, Definition 4 (pp. 176–177): an “inductive constraint” `D` has a transition-closed **complement** that implies `P`. Neither `D` nor its complement is automatically an initialized invariant. The naming is explicitly cautioned about.
- §3.3, Definition 5 and Theorem 3 (pp. 177–178): property constraints satisfy `P ⇒ D`; they gate transitions as `ite(D, f_l, l)`. They are not appended like model constraints.
- §2, Definition 2 (pp. 173–175) and §6 (pp. 183–184): independently checkable witness circuits concern the original model; the implementation is AIGER/SAT/QBF, not a ready-made QF_ABV extractor or word-level proof format.

For Btor2Sieve, an SMT implication receipt is evidence of extraction correctness; it is not a full certificate of a transformed model-checking pipeline.

### Flanagan and Leino, Houdini, FME 2001

[Paper PDF](https://fastpl.doc.ic.ac.uk/SoftwareReliability/2016-2017/papers/Houdini.pdf), *Houdini, an Annotation Assistant for ESC/Java*, pp. 500–517, DOI `10.1007/3-540-45251-6_29`.

§3 (PDF pp. 3–5 / proceedings pp. 502–504) generates a finite candidate set, checks annotations, removes refuted candidates, and repeats because removing one assumption can invalidate others. The final set is maximal relative to the candidate set and checker. §4 (pp. 504–505) uses cheap templates such as comparisons to fields and interesting constants. §2 (p. 502) explicitly notes that ESC/Java itself has intentional unsoundness; reuse the algorithmic idea, not that historical implementation as a proof authority.

A property-consequence miner has a simpler obligation than invariant Houdini: its antecedent `P` is fixed. Candidates must not justify one another by being silently asserted. A SAT assignment satisfying `P` can refute every candidate false in that assignment; every surviving candidate still needs a definitive UNSAT check.

### Yao et al., ASE 2023

[Author PDF](https://rainoftime.github.io/files/ASE23Invariant.pdf), [publisher record](https://ieeexplore.ieee.org/document/10298567), *Demystifying Template-Based Invariant Generation for Bit-Vector Programs*, DOI `10.1109/ASE56229.2023.00069`.

§II-B (PDF p. 3) encodes template parameters with initiation, consecution, and postcondition constraints. §IV-A (pp. 5–6) compares interval, zone, octagon, and bounded-polyhedron templates, plus bounded disjunction and property strengthening. §III (pp. 3–5) motivates exact bit-vector semantics and discusses quantified-solver costs. §V (pp. 7–11) shows sensitivity to template and solver choice; its experiments are not evidence that the richest template is universally best. Arrays are discussed as an extension in §V-C, not a completed array-mining result.

This supports exact BV templates as a research extension. An existential–universal synthesis engine is a substantially larger first implementation than enumerating a bounded set of candidate formulas and checking QF_ABV obligations.

### Zuo, Yao, Ren, July 2026 preprint

[Author preprint](https://arxiv.org/abs/2607.26386), [full text](https://arxiv.org/html/2607.26386v1), *A Fresh Look at Best Inductive Loop Invariant Synthesis for Bit-Vector Relations*, arXiv:2607.26386v1. This is cited as a preprint, not an established conference result.

§§3–5 formulate best inductive invariants in a fixed abstract domain as quantified optimization and provide lattice and bitwise refinement algorithms. The top-down sequence maintains sound intermediate invariants. §6 instantiates interval, octagon, and sparse-polyhedron templates; §6.4 studies supplying partial and optimal invariants to k-induction. These are initialized inductive invariants, not merely consequences of a safety predicate.

Possible later work is progressively tightening bounds while preserving certified obligations and returning partial results under a budget. The paper’s quantified invariant problem should not be conflated with the much simpler fixed-antecedent implication problem.

### Perez-Lopez et al., Pono 2.0, FM 2026

[Author PDF](https://www.sosy-lab.org/research/pub/2026-FM.Pono_2.0_A_Versatile_SMT-Based_Model_Checker_for_Safety_and_Liveness.pdf), [publisher record](https://link.springer.com/chapter/10.1007/978-3-032-26220-2_1), *Pono 2.0: A Versatile SMT-Based Model Checker for Safety and Liveness*.

§4.2 (PDF p. 8) extends IC3SA to arrays with BV indices and values. §4.4 (p. 10) explains array abstraction, history/prophecy refinement, and incompleteness of its finite-index CEGP implementation. §4.5 (pp. 10–11) distinguishes violation witnesses from correctness witnesses: invariants are available through `Prover::invar()` and optional internal inductiveness checking, but witness-circuit correctness export is not supported by that version.

Pono is a useful downstream baseline and optional source of independently rechecked invariant candidates. Its machinery is much larger than a property-consequence preprocessor. Do not describe an internal invariant check as an independent external certificate.

## Proposed semantic contract

### Additional recent lead: LLM4PDR (preprint)

[Hu et al., arXiv:2609.30131v1](https://arxiv.org/abs/2609.30131), [full text](https://arxiv.org/html/2609.30131v1), *Enhancing Word-Level Property Directed Reachability with LLM-Driven Semantic Guidance*, submitted 24 September 2026. The abstract, introduction, and §IV organization distinguish predicate generation, candidate frame clauses, and helper assertions. Generated hints are untrusted and pass verifier-side parsing, typing, and proof checks. The system is implemented in Pono; reported gains are benchmark- and mode-dependent. This is a preprint, separately from the published FM2026 and ASE2023 sources above.

For Btor2Sieve, an optional future LLM backend could propose formulas in a restricted typed grammar and feed the same scope-aware validator. A plausible invariant proposed by an LLM need not follow from `P`; reject it in property scope unless that exact implication succeeds. A different invariant scope would need initiation and consecution checks. No external LLM is necessary for the initial implementation.

The following is project design analysis, written in a uniform notation rather than copied from any paper. Let `s` be state variables, `u` current inputs, `s'` next state, `u'` independently chosen next inputs, `I` initialization, `T` the transition relation, and `E` the conjunction of original environment constraints. Expressions denote their complete definitions; internal node names must not become unconstrained fresh symbols.

| Result kind | Required evidence | Allowed conclusion |
|---|---|---|
| Structural/theory fact `C` | `¬C` is UNSAT after exact definition expansion, or `Def ∧ ¬C` is UNSAT | Holds in every valuation of the represented expression graph; no property or reachability premise |
| Environment consequence | `E ∧ ¬C` is UNSAT | Redundant under the original environment; report that premise |
| Initial fact | `I ∧ E ∧ ¬C` is UNSAT | Holds at time zero only |
| Transition fact `D(s,u,s',u')` | `E ∧ T ∧ E' ∧ ¬D` is UNSAT | Holds on legal edges only; cannot generally be emitted as a one-state constraint |
| Property consequence | **`P ∧ ¬C` is UNSAT** | Holds whenever the selected property holds, including unreachable valuations |
| Environment-relative property consequence | `E ∧ P ∧ ¬C` is UNSAT | Weaker claim than the preceding row; not acceptable as an unconditional `P ⇒ C` result |
| Initialized inductive invariant `J` | `I ∧ E ∧ ¬J` and `J ∧ E ∧ T ∧ E' ∧ ¬J'` are UNSAT | Holds on all legal reachable frames |
| Reachable/model fact `C` | Independently proved reachability, or an initialized inductive `J` plus `J ∧ E ∧ ¬C` UNSAT | May restrict legal frames without removing reachable behavior |
| Safe-region exclusion `D` | `¬D ∧ E ∧ T ∧ E' ∧ D'` and `¬D ∧ E ∧ ¬P` are UNSAT | Leaving `D` enters a closed safe region; restriction to `D` preserves bad traces |

For invariants containing inputs, the primed input variables above are fresh and constrained only by the original next-frame environment. Accidentally reusing `u` as `u'` assumes stable inputs. A state-only invariant interface is simpler initially.

`I`, `T`, or already accepted candidates must not be added to the fixed-antecedent property check: doing so proves a different statement. Definitions are semantic encoding, not extra behavioral assumptions. If there are multiple bad predicates, store whether `P` means one selected `¬bad_i` or the aggregate `∧_i ¬bad_i`; consequences of the aggregate need not follow from each individual property.

## Feasible candidate families

These are proposed templates, not a claim that every generated formula holds. All constants must carry a width and all comparisons an explicit signedness. Use property-cone distance, fanout, and potential rewrite savings to prioritize candidates; cap candidate count and pair generation deterministically.

| Priority | Family | Examples and generation bounds |
|---|---|---|
| 1 | Existing Boolean atoms | Property conjuncts; positive/negative existing comparison atoms; guards from nearby `ite` nodes; test implications between a bounded local set |
| 1 | Same-sort equality and disequality | `x = y`, `x ≠ y`, `x = k`, `select(A,i) = v`; prefer operands occurring together in the property or a comparison/conditional |
| 1 | Unsigned/signed bounds | `x ≤u k`, `x <u k`, `x ≤s k`; constants from the model, zero, one, all-ones, sign boundary, and width-valid adjacent values |
| 1 | Bit masks and slices | `(x & mask) = value`, `extract(x,h,l) = k`, high bits zero/one; use masks and slice boundaries already present rather than enumerating every mask |
| 2 | Guarded relations | `g ⇒ x=y`, `g ⇒ x≤u k`, mutual exclusion `¬(g∧h)`; allows facts that hold only in a mode |
| 2 | Modular arithmetic relations | `x = y+k`, `x-y = k`, `x+y = k`, low-bit alignment; same-width modular semantics, bounded constants and local pairs |
| 2 | Read/write-local array relations | `i=j ⇒ select(A,i)=select(A,j)`; `select(store(A,i,v),i)=v`; `i≠j ⇒ select(store(A,i,v),j)=select(A,j)`; index relationships and read values from existing terms |
| 3 | Array equalities | `A=B`, `store(A,i,v)=A`; use native array equality, exact sorts, and strict budgets |
| Later | Parametric bound synthesis | Binary-search the strongest unsigned upper bound under `P`; separate signed order; then consider richer quantified templates or invariant Houdini |

Array read-over-write and extensionality semantics come from the [SMT-LIB ArraysEx theory](https://smt-lib.org/theories-ArraysEx.shtml). Some candidates in this table are theory identities; classify and suppress them from “nontrivial extracted constraints,” while retaining them as rewrite facts if useful. Several observed read equalities do not establish whole-array equality. Do not invent a quantified all-index invariant from a finite sample of indices.

The [SMT-LIB fixed-size BV theory](https://smt-lib.org/theories-FixedSizeBitVectors.shtml) is the semantic reference for bit widths, modular arithmetic, extraction, shifts, and totalized division. Mathematical-integer reasoning is insufficient. For example, unsigned `x+1 > x` fails at all-ones; this is a counterexample to an otherwise tempting range template.

## Two distinct filtering algorithms

**Property-consequence mining.** Assert only the original expanded `P` in a discovery solver. For candidate `c`, ask for `P ∧ ¬c`. A SAT assignment refutes `c` and can cheaply refute other candidates false under that same assignment. Accept only definite UNSAT, and replay accepted candidates in a separate validation process. `UNKNOWN`, timeout, malformed output, or a crashed process yields no accepted claim. A vacuously false `P` implies everything: report `P` satisfiability and avoid advertising this as useful mining.

**Invariant Houdini.** With candidate pool `S`, first remove candidates refuted by legal initial states. Let `H=∧S`. Ask for `H ∧ E ∧ T ∧ E' ∧ ¬H'`; a model identifies successor-false candidates to remove. Repeat, because the antecedent changes when candidates are removed. Termination with both base and step UNSAT proves the final conjunction; each member need not be independently inductive. This is a separate optional engine and requires transition semantics.

Reachable-state simulation can prioritize or refute proposed model invariants, but cannot establish them. For property consequences, a sample is a valid refutation only when it satisfies `P` and violates the candidate. Restricting sampling to reachable states can miss many invalid consequences because the requested implication quantifies over unreachable valuations too.

## Reintegration pitfalls and small counterexamples

1. **Appending a property consequence can hide a bug.** Take a two-bit counter initialized at zero with `x'=x+1`, `P=(x<2)`, and `C=(x≠2)`. `P ⇒ C` is valid. Appending `C` as an environment constraint removes reachable state 2, the first bad state; it also prevents reaching 3. The restricted model appears safe. Gating source transitions by `C` retains the transition `1→2` and the failure.
2. **An initial fact is not invariant.** With `x=0` initially and `x'=x+1`, `x=0` is an initial fact and immediately ceases to hold. Checking `I ∧ P ∧ ¬C` instead of `P ∧ ¬C` can accept it for the wrong reason.
3. **Transition identities are not present-state facts.** `x'=y+1` may hold on every edge while `x=y+1` is false now. Priming must be explicit in metadata and exported formulas.
4. **Conditional equivalences are not global substitutions.** `P ⇒ x=y` justifies substitutions only inside a care region and a transformation with a proven first-failure argument. Rewriting `P` itself, initialization, or all uses of `x` globally can change failures.
5. **Circular assumptions produce vacuous “proofs.”** Testing `P ∧ c ∧ ¬c` proves nothing about `P ⇒ c`. Also, using unproved properties as constraints while proving each other requires a simultaneous initiation/consecution argument.
6. **The terminal BMC frame matters.** A source-gated encoding may assert `C` on transition source frames `0..k-1`, but must not blindly assert it on the final bad frame `k`. Always test zero-step failures.
7. **Array samples are partial.** Equal reads at existing indices need not mean equal arrays. A native solver can witness a differing index; sample-based reconstruction must not erase that possibility.

For a functional transition system, a simple safety-preserving transformation is `next_C(s,u)=ite(C(s,u),next(s,u),s)`, with unchanged initialization, environment, and bad predicate. Before the first failure, `P` holds and hence `C` holds, so the original prefix is unchanged. Any newly inserted stutter is entered from `¬C`, which already entails `¬P`. For relational/partial transition systems, export the precise relation and preserve nondeterminism rather than assuming that every state has a deterministic update.

The first version should emit validated facts and optional suggestions, not silently modify `constraint` lines. Actual rewriting additionally requires equivalence tests, counterexample preservation checks, and certificate handling for the original model.

## Validation receipts and evaluation

Suggested receipt fields: input SHA-256; parser/semantic version; selected bad ID(s); candidate expression with original node provenance, sort, and signedness; result kind; exact premise; exact SMT-LIB obligation; solver name/version/options/seed; status and elapsed time; checker identity; and artifact hash. A second process avoids leaked solver assertions; a second solver reduces solver-specific trust, although a shared parser remains a common trusted component. State clearly whether validation is replay, cross-solver confirmation, or proof checking.

Measure accepted nontrivial constraints by family, rejected/SAT candidates, unknown/timeouts, discovery plus validation cost, and downstream solving time including preprocessing. Include satisfiable and unsatisfiable properties, zero-step failures, signed/unsigned boundaries, wraparound, original constraints, multiple bads, arrays, missing initialization, and cross-candidate contamination. Compare candidates from syntax only, local pair templates, guarded templates, and optional invariant/Houdini engines separately. Do not count `true`, `P` itself, duplicated formulas, or theory tautologies as mining success.

| Approach | Best use here | Cost or limit |
|---|---|---|
| Syntactic conjunct/atom extraction | First baseline with tiny implementation cost | Misses non-syntactic implications |
| Local template enumeration + exact QF_ABV checks | Recommended first implementation | Candidate explosion requires deterministic caps |
| Counterexample batch filtering | Cheaply removes many invalid candidates per model | Does not replace final UNSAT validation |
| BV bound optimization | Stronger range facts without enumerating every constant | One or more solver calls per bound bit; may add no rewrite value |
| Invariant Houdini | Separately certified reachable facts usable as constraints | Needs correct initial/transition encoding and mutually inductive set handling |
| Quantified template synthesis | More expressive arithmetic invariants | Larger trust/cost surface; solver and domain sensitivity |
| IC3/PDR/CEGAR integration | Downstream verification and difficult arrays | Substantially broader than the extractor; certificate composition remains work |
| LLM-generated typed hints | Optional richer candidate vocabulary for the same validator | Nondeterministic cost and quality; no acceptance without the exact scope obligation |

## Independent review of the 2026-11-08 design

Reviewed `docs/superpowers/specs/2026-11-08-btor2sieve-design.md`. The proposed scopes `P_j`, `A`, `I∧A`, and `T∧A`, combined with fresh validation and no assumption injection, have sound stated implication contracts.

- Display `model: H=A` as an assumption/combinational consequence. This is narrower terminology than the FM2026 reachable-state definition of a model constraint.
- `T∧A` covers edges whose source satisfies the environment; it does not require `A'`. Proving a consequence of this broader relation is sound, but describe that exact premise in output.
- If transition generation considers only current-state terms, a total functional `T` adds no useful restrictions on them beyond `A`. Include primed state terms and current/next relations for useful transition extraction, or report this limitation.
- Opportunity order: bounded syntax/templates first; solver-guided symbolic bounds and known bits next; invariant Houdini as a separate scope; IC3/PDR integration and optional LLM proposals later. Keep published results, the July 2026 BII preprint, and the September 2026 LLM4PDR preprint distinct in comparisons.
