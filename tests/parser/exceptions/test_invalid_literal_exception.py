import pytest
from pytest import raises

from srilang import compiler
from srilang.exceptions import InvalidLiteral

fail_list = [
    """
@public
def foo():
    x: int128 = -170141183460469231731687303715884105729 # -2**127 - 1
    """,
    """
@public
def foo():
    x: decimal = -170141183460469231731687303715884105728.0000000001
    """,
    """
b: decimal
@public
def foo():
    self.b = 7.5178246872145875217495129745982164981654986129846
    """,
    """
@public
def foo():
    x = as_wei_value(0x05, "babbage")
    """,
    """
@public
def foo():
    send(0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae, 5)
    """,
    """
@public
def foo():
    x: uint256 = convert(821649876217461872458712528745872158745214187264875632587324658732648753245328764872135671285218762145, uint256)  # noqa: E501
    """,
    """
@public
def foo():
    x = convert(-(-(-1)), uint256)
    """,
    """
# Test decimal limit.
a:decimal

@public
def foo():
    self.a = 170141183460469231731687303715884105727.888
    """,
    """
@public
def overflow() -> uint256:
    return 2**256
    """,
    """
@public
def overflow2() -> uint256:
    a: uint256 = 2**256
    return a
    """,
]


@pytest.mark.parametrize('bad_code', fail_list)
def test_invalid_literal_exception(bad_code):
    with raises(InvalidLiteral):
        compiler.compile_code(bad_code)
