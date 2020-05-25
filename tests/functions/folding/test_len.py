import pytest

from srilang import ast as sri_ast
from srilang import functions as sri_fn


@pytest.mark.parametrize("length", [0, 1, 32, 33, 64, 65, 1024])
def test_len_string(get_contract, length):
    source = f"""
@public
def foo(a: string[1024]) -> int128:
    return len(a)
    """
    contract = get_contract(source)

    value = "a" * length

    srilang_ast = sri_ast.parse_to_ast(f"len('{value}')")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.Len().evaluate(old_node)

    assert contract.foo(value) == new_node.value


@pytest.mark.parametrize("length", [0, 1, 32, 33, 64, 65, 1024])
def test_len_bytes(get_contract, length):
    source = f"""
@public
def foo(a: bytes[1024]) -> int128:
    return len(a)
    """
    contract = get_contract(source)

    value = "a" * length

    srilang_ast = sri_ast.parse_to_ast(f"len(b'{value}')")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.Len().evaluate(old_node)

    assert contract.foo(value.encode()) == new_node.value


@pytest.mark.parametrize("length", [1, 32, 33, 64, 65, 1024])
def test_len_hex(get_contract, length):
    source = f"""
@public
def foo(a: bytes[1024]) -> int128:
    return len(a)
    """
    contract = get_contract(source)

    value = f"0x{'00' * length}"

    srilang_ast = sri_ast.parse_to_ast(f"len({value})")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.Len().evaluate(old_node)

    assert contract.foo(value) == new_node.value
