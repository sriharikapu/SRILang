from srilang import ast as sri_ast


def test_compare_different_node_clases():
    srilang_ast = sri_ast.parse_to_ast("foo = 42")
    left = srilang_ast.body[0].target
    right = srilang_ast.body[0].value

    assert left != right
    assert not sri_ast.compare_nodes(left, right)


def test_compare_different_nodes_same_class():
    srilang_ast = sri_ast.parse_to_ast("[1, 2]")
    left, right = srilang_ast.body[0].value.elts

    assert left != right
    assert not sri_ast.compare_nodes(left, right)


def test_compare_different_nodes_same_value():
    srilang_ast = sri_ast.parse_to_ast("[1, 1]")
    left, right = srilang_ast.body[0].value.elts

    assert left != right
    assert sri_ast.compare_nodes(left, right)


def test_compare_complex_nodes_same_value():
    srilang_ast = sri_ast.parse_to_ast("[{'foo':'bar', 43:[1,2,3]}, {'foo':'bar', 43:[1,2,3]}]")
    left, right = srilang_ast.body[0].value.elts

    assert left != right
    assert sri_ast.compare_nodes(left, right)


def test_compare_same_node():
    srilang_ast = sri_ast.parse_to_ast("42")
    node = srilang_ast.body[0].value

    assert node == node
    assert sri_ast.compare_nodes(node, node)
