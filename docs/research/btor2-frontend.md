# BTOR2 frontend: sources, semantics, and a small public corpus

Historical note: the starter corpus described below was replaced on 2026-11-09 by the user-supplied HWMCC’25 files. See [the current corpus](../../benchmarks/README.md). Prior corpus validation results below do not apply to the replacement.

Verified 2026-11-08. This note records implementation decisions for Btor2Sieve; it does not establish correctness of a completed implementation.

## Primary references and version pins

- Niemetz, Preiner, Wolf, Biere, **BTOR2, BtorMC and Boolector 3.0**, CAV 2018, [author PDF](https://cs.stanford.edu/~preiner/publications/2018/NiemetzPreinerWolfBiere-CAV18.pdf), [DOI](https://doi.org/10.1007/978-3-319-96145-3_32). The sequential and witness semantics are on pages 2–4.
- [Official Btor2Tools](https://github.com/hwmcc/btor2tools), inspected commit `e6941e37e056084ab6e51c5c1eee6233089a330d`: [format README](https://github.com/hwmcc/btor2tools/blob/e6941e37e056084ab6e51c5c1eee6233089a330d/README.md), [C parser](https://github.com/hwmcc/btor2tools/blob/e6941e37e056084ab6e51c5c1eee6233089a330d/src/btor2parser/btor2parser.c), [header](https://github.com/hwmcc/btor2tools/blob/e6941e37e056084ab6e51c5c1eee6233089a330d/src/btor2parser/btor2parser.h). MIT licensed.
- Mann et al., **Pono: A Flexible and Extensible SMT-Based Model Checker**, CAV 2021, [author PDF](https://theory.stanford.edu/~barrett/pubs/MIL+21.pdf), [DOI](https://doi.org/10.1007/978-3-030-81688-9_22). Pono uses a C++ transition-system abstraction over Smt-Switch. This is the baseline paper, rather than a description of every current feature.
- [Pono BTOR2 encoder](https://github.com/stanford-centaur/pono/blob/b0aa8fe43b4449d5ad62abb0f700e04dbbaa8fce/frontends/btor2_encoder.cpp), inspected commit `b0aa8fe43b4449d5ad62abb0f700e04dbbaa8fce`, BSD-3-Clause. Useful independent operational reference for casts, arrays, signed references, overflow, and rotates.
- [SMT-LIB fixed-size bit-vectors](https://smt-lib.org/theories-FixedSizeBitVectors.shtml), [QF_BV additional operations](https://smt-lib.org/logics-all.shtml#QF_BV), [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html).

## Architecture recommendation

Use a self-contained, typed, line-based Python frontend and an iterative Z3 translation for this small extractor. Keep parsing, structural validation, and SMT encoding separate. A grammar library is unnecessary for fixed operator arities; a dictionary of operator signatures is useful. Preserve line number, original numeric ID, symbol, sort, operand IDs, and immediate parameters in the IR. Build solver symbols from unique numeric IDs, never from optional user symbols. Sort equality is structural: distinct sort IDs may denote the same width or array shape.

The official C parser is a good optional differential oracle (`catbtor`), but using it through ctypes adds a native-library ABI and installation dependency while still leaving all SMT encoding work. A full Pono/Smt-Switch binding is substantially more machinery than this extractor needs. These are project-specific judgments, not claims that Python is inherently better. Treat the new frontend as trusted code and test it against upstream artifacts and independently evaluated small-width operations.

## Required semantic contract

1. A `bad b` directive represents an undesirable condition. Its safety property is `not b`; multiple `bad` directives are separate properties, numbered in encounter order for witness purposes. Preserve each node ID and optional name.
2. `constraint c` is a global assumption and may depend on current inputs. It must be applied at each relevant frame in a trace encoding. Do not silently strengthen a property-only extraction hypothesis with it.
3. Missing `init` means unrestricted initial value. Missing `next` means a state behaves like a primary input, taking a fresh unrestricted value at each step; it does **not** mean that the value is held constant. An explicit `next s s` does hold the value constant. An initialization on a state with no next still restricts frame zero.
4. An `init` equation constrains only the initial state. Initialization may depend on earlier state variables, enabling partial initialization, but not on any `input` in its transitive operand graph. The initialization expression must be declared before its target state. Reject self-initialization explicitly: the inspected C parser has an equality boundary that reaches an assertion in `check_state_init`, so acceptance by a release build is not an intended semantics guarantee.
5. An array `init` RHS can be an array of the same sort or a literal BV constant of the element sort (`const`, `constd`, `consth`, `zero`, `one`, `ones`). The latter means the constant array, implemented by `K(index_sort, value)`. An arbitrary scalar expression is not this special case.
6. Negative operand IDs denote bitwise complement of the referenced BV, including width-one BVs. They are not arithmetic negation. Negative array references and negated state targets of init/next are invalid. IDs defining lines and sorts are positive.
7. Arrays support read, write, equality/disequality, state/input, and conditional selection. Array-valued `ite` occurs in upstream Yosys/Pono files even though the abbreviated README table shows only the BV signature. Array sorts can be nested; either implement recursively or reject unsupported shapes explicitly.
8. `fair` and `justice` have infinite-path semantics, not Boolean assumptions for ordinary safety extraction. A safety-only first version should reject such inputs with a precise unsupported-feature error, or expose a clearly separate inspection-only path. Never silently ignore them in a result advertised as preserving the full model. `output` is an observable value, not a safety property.

These decisions are based on the paper’s sequential semantics and the upstream implementations linked above. Fairness concerns liveness witnesses; the paper’s finite bad-state witness definition requires initialization and all global invariant constraints, not satisfaction of a Büchi condition in each frame.

## Validation checklist

Reject unknown operators, malformed immediate parameters, duplicate/out-of-order line IDs, missing/forward references, a sort used as a value, a directive used as a value, absent sort IDs, duplicate init/next assignments, and operands of incompatible structural sorts. Do not merely let Z3 reject malformed input: report source line, node, operator, and expected shape.

| Construct | Required check |
| --- | --- |
| `sort bitvec w` | Positive integer width; use a documented resource cap before allocating solver terms. |
| `sort array i e` | Previously defined index and element sorts. |
| Unary arithmetic/bitwise | BV input and same BV result width. |
| Binary arithmetic/bitwise/shift/rotate | Both operands and result are BVs of the same width. |
| Comparisons/overflow | Equal-width BV operands, BV1 result. |
| `eq`, `neq` | Equal structural operand sorts, BV1 result; arrays are allowed. |
| `iff`, `implies` | All operands/results BV1. |
| `redand`, `redor`, `redxor` | Any positive BV input width, BV1 result. |
| `concat` | BV result width equals sum of operand widths. |
| `slice u l` | `0 <= l <= u < input_width`; result width `u-l+1`. |
| `uext`, `sext` | Nonnegative extension; result width is input width plus extension. |
| `ite` | BV1 condition; both branches and declared result have equal sorts. |
| `read` | First operand array, index matches its domain, result matches its range. |
| `write` | Array result equals first operand sort; index/value match domain/range. |
| `bad`, `constraint`, `fair`, justice members | BV1 references. |
| `output` | BV reference, any positive width. |
| `init`, `next` | Positive state target; declared sort equals state sort; next RHS matches; init exceptions above. |

A binary `const` has exactly the declared number of bits. Hexadecimal and decimal constants must fit; do not silently truncate oversized numerals. Nonnegative decimal values use the full unsigned range; negative decimal values use the signed range. Hex permits leading zeroes and need not have exactly `ceil(width/4)` digits. The parser header caps IDs below `2^40` and widths below `2^31-1`; a Python dictionary avoids sparse-ID allocation, but an explicit smaller maximum width is sensible resource policy, not an extra BTOR2 semantic rule.

Separate fixed operands/immediates from the optional symbol and trailing comment. Numeric-looking symbols are legal names. The upstream parser accepts leading spaces and blank lines but is strict about tabs, single separators, and final newlines. Btor2Sieve may deliberately normalize ordinary whitespace, but document that as input tolerance. Do not interpret a semicolon embedded inside a symbol as a comment without deciding this compatibility policy.

The C parser performs only basic type checks. In particular, add explicit declared-result checks for `ite`, `write`, and array-to-array init, and an upper-bound check for `slice`; the inspected parser does not consistently enforce all of these. Do not copy implementation omissions as specification rules. The CAV paper’s table has an apparent `udivo` entry, but the current README/parser support **only `sdivo`**; reject `udivo`.

## Z3 translation traps and test targets

Keep every BTOR2 predicate as a BV1 expression internally. Wrap a Z3 Boolean result using `If(condition, BitVecVal(1,1), BitVecVal(0,1))`; convert a property/constraint to Boolean with `term == 1`. This avoids accidental Python truth tests and BV1/Bool sort mismatches.

| BTOR2 | Z3 encoding detail |
| --- | --- |
| `ult`, `ulte`, `ugt`, `ugte` | `ULT`, `ULE`, `UGT`, `UGE`; Python `<`/`<=` on BVs are signed. |
| `srl` / `sra` | `LShR(a,b)` / `a >> b`. |
| `udiv`, `urem` | `UDiv`, `URem`. |
| `sdiv`, `srem`, `smod` | Signed BV division, `SRem`, and signed modulo; Z3 `%` on BVs is modulo, not `SRem`. |
| `rol`, `ror` | Variable rotate amount is unsigned and reduced modulo width; use supported extended rotation or an explicit width-modulo construction. Test widths 1, 3, and 70 and an amount above 64 bits. |
| `uaddo` | Carry of zero-extended addition, or mathematical result outside unsigned width. |
| `usubo` | `ULT(a,b)`. |
| `umulo` | High half of zero-extended double-width product is nonzero. |
| `saddo`, `ssubo`, `smulo` | Sign-extend to a sufficiently wide result and test that truncation/re-extension changes it; this covers both positive overflow and negative underflow. |
| `sdivo` | Dividend equals signed minimum and divisor equals all-ones (`-1`). |

Arithmetic wraps at its declared width. SMT-LIB division/remainder are total: unsigned division by zero yields all ones, unsigned remainder by zero yields the dividend. Signed division and signed remainder/modulo follow SMT-LIB’s signed definitions, including the minimum-signed-value divided by minus-one case; preserve these by using the correct BV primitives. Shifts do not reduce their amount modulo width: logical shifts at or beyond width yield zero, while arithmetic-right shift sign-fills. These are high-value exhaustive test cases for widths 1–4, alongside minimum/maximum values and negative-reference operands.

## Small public benchmark plan

Do not call regression examples HWMCC competition entries. Use two labeled groups:

- **HWMCC-derived hardware:** original [Makai Mann collection](https://github.com/makaimann/btor-benchmarks/tree/d9a2792dcee39f17607c889500ac76ad3df35a50), with an explicit [BSD-3-Clause license](https://github.com/makaimann/btor-benchmarks/blob/d9a2792dcee39f17607c889500ac76ad3df35a50/LICENSE). The [SoSy-Lab source inventory](https://gitlab.com/sosy-lab/research/data/word-level-hwmc-benchmarks/-/blob/main/README.md) associates this family with HWMCC 2019/2024. Selected-file membership can additionally be checked against the [HWMCC19 mirror](https://github.com/zhanghongce/HWMCC19-in-CHC/tree/65c2d913d25646d9a0a0f351032e6eddb409e59f/btor2); the mirror itself warns that its blanket licensing status is uncertain, so obtain redistributable files from Mann’s licensed original.
- **Upstream regression examples:** official Btor2Tools (MIT) and Pono (BSD-3-Clause). These cover constant-array initialization, missing-next states, negative IDs, rotations, constraints, and multiple bad properties with tiny files.

Verified original Mann downloads: `safe/analog_estimation_convergence.btor` (3619 bytes; 5 states, 3 inputs, 2 constraints, 1 bad); `unsafe/analog_estimation_convergence.btor` (2950 bytes; same counts); `safe/arbitrated_fifos_n2d8w8.btor` (11421 bytes; one array sort, 22 states, 7 inputs, 5 constraints, 1 bad); `unsafe/arbitrated_fifos_n2d8w8.btor` (11385 bytes; same counts). Despite the `.btor` suffix, these are BTOR2 and start with `sort` declarations. The HWMCC19 mirror directly contains the safe analog and both FIFO files at matching sizes; unsafe analog is a family member rather than a verified selected competition entry.

For multiple properties, [Btor2Tools factorial4even](https://github.com/hwmcc/btor2tools/blob/e6941e37e056084ab6e51c5c1eee6233089a330d/examples/btorsim/factorial4even.btor2) is 411 bytes and is listed in SoSy-Lab’s [multi-bad manifest](https://gitlab.com/sosy-lab/research/data/word-level-hwmc-benchmarks/-/blob/main/bv/btor2/multi-bad.set). Pono’s [rotate regression](https://github.com/stanford-centaur/pono/blob/b0aa8fe43b4449d5ad62abb0f700e04dbbaa8fce/tests/encoders/inputs/btor2/rotate.btor2) is 1224 bytes with ten bad conditions, including wide variable rotation. Pono’s [constarrtest](https://github.com/stanford-centaur/pono/blob/b0aa8fe43b4449d5ad62abb0f700e04dbbaa8fce/samples/constarrtest.btor2) is 216 bytes; [array_lt200](https://github.com/stanford-centaur/pono/blob/b0aa8fe43b4449d5ad62abb0f700e04dbbaa8fce/samples/array_lt200.btor2) is 1205 bytes and uses array-valued `ite`.

Fetch individual pinned raw files, store SHA-256/bytes/source URL/license alongside each, and retain license notices if vendored. Record claimed safe/unsafe labels as upstream labels rather than new solver results. Avoid automatically fetching entire HWMCC archives: HWMCC24’s array archive is 70.6 MB and BV archive about 1.1 GB; [official archive](https://zenodo.org/records/14775242).

## Current-tool context

Pono **2.0.0 was released 2026-05-05**, adding BTOR2 liveness, VMT-LIB, additional algorithms and array capabilities: [official release](https://github.com/stanford-centaur/pono/releases/tag/v2.0.0), [FM 2026 paper](https://www.sosy-lab.org/research/pub/2026-FM.Pono_2.0_A_Versatile_SMT-Based_Model_Checker_for_Safety_and_Liveness.pdf), [reproduction artifact](https://doi.org/10.5281/zenodo.18680797). Do not repeat an old claim that current Pono is safety-only.

[HWMCC25 official results](https://hwmcc.github.io/2025/) include Pono, AVR, BtorMC, rIC3 and Btor2-Select. Pono led the arrays track; rIC3 led the BV track. Btor2-Select’s [CAV 2025 paper](https://www.sosy-lab.org/research/pub/2025-CAV.Btor2-Select_Machine_Learning_Based_Algorithm_Selection_for_Hardware_Model_Checking.pdf) and the related [2025 benchmark performance dataset](https://www.sosy-lab.org/research/pub/2025-TR.Performance_Dataset_for_Hardware_Model_Checking_on_Btor2_Benchmarks.pdf) are useful for later broad evaluation. This starter corpus supports correctness and integration smoke tests, not a comparative performance claim.

## Corpus and implementation validation performed

The original, now removed corpus contained: 13 BTOR2 files, 49,024 bytes, plus three license notices. SHA-256 equality against independently downloaded HWMCC19 mirror files was checked for four selected competition entries; unverified exact membership remains explicitly labeled for the other two Mann family examples. Every file was accepted by the pinned official parser.

The official `catbtor` was built locally from `src/catbtor.c`, `src/btor2parser/btor2parser.c`, and the parser/utility headers using the system C compiler. Build and downloaded artifacts remain under `tmp/research/official/` as optional development evidence; the Python package does not depend on this build. The former corpus verification step checked 16/16 benchmark/license files. An independent re-download to `tmp/research/refetched-corpus` also verified 16/16.

A read-only review of the initial Python parser/encoder, followed by 3,150 exhaustive width-1-through-4 truth-table comparisons, found no mismatch for the seven overflow operators, both rotations, or the three reductions. Expected values were calculated using Python integers, explicit signed ranges, and bit-count parity. This checks these operators only; it is not an independent proof of the entire frontend. The review also flagged that liveness-containing inputs must have an explicit analysis policy rather than silently appearing fully supported.
