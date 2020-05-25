from srilang import ast as sri_ast


def test_order():
    node = sri_ast.parse_to_ast("1 + 2").body[0].value
    assert node.get_children() == [node.left, node.op, node.right]


def test_order_reversed():
    node = sri_ast.parse_to_ast("1 + 2").body[0].value
    assert node.get_children(reverse=True) == [node.right, node.op, node.left]


def test_type_filter():
    node = sri_ast.parse_to_ast("[1, 2.0, 'three', 4, 0x05]").body[0].value
    assert node.get_children(sri_ast.Int) == [node.elts[0], node.elts[3]]


def test_dict_filter():
    node = sri_ast.parse_to_ast("[foo, foo(), bar, bar()]").body[0].value
    assert node.get_children(filters={"func.id": "foo"}) == [node.elts[1]]


def test_only_returns_children():
    node = sri_ast.parse_to_ast("[1, 2, (3, 4), 5]").body[0].value
    assert node.get_children() == node.elts
