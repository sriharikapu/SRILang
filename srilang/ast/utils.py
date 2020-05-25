import ast as python_ast
from typing import Dict, List, Union

from srilang.ast import nodes as sri_ast
from srilang.ast.annotation import annotate_python_ast
from srilang.ast.pre_parser import pre_parse
from srilang.exceptions import CompilerPanic, ParserException, SyntaxException


def parse_to_ast(source_code: str, source_id: int = 0) -> sri_ast.Module:
    """
    Parses a srilang source string and generates basic srilang AST nodes.

    Parameters
    ----------
    source_code : str
        The srilang source code to parse.
    source_id : int, optional
        Source id to use in the `src` member of each node.

    Returns
    -------
    list
        Untyped, unoptimized srilang AST nodes.
    """
    if "\x00" in source_code:
        raise ParserException("No null bytes (\\x00) allowed in the source code.")
    class_types, reformatted_code = pre_parse(source_code)
    try:
        py_ast = python_ast.parse(reformatted_code)
    except SyntaxError as e:
        # TODO: Ensure 1-to-1 match of source_code:reformatted_code SyntaxErrors
        raise SyntaxException(str(e), source_code, e.lineno, e.offset) from e
    annotate_python_ast(py_ast, source_code, class_types, source_id)

    # Convert to srilang AST.
    return sri_ast.get_node(py_ast)  # type: ignore


def ast_to_dict(ast_struct: Union[sri_ast.srilangNode, List]) -> Union[Dict, List]:
    """
    Converts a srilang AST node, or list of nodes, into a dictionary suitable for
    output to the user.
    """
    if isinstance(ast_struct, sri_ast.srilangNode):
        return ast_struct.to_dict()
    elif isinstance(ast_struct, list):
        return [i.to_dict() for i in ast_struct]
    else:
        raise CompilerPanic(f'Unknown srilang AST node provided: "{type(ast_struct)}".')


def dict_to_ast(ast_struct: Union[Dict, List]) -> Union[sri_ast.srilangNode, List]:
    """
    Converts an AST dict, or list of dicts, into srilang AST node objects.
    """
    if isinstance(ast_struct, dict):
        return sri_ast.get_node(ast_struct)
    if isinstance(ast_struct, list):
        return [sri_ast.get_node(i) for i in ast_struct]
    raise CompilerPanic(f'Unknown ast_struct provided: "{type(ast_struct)}".')
