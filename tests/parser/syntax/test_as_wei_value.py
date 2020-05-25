import pytest
from pytest import raises

from srilang import compiler
from srilang.exceptions import ArgumentException, TypeMismatch

fail_list = [
    ("""
@public
def foo():
    x: int128 = as_wei_value(5, szabo)
    """, ArgumentException),
    ("""
@public
def foo() -> int128:
    x: int128 = 45
    return x.balance
    """, TypeMismatch),
]


@pytest.mark.parametrize('bad_code,exc', fail_list)
def test_as_wei_fail(bad_code, exc):
    with raises(exc):
        compiler.compile_code(bad_code)


valid_list = [
    """
@public
def foo():
    x: uint256 = as_wei_value(5, "finney") + as_wei_value(2, "babbage") + as_wei_value(8, "shannon")  # noqa: E501
    """,
    """
@public
def foo():
    z: int128 = 2 + 3
    x: uint256 = as_wei_value(2 + 3, "finney")
    """,
    """
@public
def foo():
    x: uint256 = as_wei_value(5.182, "babbage")
    """,
    """
@public
def foo() -> uint256:
    x: address = 0x1234567890123456789012345678901234567890
    return x.balance
    """
]


@pytest.mark.parametrize('good_code', valid_list)
def test_as_wei_success(good_code):
    assert compiler.compile_code(good_code) is not None
