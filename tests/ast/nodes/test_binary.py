import pytest

from srilang import ast as sri_ast
from srilang.exceptions import SyntaxException


def test_binary_becomes_bytes():
    expected = sri_ast.parse_to_ast("foo: bytes[1] = b'\x01'")
    mutated = sri_ast.parse_to_ast("foo: bytes[1] = 0b00000001")

    assert sri_ast.compare_nodes(expected, mutated)


def test_binary_length():
    with pytest.raises(SyntaxException):
        sri_ast.parse_to_ast("foo: bytes[1] = 0b01")
