import pytest

from btor2sieve.btor2 import Btor2Error, parse, parse_file


def test_records_source_directives_and_signed_term_references(tmp_path):
    path = tmp_path / "sample.btor2"
    path.write_text(
        "; sample\n1 sort bitvec 1\n2 zero 1\n3 state 1 latch\n"
        "4 input 1 tick\n5 init 1 3 2\n6 next 1 3 -4\n"
        "7 constraint -3\n8 bad 3 b0\n9 fair -4\n10 justice 2 3 -4\n",
        encoding="utf-8",
    )
    model = parse_file(path)
    assert model.source == str(path)
    assert model.sorts[1].width == 1
    assert model.states == [model.nodes[3]]
    assert model.inputs == [model.nodes[4]]
    assert model.inits == [model.nodes[5]]
    assert model.nexts[0].args == (3, -4)
    assert model.constraints[0].args == (-3,)
    assert model.bads[0].symbol == "b0"
    assert model.nodes[9].op == "fair"
    assert model.nodes[10].params == (2,)
    assert model.nodes[10].args == (3, -4)
    assert model.nodes[10].line == 11


@pytest.mark.parametrize(
    ("program", "message"),
    [
        ("1 sort bitvec 0", "width"),
        ("1 sort bitvec 2\n1 zero 1", "increasing"),
        ("2 sort bitvec 2\n1 zero 2", "increasing"),
        ("1 sort bitvec 1\n2 not 1 3", "reference"),
        ("1 sort bitvec 1\n2 not 1 1", "reference"),
        ("1 sort bitvec 1\n2 one 1\n3 bad 2\n4 not 1 3", "reference"),
        ("1 sort bitvec 1\n2 not 1", "arity"),
        ("1 sort bitvec 1\n2 one 1 name extra", "arity"),
        ("1 sort bitvec 2\n2 const 1 1", "constant"),
        ("1 sort bitvec 2\n2 constd 1 -3", "constant"),
        ("1 sort bitvec 2\n2 consth 1 4", "constant"),
        ("1 sort bitvec 2\n2 one 1\n3 slice 1 2 2 1", "slice"),
        ("1 sort bitvec 2\n2 one 1\n3 bad 2", "bitvec 1"),
        ("1 sort bitvec 2\n2 one 1\n3 implies 1 2 2", "sort"),
        ("1 sort bitvec 2\n2 sort array 1 1\n3 input 2\n4 read 1 -3 3", "array"),
        ("1 sort bitvec 1\n2 sort bitvec 2\n3 one 1\n4 one 2\n5 ite 2 3 3 3", "sort"),
        ("1 sort bitvec 1\n2 sort bitvec 2\n3 sort array 1 1\n4 sort array 1 2\n"
         "5 input 3\n6 one 1\n7 write 4 5 6 6", "sort"),
        ("1 sort bitvec 1\n2 one 1\n3 next 1 2 2", "state"),
        ("1 sort bitvec 1\n2 state 1\n3 next 1 -2 2", "state"),
        ("1 sort bitvec 1\n2 state 1\n3 next 1 2 2\n4 next 1 2 2", "duplicate"),
        ("1 sort bitvec 1\n2 zero 1\n3 state 1\n4 init 1 3 2\n5 init 1 3 2", "duplicate"),
        ("1 sort bitvec 1\n2 state 1\n3 init 1 2 -2", "precede"),
        ("1 sort bitvec 1\n2 state 1\n3 one 1\n4 init 1 2 3", "precede"),
        ("1 sort bitvec 1\n2 input 1\n3 not 1 2\n4 state 1\n5 init 1 4 3", "input"),
        ("1 sort bitvec 1\n2 sort array 1 1\n3 one 1\n4 not 1 3\n"
         "5 state 2\n6 init 2 5 4", "constant"),
        ("1 sort bitvec 1\n2 one 1\n3 justice 2 2", "arity"),
        ("1 sort bitvec 1\n2 mystery 1", "unsupported"),
    ],
)
def test_reports_malformed_lines_with_source(program, message):
    with pytest.raises(Btor2Error, match=rf"sample\.btor2:{len(program.splitlines())}: .*{message}"):
        parse(program, "sample.btor2")
