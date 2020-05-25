import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from srilang import ast as sri_ast
from srilang import functions as sri_fn

denoms = [x for k in sri_fn.AsWeiValue.wei_denoms.keys() for x in k]


st_decimals = st.decimals(
    min_value=0,
    max_value=2 ** 32,
    allow_nan=False,
    allow_infinity=False,
    places=10,
)


@pytest.mark.fuzzing
@settings(max_examples=10, deadline=1000)
@given(value=st_decimals)
@pytest.mark.parametrize('denom', denoms)
def test_decimal(get_contract, value, denom):
    source = f"""
@public
def foo(a: decimal) -> uint256:
    return as_wei_value(a, '{denom}')
    """
    contract = get_contract(source)

    srilang_ast = sri_ast.parse_to_ast(f"as_wei_value({value:.10f}, '{denom}')")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.AsWeiValue().evaluate(old_node)

    assert contract.foo(value) == new_node.value


@pytest.mark.fuzzing
@settings(max_examples=10, deadline=1000)
@given(value=st.integers(min_value=0, max_value=2 ** 128))
@pytest.mark.parametrize('denom', denoms)
def test_integer(get_contract, value, denom):
    source = f"""
@public
def foo(a: uint256) -> uint256:
    return as_wei_value(a, '{denom}')
    """
    contract = get_contract(source)

    srilang_ast = sri_ast.parse_to_ast(f"as_wei_value({value}, '{denom}')")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.AsWeiValue().evaluate(old_node)

    assert contract.foo(value) == new_node.value
