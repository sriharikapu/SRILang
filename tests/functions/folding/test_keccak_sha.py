import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from srilang import ast as sri_ast
from srilang import functions as sri_fn

alphabet = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&()*+,-./:;<=>?@[]^_`{|}~'  # NOQA: E501


@pytest.mark.fuzzing
@given(value=st.text(alphabet=alphabet, min_size=0, max_size=100))
@settings(max_examples=50, deadline=1000)
@pytest.mark.parametrize('fn_name', ['keccak256', 'sha256'])
def test_string(get_contract, value, fn_name):

    source = f"""
@public
def foo(a: string[100]) -> bytes32:
    return {fn_name}(a)
    """
    contract = get_contract(source)

    srilang_ast = sri_ast.parse_to_ast(f"{fn_name}('''{value}''')")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.DISPATCH_TABLE[fn_name].evaluate(old_node)

    assert f"0x{contract.foo(value).hex()}" == new_node.value


@pytest.mark.fuzzing
@given(value=st.binary(min_size=0, max_size=100))
@settings(max_examples=50, deadline=1000)
@pytest.mark.parametrize('fn_name', ['keccak256', 'sha256'])
def test_bytes(get_contract, value, fn_name):
    source = f"""
@public
def foo(a: bytes[100]) -> bytes32:
    return {fn_name}(a)
    """
    contract = get_contract(source)

    srilang_ast = sri_ast.parse_to_ast(f"{fn_name}({value})")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.DISPATCH_TABLE[fn_name].evaluate(old_node)

    assert f"0x{contract.foo(value).hex()}" == new_node.value


@pytest.mark.fuzzing
@given(value=st.binary(min_size=1, max_size=100))
@settings(max_examples=50, deadline=1000)
@pytest.mark.parametrize('fn_name', ['keccak256', 'sha256'])
def test_hex(get_contract, value, fn_name):
    source = f"""
@public
def foo(a: bytes[100]) -> bytes32:
    return {fn_name}(a)
    """
    contract = get_contract(source)

    value = f"0x{value.hex()}"

    srilang_ast = sri_ast.parse_to_ast(f"{fn_name}({value})")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.DISPATCH_TABLE[fn_name].evaluate(old_node)

    assert f"0x{contract.foo(value).hex()}" == new_node.value
