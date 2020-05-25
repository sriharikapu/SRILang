from pathlib import Path

from srilang import ast as sri_ast


def test_all_nodes_have_lineno():
    # every node in an AST tree must have a lineno member
    for path in Path(".").glob("examples/**/*.sri"):
        with path.open() as fp:
            source = fp.read()
            srilang_ast = sri_ast.parse_to_ast(source)
            for item in srilang_ast.get_descendants():
                assert hasattr(item, "lineno")
                assert item.lineno > 0


def test_returns_all_descendants():
    srilang_ast = sri_ast.parse_to_ast("[1, 2, (3, 4, 5, 6), 7]")
    descendants = srilang_ast.get_descendants()

    assert srilang_ast.body[0] in descendants
    for node in srilang_ast.body[0].value.elts:
        assert node in descendants

    for node in srilang_ast.body[0].value.elts[2].elts:
        assert node in descendants


def test_type_filter():
    srilang_ast = sri_ast.parse_to_ast("[1, (2, (3, (4, 5.0), 'six')), 7, 0x08]")
    descendants = srilang_ast.get_descendants(sri_ast.Int)

    assert len(descendants) == 5
    assert not next((i for i in descendants if not isinstance(i, sri_ast.Int)), False)


def test_dict_filter():
    node = sri_ast.parse_to_ast("[foo, (foo(), bar), bar()]").body[0].value

    assert node.get_descendants(filters={"func.id": "foo"}) == [node.elts[1].elts[0]]


def test_include_self():
    srilang_ast = sri_ast.parse_to_ast("1 + 2")
    node = srilang_ast.body[0].value
    descendants = node.get_descendants(sri_ast.BinOp, include_self=True)

    assert descendants == [node]


def test_include_self_wrong_type():
    srilang_ast = sri_ast.parse_to_ast("1 + 2")
    descendants = srilang_ast.get_descendants(sri_ast.Int, include_self=True)

    assert srilang_ast not in descendants


def test_order():
    node = sri_ast.parse_to_ast("[(1 + (2 - 3)) / 4 ** 5, 6 - (7 / -(8 % 9)), 0]")
    node = node.body[0].value
    values = [i.value for i in node.get_descendants(sri_ast.Int)]

    assert values == [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]


def test_order_reversed():
    node = sri_ast.parse_to_ast("[(1 + (2 - 3)) / 4 ** 5, 6 - (7 / -(8 % 9)), 0]")
    node = node.body[0].value
    values = [i.value for i in node.get_descendants(sri_ast.Int, reverse=True)]

    assert values == [0, 9, 8, 7, 6, 5, 4, 3, 2, 1]
