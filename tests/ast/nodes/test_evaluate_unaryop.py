import pytest

from srilang import ast as sri_ast


@pytest.mark.parametrize("bool_cond", [True, False])
def test_unaryop(get_contract, bool_cond):
    source = """
@public
def foo(a: bool) -> bool:
    return not a
    """
    contract = get_contract(source)

    srilang_ast = sri_ast.parse_to_ast(f"not {bool_cond}")
    old_node = srilang_ast.body[0].value
    new_node = old_node.evaluate()

    assert contract.foo(bool_cond) == new_node.value


@pytest.mark.parametrize("count", range(2, 11))
@pytest.mark.parametrize("bool_cond", [True, False])
def test_unaryop_nested(get_contract, bool_cond, count):
    source = f"""
@public
def foo(a: bool) -> bool:
    return {'not ' * count} a
    """
    contract = get_contract(source)

    literal_op = f"{'not ' * count}{bool_cond}"
    srilang_ast = sri_ast.parse_to_ast(literal_op)
    sri_ast.folding.replace_literal_ops(srilang_ast)
    expected = srilang_ast.body[0].value.value

    assert contract.foo(bool_cond) == expected
