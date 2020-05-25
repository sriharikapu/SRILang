import pytest

from srilang.ast import parse_natspec, parse_to_ast
from srilang.exceptions import NatSpecSyntaxException
from srilang.parser.global_context import GlobalContext

test_code = """
'''
@title A simulator for Bug Bunny, the most famous Rabbit
@author Warned Bros
@notice You can use this contract for only the most basic simulation
@dev
    Simply chewing a carrot does not count, carrots must pass
    the throat to be considered eaten
'''

@public
@payable
def doesEat(food: string[30], qty: uint256) -> bool:
    '''
    @notice Determine if Bugs will accept `qty` of `food` to eat
    @dev Compares the entire string and does not rely on a hash
    @param food The name of a food to evaluate (in English)
    @param qty The number of food items to evaluate
    @return True if Bugs will eat it, False otherwise
    '''
    return True
"""


expected_userdoc = {
    "methods": {
        "doesEat(string,uint256)": {
            "notice": "Determine if Bugs will accept `qty` of `food` to eat"
        }
    },
    "notice": "You can use this contract for only the most basic simulation",
}


expected_devdoc = {
    "author": "Warned Bros",
    "details": "Simply chewing a carrot does not count, carrots must pass the throat to be considered eaten",  # NOQA: E501
    "methods": {
        "doesEat(string,uint256)": {
            "details": "Compares the entire string and does not rely on a hash",
            "params": {
                "food": "The name of a food to evaluate (in English)",
                "qty": "The number of food items to evaluate",
            },
            "returns": {"_0": "True if Bugs will eat it, False otherwise"},
        }
    },
    "title": "A simulator for Bug Bunny, the most famous Rabbit",
}


def test_documentation_example_output():
    srilang_ast = parse_to_ast(test_code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    userdoc, devdoc = parse_natspec(srilang_ast, global_ctx)

    assert userdoc == expected_userdoc
    assert devdoc == expected_devdoc


def test_no_tags_implies_notice():
    code = """
'''
Because there is no tag, this docstring is handled as a notice.
'''
@public
def foo():
    '''
    This one too!
    '''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    userdoc, devdoc = parse_natspec(srilang_ast, global_ctx)

    assert userdoc == {
        "methods": {"foo()": {"notice": "This one too!"}},
        "notice": "Because there is no tag, this docstring is handled as a notice.",
    }
    assert not devdoc


def test_whitespace():
    code = """
'''
        @dev

  Whitespace    gets  cleaned
    up,
            people can use


         awful formatting.


We don't mind!

@author Mr No-linter
                '''
"""
    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    _, devdoc = parse_natspec(srilang_ast, global_ctx)

    assert devdoc == {
        "author": "Mr No-linter",
        "details": "Whitespace gets cleaned up, people can use awful formatting. We don't mind!",
    }


def test_params():
    code = """
@public
def foo(bar: int128, baz: uint256, potato: bytes32):
    '''
    @param bar a number
    @param baz also a number
    @dev we didn't document potato, but that's ok
    '''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    _, devdoc = parse_natspec(srilang_ast, global_ctx)

    assert devdoc == {
        "methods": {
            "foo(int128,uint256,bytes32)": {
                "details": "we didn't document potato, but that's ok",
                "params": {"bar": "a number", "baz": "also a number"},
            }
        }
    }


def test_returns():
    code = """
@public
def foo(bar: int128, baz: uint256) -> (int128, uint256):
    '''
    @return value of bar
    @return value of baz
    '''
    return bar, baz
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    _, devdoc = parse_natspec(srilang_ast, global_ctx)

    assert devdoc == {
        "methods": {
            "foo(int128,uint256)": {
                "returns": {"_0": "value of bar", "_1": "value of baz"}
            }
        }
    }


def test_ignore_private_methods():
    code = """
@public
def foo(bar: int128, baz: uint256):
    '''@dev I will be parsed.'''
    pass

@private
def notfoo(bar: int128, baz: uint256):
    '''@dev I will not be parsed.'''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    _, devdoc = parse_natspec(srilang_ast, global_ctx)

    assert devdoc["methods"] == {
        "foo(int128,uint256)": {"details": "I will be parsed."}
    }


def test_partial_natspec():
    code = """
@public
def foo():
    '''
    Regular comments preceeding natspec is not allowed
    @notice this is natspec
    '''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(
        NatSpecSyntaxException, match="NatSpec docstring opens with untagged comment"
    ):
        parse_natspec(srilang_ast, global_ctx)


empty_field_cases = [
    """
    @notice
    @dev notice shouldn't be empty
    @author nobody
    """,
    """
    @dev notice shouldn't be empty
    @notice
    @author nobody
    """,
    """
    @dev notice shouldn't be empty
    @author nobody
    @notice
    """,
]


@pytest.mark.parametrize("bad_docstring", empty_field_cases)
def test_empty_field(bad_docstring):
    code = f"""
@public
def foo():
    '''{bad_docstring}'''
    pass
    """
    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(NatSpecSyntaxException, match="No description given for tag '@notice'"):
        parse_natspec(srilang_ast, global_ctx)


def test_unknown_field():
    code = """
@public
def foo():
    '''
    @notice this is ok
    @thing this is bad
    '''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(NatSpecSyntaxException, match="Unknown NatSpec field '@thing'"):
        parse_natspec(srilang_ast, global_ctx)


def test_invalid_field():
    code = """
@public
def foo():
    '''@title function level docstrings cannot have titles'''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(NatSpecSyntaxException, match="'@title' is not a valid field"):
        parse_natspec(srilang_ast, global_ctx)


def test_duplicate_fields():
    code = """
@public
def foo():
    '''
    @notice It's fine to have one notice, but....
    @notice a second one, not so much
    '''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(NatSpecSyntaxException, match="Duplicate NatSpec field '@notice'"):
        parse_natspec(srilang_ast, global_ctx)


def test_duplicate_param():
    code = """
@public
def foo(bar: int128, baz: uint256):
    '''
    @param bar a number
    @param bar also a number
    '''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(
        NatSpecSyntaxException, match="Parameter 'bar' documented more than once"
    ):
        parse_natspec(srilang_ast, global_ctx)


def test_unknown_param():
    code = """
@public
def foo(bar: int128, baz: uint256):
    '''@param hotdog not a number'''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(NatSpecSyntaxException, match="Method has no parameter 'hotdog'"):
        parse_natspec(srilang_ast, global_ctx)


empty_field_cases = [
    """
    @param a
    @dev param shouldn't be empty
    @author nobody
    """,
    """
    @dev param shouldn't be empty
    @param a
    @author nobody
    """,
    """
    @dev param shouldn't be empty
    @author nobody
    @param a
    """,
]


@pytest.mark.parametrize("bad_docstring", empty_field_cases)
def test_empty_param(bad_docstring):
    code = f"""
@public
def foo(a: int128):
    '''{bad_docstring}'''
    pass
    """
    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(NatSpecSyntaxException, match="No description given for parameter 'a'"):
        parse_natspec(srilang_ast, global_ctx)


def test_too_many_returns_no_return_type():
    code = """
@public
def foo():
    '''@return should fail, the function does not include a return value'''
    pass
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(NatSpecSyntaxException, match="Method does not return any values"):
        parse_natspec(srilang_ast, global_ctx)


def test_too_many_returns_single_return_type():
    code = """
@public
def foo() -> int128:
    '''
    @return int128
    @return this should fail
    '''
    return 1
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(
        NatSpecSyntaxException,
        match="Number of documented return values exceeds actual number",
    ):
        parse_natspec(srilang_ast, global_ctx)


def test_too_many_returns_tuple_return_type():
    code = """
@public
def foo() -> (int128,uint256):
    '''
    @return int128
    @return uint256
    @return this should fail
    '''
    return 1, 2
    """

    srilang_ast = parse_to_ast(code)
    global_ctx = GlobalContext.get_global_context(srilang_ast)
    with pytest.raises(
        NatSpecSyntaxException,
        match="Number of documented return values exceeds actual number",
    ):
        parse_natspec(srilang_ast, global_ctx)
