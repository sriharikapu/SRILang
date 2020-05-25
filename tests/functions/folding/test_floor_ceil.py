from decimal import Decimal

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from srilang import ast as sri_ast
from srilang import functions as sri_fn

st_decimals = st.decimals(
    min_value=-(2 ** 32),
    max_value=2 ** 32,
    allow_nan=False,
    allow_infinity=False,
    places=10,
)


@pytest.mark.fuzzing
@settings(max_examples=50, deadline=1000)
@given(value=st_decimals)
@example(value=Decimal("0.9999999999"))
@example(value=Decimal("0.0000000001"))
@example(value=Decimal("-0.9999999999"))
@example(value=Decimal("-0.0000000001"))
@pytest.mark.parametrize("fn_name", ["floor", "ceil"])
def test_floor_ceil(get_contract, value, fn_name):
    source = f"""
@public
def foo(a: decimal) -> int128:
    return {fn_name}(a)
    """
    contract = get_contract(source)

    srilang_ast = sri_ast.parse_to_ast(f"{fn_name}({value})")
    old_node = srilang_ast.body[0].value
    new_node = sri_fn.DISPATCH_TABLE[fn_name].evaluate(old_node)

    assert contract.foo(value) == new_node.value
