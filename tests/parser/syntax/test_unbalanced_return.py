import pytest
from pytest import raises

from srilang import compiler
from srilang.exceptions import StructureException

fail_list = [
    """
@public
def foo() -> int128:
    pass
    """,
    """
@public
def foo() -> int128:
    if False:
        return 123
    """,
    """
@public
def test() -> int128:
    if 1 == 1 :
        return 1
        if True:
            return 0
    else:
        assert False
    """,
    """
@private
def valid_address(sender: address) -> bool:
    selfdestruct(sender)
    return True
    """,
    """
@private
def valid_address(sender: address) -> bool:
    selfdestruct(sender)
    a: address = sender
    """,
    """
@private
def valid_address(sender: address) -> bool:
    if sender == ZERO_ADDRESS:
        selfdestruct(sender)
        _sender: address = sender
    else:
        return False
    """
]


@pytest.mark.parametrize('bad_code', fail_list)
def test_return_mismatch(bad_code):
    with raises(StructureException):
        compiler.compile_code(bad_code)


valid_list = [
    """
@public
def foo() -> int128:
    return 123
    """,
    """
@public
def foo() -> int128:
    if True:
        return 123
    else:
        raise "test"
    """,
    """
@public
def foo() -> int128:
    if False:
        return 123
    else:
        selfdestruct(msg.sender)
    """,
    """
@public
def foo() -> int128:
    if False:
        return 123
    return 333
    """,
    """
@public
def test() -> int128:
    if 1 == 1 :
        return 1
    else:
        assert False
        return 0
    """,
    """
@public
def test() -> int128:
    x: bytes32 = EMPTY_BYTES32
    if False:
        if False:
            return 0
        else:
            x = keccak256(x)
            return 1
    else:
        x = keccak256(x)
        return 1
    return 1
    """
]


@pytest.mark.parametrize('good_code', valid_list)
def test_return_success(good_code):
    assert compiler.compile_code(good_code) is not None
