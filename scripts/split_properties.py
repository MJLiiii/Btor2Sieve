#!/usr/bin/env python3
"""Split multi-property BTOR2 models into one single-property model per `bad` directive.

For a model with bad directives b0, b1, ..., bN, the split ``<name>-b<i>.btor2``
keeps every line of the source except the other bad directives. Nothing is
renumbered and no cone-of-influence reduction is applied, so:

* the kept property has the same line id (the reports' ``property_id``) as in
  the multi-property model, which lets results be joined row by row;
* inputs, states, `constraint` assumptions and outputs are unchanged.

Each split is checked before it is written: Pono must read it (``--pono``),
it must have exactly one bad directive equal to the source's b<i>, and it
must differ from the source only by the removed bad lines. Models with `justice` or `fair` declarations are
rejected, because only safety properties are split.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from btor2sieve.pono import check_readable, scan  # noqa: E402


class SplitError(ValueError):
    """A model that cannot be split, or a split that fails its check."""


def split(text: str, source: str = "<string>", pono: str = "pono") -> list[str]:
    """Return one model text per bad directive, in definition order (b0, b1, ...)."""
    try:
        model = scan(text)
    except ValueError as exc:
        raise SplitError(f"{source}: {exc}") from None
    if any(line.op in ("justice", "fair") for line in model):
        raise SplitError(f"{source}: justice/fair declarations are not supported")
    bads = [line for line in model if line.op == "bad"]
    if len(bads) < 2:
        raise SplitError(f"{source}: has {len(bads)} bad directive(s); nothing to split")
    lines = text.splitlines()
    bad_lines = {bad.number for bad in bads}
    outputs = []
    for index, kept in enumerate(bads):
        note = (f"; single-property split by scripts/split_properties.py: "
                f"b{index} of {len(bads)} (line id {kept.id}) from {Path(source).name}")
        body = [line for number, line in enumerate(lines, start=1)
                if number not in bad_lines or number == kept.number]
        # Leading comments stay first; the note follows them.
        lead = 0
        while lead < len(body) and (not body[lead].strip() or body[lead].lstrip().startswith(";")):
            lead += 1
        result = "\n".join([*body[:lead], note, *body[lead:]]) + "\n"
        _check(lines, bad_lines, kept, result, source, index, pono)
        outputs.append(result)
    return outputs


def _check(lines: list[str], bad_lines: set[int], kept, result: str, source: str, index: int,
           pono: str) -> None:
    single = [line for line in scan(result) if line.op == "bad"]
    if [(b.id, b.words) for b in single] != [(kept.id, kept.words)]:
        raise SplitError(f"split b{index} does not keep exactly bad {kept.id}")
    expected = [line for number, line in enumerate(lines, start=1)
                if number not in bad_lines or number == kept.number]
    actual = [line for line in result.splitlines() if not line.startswith("; single-property split")]
    if actual != expected:
        raise SplitError(f"split b{index} changes lines other than the removed bad directives")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / f"{Path(source).stem}-b{index}.btor2"
        path.write_text(result, encoding="utf-8")
        try:
            check_readable(pono, path)
        except ValueError as exc:
            raise SplitError(f"split b{index}: {exc}") from None


def names(stem: str, count: int) -> list[str]:
    width = max(2, len(str(count - 1)))
    return [f"{stem}-b{index:0{width}d}.btor2" for index in range(count)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("models", type=Path, nargs="+", help="multi-property BTOR2 models")
    parser.add_argument("--out", type=Path, required=True,
                        help="directory; each model's splits go to <out>/<model name>/")
    parser.add_argument("--pono", default="pono", help="Pono executable that must read every split")
    args = parser.parse_args(argv)

    planned = []
    for model in args.models:
        try:
            texts = split(model.read_text(encoding="utf-8"), str(model), args.pono)
        except (SplitError, OSError, UnicodeError) as exc:
            print(f"error: {model}: {exc}", file=sys.stderr)
            return 1
        folder = args.out / model.stem
        planned += [(folder / name, text) for name, text in zip(names(model.stem, len(texts)), texts)]
    targets = [target for target, _ in planned]
    if len(set(targets)) != len(targets):
        parser.error("two models would write the same split file")
    clashes = [str(target) for target in targets if target.exists()]
    if clashes:
        parser.error("refusing to overwrite: " + ", ".join(clashes[:5]) + (" ..." if len(clashes) > 5 else ""))
    for target, text in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for model in args.models:
        count = sum(1 for target in targets if target.parent == args.out / model.stem)
        print(f"{model} -> {args.out / model.stem}/ ({count} single-property models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
