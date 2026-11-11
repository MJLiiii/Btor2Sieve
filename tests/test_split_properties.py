"""scripts/split_properties.py: one single-property model per bad directive, ids unchanged.

Pono (on PATH, inside nix-shell) must read every split."""

import importlib.util
from pathlib import Path
import sys

import pytest

from btor2sieve.pono import scan


def _ops(text: str, op: str):
    return [line for line in scan(text) if line.op == op]


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("split_properties", ROOT / "scripts/split_properties.py")
split_properties = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = split_properties
_spec.loader.exec_module(split_properties)

MULTI = """\
; generated for a test
1 sort bitvec 1
2 input 1 a
3 state 1 s
4 next 1 3 2
5 bad 2 first
6 constraint 3
7 not 1 3
8 bad 7 second
9 and 1 2 3
10 bad 9
"""


def test_each_split_keeps_one_property_and_its_id():
    texts = split_properties.split(MULTI, "multi.btor2")
    assert len(texts) == 3
    assert [[(bad.id, bad.words) for bad in _ops(text, "bad")] for text in texts] == [
        [(5, ("2", "first"))], [(8, ("7", "second"))], [(10, ("9",))]]
    for text in texts:
        assert [line.id for line in _ops(text, "constraint")] == [6]
        assert [line.id for line in _ops(text, "state")] == [3]


def test_split_only_removes_other_bad_lines():
    first = split_properties.split(MULTI)[0].splitlines()
    assert first[0] == "; generated for a test"
    assert first[1].startswith("; single-property split") and "b0 of 3 (line id 5)" in first[1]
    assert first[2:] == [line for line in MULTI.splitlines()[1:] if line not in ("8 bad 7 second", "10 bad 9")]


@pytest.mark.parametrize("model, message", [
    ("1 sort bitvec 1\n2 input 1 a\n3 bad 2\n", "nothing to split"),
    ("1 sort bitvec 1\n2 input 1 a\n3 bad 2\n4 bad 2\n5 fair 2\n", "justice/fair"),
    ("1 sort bitvec 1\n2 frobnicate 1\n3 bad 2\n4 bad 2\n", "Pono could not read"),
])
def test_unsplittable_models(model, message):
    with pytest.raises(split_properties.SplitError, match=message):
        split_properties.split(model)


def test_check_rejects_a_changed_line():
    lines = MULTI.splitlines()
    bads = _ops(MULTI, "bad")
    bad_lines = {bad.number for bad in bads}
    good = split_properties.split(MULTI)[1]
    with pytest.raises(split_properties.SplitError, match="changes lines"):
        split_properties._check(lines, bad_lines, bads[1], good.replace("6 constraint 3", "6 constraint -3"),
                                "", 1, "pono")


def test_names_are_zero_padded():
    assert split_properties.names("m", 3) == ["m-b00.btor2", "m-b01.btor2", "m-b02.btor2"]
    assert split_properties.names("m", 101)[-1] == "m-b100.btor2"


def test_cli_writes_one_folder_per_model_and_refuses_to_overwrite(tmp_path, capsys):
    model = tmp_path / "design.btor2"
    model.write_text(MULTI)
    out = tmp_path / "single"
    assert split_properties.main([str(model), "--out", str(out)]) == 0
    files = sorted(path.name for path in (out / "design").iterdir())
    assert files == ["design-b00.btor2", "design-b01.btor2", "design-b02.btor2"]
    assert _ops((out / "design" / "design-b02.btor2").read_text(), "bad")[0].id == 10
    with pytest.raises(SystemExit):
        split_properties.main([str(model), "--out", str(out)])
    assert "refusing to overwrite" in capsys.readouterr().err


def test_cli_writes_nothing_when_any_model_fails(tmp_path):
    good, single = tmp_path / "good.btor2", tmp_path / "single.btor2"
    good.write_text(MULTI)
    single.write_text("1 sort bitvec 1\n2 input 1 a\n3 bad 2\n")
    out = tmp_path / "split"
    assert split_properties.main([str(good), str(single), "--out", str(out)]) == 1
    assert not out.exists()


CAV18 = ROOT / "benchmarks/cav18/2018"


def test_local_cav18_single_matches_multi():
    multi = sorted((CAV18 / "multi").glob("*/*.btor2"))
    if not multi:
        pytest.skip("CAV'18 models not set up locally; see benchmarks/README.md")
    for path in multi:
        source = _ops(path.read_text(), "bad")
        folder = CAV18 / "single" / path.parent.name / path.stem
        splits = sorted(folder.glob("*.btor2"))
        assert [_ops(split.read_text(), "bad")[0].id for split in splits] == [bad.id for bad in source], path
