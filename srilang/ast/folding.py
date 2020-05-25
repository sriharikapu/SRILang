from decimal import Decimal
from typing import Union

from srilang.ast import nodes as sri_ast
from srilang.exceptions import UnfoldableNode
from srilang.functions import DISPATCH_TABLE

BUILTIN_CONSTANTS = {
    "EMPTY_BYTES32": (
        sri_ast.Hex,
        "0x0000000000000000000000000000000000000000000000000000000000000000",
    ),  # NOQA: E501
    "ZERO_ADDRESS": (sri_ast.Hex, "0x0000000000000000000000000000000000000000"),
    "MAX_INT128": (sri_ast.Int, 2 ** 127 - 1),
    "MIN_INT128": (sri_ast.Int, -(2 ** 127)),
    "MAX_DECIMAL": (sri_ast.Decimal, Decimal(2 ** 127 - 1)),
    "MIN_DECIMAL": (sri_ast.Decimal, Decimal(-(2 ** 127))),
    "MAX_UINT256": (sri_ast.Int, 2 ** 256 - 1),
}


def fold(srilang_module: sri_ast.Module) -> None:
    """
    Perform literal folding operations on a srilang AST.

    Arguments
    ---------
    srilang_module : Module
        Top-level srilang AST node.
    """
    replace_builtin_constants(srilang_module)

    changed_nodes = 1
    while changed_nodes:
        changed_nodes = 0
        changed_nodes += replace_user_defined_constants(srilang_module)
        changed_nodes += replace_literal_ops(srilang_module)
        changed_nodes += replace_subscripts(srilang_module)
        changed_nodes += replace_builtin_functions(srilang_module)


def replace_literal_ops(srilang_module: sri_ast.Module) -> int:
    """
    Find and evaluate operation and comparison nodes within the srilang AST,
    replacing them with Constant nodes where possible.

    Arguments
    ---------
    srilang_module : Module
        Top-level srilang AST node.

    Returns
    -------
    int
        Number of nodes that were replaced.
    """
    changed_nodes = 0

    node_types = (sri_ast.BoolOp, sri_ast.BinOp, sri_ast.UnaryOp, sri_ast.Compare)
    for node in srilang_module.get_descendants(node_types, reverse=True):
        try:
            new_node = node.evaluate()
        except UnfoldableNode:
            continue

        changed_nodes += 1
        srilang_module.replace_in_tree(node, new_node)

    return changed_nodes


def replace_subscripts(srilang_module: sri_ast.Module) -> int:
    """
    Find and evaluate Subscript nodes within the srilang AST, replacing them with
    Constant nodes where possible.

    Arguments
    ---------
    srilang_module : Module
        Top-level srilang AST node.

    Returns
    -------
    int
        Number of nodes that were replaced.
    """
    changed_nodes = 0

    for node in srilang_module.get_descendants(sri_ast.Subscript, reverse=True):
        try:
            new_node = node.evaluate()
        except UnfoldableNode:
            continue

        changed_nodes += 1
        srilang_module.replace_in_tree(node, new_node)

    return changed_nodes


def replace_builtin_functions(srilang_module: sri_ast.Module) -> int:
    """
    Find and evaluate builtin function calls within the srilang AST, replacing
    them with Constant nodes where possible.

    Arguments
    ---------
    srilang_module : Module
        Top-level srilang AST node.

    Returns
    -------
    int
        Number of nodes that were replaced.
    """
    changed_nodes = 0

    for node in srilang_module.get_descendants(sri_ast.Call, reverse=True):
        if not isinstance(node.func, sri_ast.Name):
            continue

        name = node.func.id
        func = DISPATCH_TABLE.get(name)
        if func is None or not hasattr(func, "evaluate"):
            continue
        try:
            new_node = func.evaluate(node)  # type: ignore
        except UnfoldableNode:
            continue

        changed_nodes += 1
        srilang_module.replace_in_tree(node, new_node)

    return changed_nodes


def replace_builtin_constants(srilang_module: sri_ast.Module) -> None:
    """
    Replace references to builtin constants with their literal values.

    Arguments
    ---------
    srilang_module : Module
        Top-level srilang AST node.
    """
    for name, (node, value) in BUILTIN_CONSTANTS.items():
        replace_constant(srilang_module, name, node(value=value), True)  # type: ignore


def replace_user_defined_constants(srilang_module: sri_ast.Module) -> int:
    """
    Find user-defined constant assignments, and replace references
    to the constants with their literal values.

    Arguments
    ---------
    srilang_module : Module
        Top-level srilang AST node.

    Returns
    -------
    int
        Number of nodes that were replaced.
    """
    changed_nodes = 0

    for node in srilang_module.get_children(sri_ast.AnnAssign):
        if not isinstance(node.target, sri_ast.Name):
            # left-hand-side of assignment is not a variable
            continue
        if node.get("annotation.func.id") != "constant":
            # annotation is not wrapped in `constant(...)`
            continue

        changed_nodes += replace_constant(
            srilang_module, node.target.id, node.value, False
        )

    return changed_nodes


def _replace(old_node, new_node):
    if isinstance(new_node, sri_ast.Constant):
        return new_node.from_node(old_node, value=new_node.value)
    elif isinstance(new_node, sri_ast.List):
        list_values = [_replace(old_node, i) for i in new_node.elts]
        return new_node.from_node(old_node, elts=list_values)
    else:
        raise UnfoldableNode


def replace_constant(
    srilang_module: sri_ast.Module,
    id_: str,
    replacement_node: Union[sri_ast.Constant, sri_ast.List],
    raise_on_error: bool,
) -> int:
    """
    Replace references to a variable name with a literal value.

    Arguments
    ---------
    srilang_module : Module
        Module-level ast node to perform replacement in.
    id_ : str
        String representing the `.id` attribute of the node(s) to be replaced.
    replacement_node : Constant | List
        srilang ast node representing the literal value to be substituted in.
    raise_on_error: bool
        Boolean indicating if `UnfoldableNode` exception should be raised or ignored.

    Returns
    -------
    int
        Number of nodes that were replaced.
    """
    changed_nodes = 0

    for node in srilang_module.get_descendants(sri_ast.Name, {"id": id_}, reverse=True):
        parent = node.get_ancestor()

        if isinstance(parent, sri_ast.Attribute):
            # do not replace attributes
            continue
        if isinstance(parent, sri_ast.Call) and node == parent.func:
            # do not replace calls
            continue

        # do not replace dictionary keys
        if isinstance(parent, sri_ast.Dict) and node in parent.keys:
            continue

        if not isinstance(parent, sri_ast.Index):
            # do not replace left-hand side of assignments
            assign = node.get_ancestor(
                (sri_ast.Assign, sri_ast.AnnAssign, sri_ast.AugAssign)
            )
            if assign and node in assign.target.get_descendants(include_self=True):
                continue

        try:
            new_node = _replace(node, replacement_node)
        except UnfoldableNode:
            if raise_on_error:
                raise
            continue

        changed_nodes += 1
        srilang_module.replace_in_tree(node, new_node)

    return changed_nodes
