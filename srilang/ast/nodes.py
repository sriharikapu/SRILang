import ast as python_ast
import decimal
import operator
import sys
from typing import Any, Optional, Union

from srilang.exceptions import (
    CompilerPanic,
    SyntaxException,
    TypeMismatch,
    UnfoldableNode,
    ZeroDivisionException,
)
from srilang.settings import srilang_ERROR_CONTEXT_LINES, srilang_ERROR_LINE_NUMBERS
from srilang.utils import annotate_source_code

NODE_BASE_ATTRIBUTES = (
    "_children",
    "_depth",
    "_parent",
    "ast_type",
    "node_id",
)
NODE_SRC_ATTRIBUTES = (
    "col_offset",
    "end_col_offset",
    "end_lineno",
    "full_source_code",
    "lineno",
    "node_source_code",
    "src",
)

DICT_AST_SKIPLIST = ("full_source_code", "node_source_code")


def get_node(
    ast_struct: Union[dict, python_ast.AST], parent: Optional["srilangNode"] = None
) -> "srilangNode":
    """
    Convert an AST structure to a srilang AST node.

    This is a recursive call, all child nodes of the input value are also
    converted to srilang nodes.

    Parameters
    ----------
    ast_struct: dict | AST
        Annotated python AST node or srilang AST dict to generate the node from.
    parent: srilangNode, optional
        Parent node of the node being created.

    Returns
    -------
    srilangNode
        The generated AST object.
    """
    if not isinstance(ast_struct, dict):
        ast_struct = ast_struct.__dict__

    sri_class = getattr(sys.modules[__name__], ast_struct["ast_type"], None)
    if not sri_class:
        if ast_struct["ast_type"] == "Delete":
            _raise_syntax_exc("Deleting is not supported", ast_struct)
        elif ast_struct["ast_type"] in ("ExtSlice", "Slice"):
            _raise_syntax_exc("srilang does not support slicing", ast_struct)
        elif ast_struct["ast_type"] in ("Invert", "UAdd"):
            op = "+" if ast_struct["ast_type"] == "UAdd" else "~"
            _raise_syntax_exc(
                f"srilang does not support {op} as a unary operator", parent
            )
        else:
            _raise_syntax_exc(
                f"Invalid syntax (unsupported '{ast_struct['ast_type']}' Python AST node)",
                ast_struct,
            )

    return sri_class(parent=parent, **ast_struct)


def compare_nodes(left_node: "srilangNode", right_node: "srilangNode") -> bool:
    """
    Compare the represented value(s) of two srilang nodes.

    This method evaluates a sort of "loose equality". It recursively compares the
    values of each field within two different nodes but does not compare the
    node_id or any members related to source offsets.

    Arguments
    ---------
    left_node : srilangNode
        First node object to compare.
    right_node : srilangNode
        Second node object to compare.

    Returns
    -------
    bool
        True if the given nodes represent the same value(s), False otherwise.
    """
    if not isinstance(left_node, type(right_node)):
        return False

    for field_name in (
        i for i in left_node.get_fields() if i not in srilangNode.__slots__
    ):
        left_value = getattr(left_node, field_name, None)
        right_value = getattr(right_node, field_name, None)

        # compare types instead of isinstance() in case one node class inherits the other
        if type(left_value) is not type(right_value):
            return False

        if isinstance(left_value, list):
            if next(
                (i for i in zip(left_value, right_value) if not compare_nodes(*i)), None
            ):
                return False
        elif isinstance(left_value, srilangNode):
            if not compare_nodes(left_value, right_value):
                return False
        elif left_value != right_value:
            return False

    return True


def _to_node(value, parent):
    # if value is a Python node or dict representing a node, convert to a srilang node
    if isinstance(value, (dict, python_ast.AST)):
        return get_node(value, parent)
    return value


def _to_dict(value):
    # if value is a srilang node, convert to a dict
    if isinstance(value, srilangNode):
        return value.to_dict()
    return value


def _node_filter(node, filters):
    # recursive equality check for srilangNode.get_children filters
    if not filters:
        return True
    for key, value in filters.items():
        if isinstance(value, set):
            if node.get(key) not in value:
                return False
        elif node.get(key) != value:
            return False
    return True


def _sort_nodes(node_iterable):
    # sorting function for srilangNode.get_children

    def sortkey(key):
        return float("inf") if key is None else key

    return sorted(
        node_iterable,
        key=lambda k: (sortkey(k.lineno), sortkey(k.col_offset), k.node_id),
    )


def _raise_syntax_exc(error_msg: str, ast_struct: dict) -> None:
    # helper function to raise a SyntaxException from a dict representing a node
    raise SyntaxException(
        error_msg,
        ast_struct.get("full_source_code"),
        ast_struct.get("lineno"),
        ast_struct.get("col_offset"),
    )


class srilangNode:
    """
    Base class for all srilang AST nodes.

    srilang nodes are generated from, and closely resemble, their Python counterparts.
    Divergences are always handled in a node's `__init__` method, and explained
    in the node docstring.

    Class Attributes
    ----------------
    __slots__ : Tuple
        Allowed field names for the node.
    _description : str, optional
        A human-readable description of the node. Used to give more verbose error
        messages.
    _only_empty_fields : Tuple, optional
        Field names that, if present, must be set to None or a `SyntaxException`
        is raised. This attribute is used to exclude syntax that is valid in Python
        but not in srilang.
    _translated_fields : Dict, optional
        Field names that are reassigned if encountered. Used to normalize fields
        across different Python versions.
    """

    __slots__ = NODE_BASE_ATTRIBUTES + NODE_SRC_ATTRIBUTES
    _only_empty_fields: tuple = ()
    _translated_fields: dict = {}

    def __init__(self, parent: Optional["srilangNode"] = None, **kwargs: dict):
        """
        AST node initializer method.

        Node objects are not typically instantiated directly, you should instead
        create them using the `get_node` method.

        Parameters
        ----------
        parent: srilangNode, optional
            Node which contains this node.
        **kwargs : dict
            Dictionary of fields to be included within the node.
        """
        self._parent = parent
        self._depth = getattr(parent, "_depth", -1) + 1
        self._children: set = set()

        for field_name in NODE_SRC_ATTRIBUTES:
            # when a source offset is not available, use the parent's source offset
            value = kwargs.get(field_name)
            if kwargs.get(field_name) is None:
                value = getattr(parent, field_name, None)
            setattr(self, field_name, value)

        for field_name, value in kwargs.items():
            if field_name in NODE_SRC_ATTRIBUTES:
                continue

            if field_name in self._translated_fields:
                field_name = self._translated_fields[field_name]

            if field_name in self.get_fields():
                if isinstance(value, list):
                    value = [_to_node(i, self) for i in value]
                else:
                    value = _to_node(value, self)
                setattr(self, field_name, value)

            elif value and field_name in self._only_empty_fields:
                _raise_syntax_exc(
                    f"Syntax is valid Python but not valid for srilang\n"
                    f"class: {type(self).__name__}, field_name: {field_name}",
                    kwargs,
                )

        # add to children of parent last to ensure an accurate hash is generated
        if parent is not None:
            parent._children.add(self)

    @classmethod
    def from_node(cls, node: "srilangNode", **kwargs) -> "srilangNode":
        """
        Return a new srilangNode based on an existing node.

        This method creates a new node with the same source offsets as an existing
        node. The new node can then replace the existing node within the AST.
        Preserving source offsets ensures accurate error reporting and source
        map generation from the modified AST.

        Arguments
        ---------
        node: srilangNode
            An existing srilang node. The generated node will have the same source
            offsets and ID as this node.
        **kwargs : Any
            Fields and values for the new node.

        Returns
        -------
        srilang node instance
        """
        ast_struct = {
            i: getattr(node, i) for i in srilangNode.__slots__ if not i.startswith("_")
        }
        ast_struct.update(ast_type=cls.__name__, **kwargs)
        return cls(**ast_struct)

    @classmethod
    def get_fields(cls) -> set:
        """
        Return a set of field names for this node.

        Attributes that are prepended with an underscore are considered private
        and are not included within this sequence.
        """
        slot_fields = [x for i in cls.__mro__ for x in getattr(i, "__slots__", [])]
        return set(i for i in slot_fields if not i.startswith("_"))

    def __hash__(self):
        values = [
            getattr(self, i, None) for i in srilangNode.__slots__ if not i.startswith("_")
        ]
        return hash(tuple(values))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        if other.node_id != self.node_id:
            return False
        for field_name in (
            i for i in self.get_fields() if i not in srilangNode.__slots__
        ):
            if getattr(self, field_name, None) != getattr(other, field_name, None):
                return False
        return True

    def __repr__(self):
        cls = type(self)
        class_repr = f"{cls.__module__}.{cls.__qualname__}"

        source_annotation = annotate_source_code(
            self.full_source_code,
            self.lineno,
            self.col_offset,
            context_lines=srilang_ERROR_CONTEXT_LINES,
            line_numbers=srilang_ERROR_LINE_NUMBERS,
        )

        return f"{class_repr}:\n{source_annotation}"

    @property
    def description(self):
        """
        Property method providing a human-readable description of a node.

        Node-specific description strings are added via the `_descrption` class
        attribute. If this attribute is not found, the name of the class is
        returned instead.
        """
        return getattr(self, "_description", type(self).__name__)

    def evaluate(self) -> "srilangNode":
        """
        Attempt to evaluate the content of a node and generate a new node from it.

        If a node cannot be evaluated it should raise `UnfoldableNode`. This base
        method acts as a catch-all to raise on any inherited classes that do not
        implement the method.
        """
        raise UnfoldableNode(f"{type(self)} cannot be evaluated")

    def to_dict(self) -> dict:
        """
        Return the node as a dict. Child nodes and their descendants are also converted.
        """
        ast_dict = {}
        for key in [i for i in self.get_fields() if i not in DICT_AST_SKIPLIST]:
            value = getattr(self, key, None)
            if isinstance(value, list):
                ast_dict[key] = [_to_dict(i) for i in value]
            else:
                ast_dict[key] = _to_dict(value)
        return ast_dict

    def get_ancestor(
        self, node_type: Union["srilangNode", tuple, None] = None
    ) -> "srilangNode":
        """
        Return an ancestor node for this node.

        An ancestor is any node which exists within the AST above the given node.

        Arguments
        ---------
        node_type : srilangNode | tuple, optional
            A node type or tuple of types. If given, this method checks all
            ancestor nodes of this node starting with the parent, and returns
            the first node with a type matching the given value.

        Returns
        -------
        With no arguments given: the parent of this node.

        With `node_type`: the first matching ascendant node, or `None` if no node
        is found which matches the argument value.
        """
        if node_type is None or self._parent is None:
            return self._parent

        if isinstance(self._parent, node_type):
            return self._parent

        return self._parent.get_ancestor(node_type)

    def get_children(
        self,
        node_type: Union["srilangNode", tuple, None] = None,
        filters: Optional[dict] = None,
        reverse: bool = False,
    ) -> list:
        """
        Return a list of children of this node which match the given filter(s).

        Results are sorted by the starting source offset and node ID, ascending.

        Parameters
        ----------
        node_type : srilangNode | tuple, optional
            A node type or tuple of types. If given, only child nodes where the
            type matches this value are returned. This is functionally identical
            to calling `isinstance(child, node_type)`
        filters : dict, optional
            Dictionary of attribute names and expected values. Only nodes that
            contain the given attributes and match the given values are returned.
            * You can use dots within the name in order to check members of members.
              e.g. `{'annotation.func.id': "constant"}`
            * Expected values may be given as a set, in order to match a node must
              contain the given attribute and match any one value within the set.
              e.g. `{'id': {'public', 'constant'}}` will match nodes with an `id`
                    member that contains either "public" or "constant".
        reverse : bool, optional
            If `True`, the order of results is reversed prior to return.

        Returns
        -------
        list
            Child nodes matching the filter conditions.
        """
        children = _sort_nodes(self._children)
        if node_type is not None:
            children = [i for i in children if isinstance(i, node_type)]
        if reverse:
            children.reverse()
        if filters is None:
            return children
        return [i for i in children if _node_filter(i, filters)]

    def get_descendants(
        self,
        node_type: Union["srilangNode", tuple, None] = None,
        filters: Optional[dict] = None,
        include_self: bool = False,
        reverse: bool = False,
    ) -> list:
        """
        Return a list of descendant nodes of this node which match the given filter(s).

        A descendant is any node which exists within the AST beneath the given node.

        Results are sorted by the starting source offset and depth, ascending. You
        can rely on that the sequence will always contain a parent node prior to any
        of it's children. If the result is reversed, all children of a node will
        be in the sequence prior to their parent.

        Parameters
        ----------
        node_type : srilangNode | tuple, optional
            A node type or tuple of types. If given, only child nodes where the
            type matches this value are returned. This is functionally identical
            to calling `isinstance(child, node_type)`
        filters : dict, optional
            Dictionary of attribute names and expected values. Only nodes that
            contain the given attributes and match the given values are returned.
            * You can use dots within the name in order to check members of members.
              e.g. `{'annotation.func.id': "constant"}`
            * Expected values may be given as a set, in order to match a node must
              contain the given attribute and match any one value within the set.
              e.g. `{'id': {'public', 'constant'}}` will match nodes with an `id`
                    member that contains either "public" or "constant".
        include_self : bool, optional
            If True, this node is also included in the search results if it matches
            the given filter.
        reverse : bool, optional
            If `True`, the order of results is reversed prior to return.

        Returns
        -------
        list
            Descendant nodes matching the filter conditions.
        """
        children = self.get_children(node_type, filters)
        for node in self.get_children():
            children.extend(node.get_descendants(node_type, filters))
        if (
            include_self
            and (not node_type or isinstance(self, node_type))
            and _node_filter(self, filters)
        ):
            children.append(self)
        result = _sort_nodes(children)
        if reverse:
            result.reverse()
        return result

    def get(self, field_str: str) -> Any:
        """
        Recursive getter function for node attributes.

        Parameters
        ----------
        field_str : str
            Attribute string of the location of the node to return.

        Returns
        -------
        srilangNode : optional
            Value at the location of the given field string, if one
            exists. `None` if the field string is empty or invalid.
        """
        obj = self
        for key in field_str.split("."):
            obj = getattr(obj, key, None)
        return obj


class TopLevel(srilangNode):
    """
    Inherited class for Module and FunctionDef nodes.

    Class attributes
    ----------------
    doc_string : Expr
        Expression node representing the docstring within this node.
    """

    __slots__ = ("body", "name", "doc_string")

    def __getitem__(self, key):
        return self.body[key]

    def __iter__(self):
        return iter(self.body)

    def __len__(self):
        return len(self.body)

    def __contains__(self, obj):
        return obj in self.body


class Module(TopLevel):
    __slots__ = ()

    def replace_in_tree(self, old_node: srilangNode, new_node: srilangNode) -> None:
        """
        Perform an in-place substitution of a node within the tree.

        Parameters
        ----------
        old_node : srilangNode
            Node object to be replaced. If the node does not currently exist
            within the AST, a `CompilerPanic` is raised.
        new_node : srilangNode
            Node object to replace new_node.

        Returns
        -------
        None
        """
        parent = old_node._parent
        if old_node not in self.get_descendants(type(old_node)):
            raise CompilerPanic("Node to be replaced does not exist within the tree")

        if old_node not in parent._children:
            raise CompilerPanic(
                "Node to be replaced does not exist within parent children"
            )

        is_replaced = False
        for key in parent.get_fields():
            obj = getattr(parent, key, None)
            if obj == old_node:
                if is_replaced:
                    raise CompilerPanic(
                        "Node to be replaced exists as multiple members in parent"
                    )
                setattr(parent, key, new_node)
                is_replaced = True
            elif isinstance(obj, list) and obj.count(old_node):
                if is_replaced or obj.count(old_node) > 1:
                    raise CompilerPanic(
                        "Node to be replaced exists as multiple members in parent"
                    )
                obj[obj.index(old_node)] = new_node
                is_replaced = True
        if not is_replaced:
            raise CompilerPanic(
                "Node to be replaced does not exist within parent members"
            )

        parent._children.remove(old_node)

        new_node._parent = parent
        new_node._depth = old_node._depth
        parent._children.add(new_node)


class FunctionDef(TopLevel):
    __slots__ = ("args", "returns", "decorator_list", "pos")


class DocStr(srilangNode):
    """
    A docstring.

    Attributes
    ----------
    value : str
        Value of the node, represented as an string.
    """

    __slots__ = ("value",)
    _translated_fields = {"s": "value"}


class arguments(srilangNode):
    __slots__ = ("args", "defaults", "default")
    _only_empty_fields = ("vararg", "kwonlyargs", "kwarg", "kw_defaults")


class arg(srilangNode):
    __slots__ = ("arg", "annotation")


class Return(srilangNode):
    __slots__ = ("value",)


class ClassDef(srilangNode):
    __slots__ = ("class_type", "name", "body")


class Constant(srilangNode):
    # inherited class for all simple constant node types
    __slots__ = ("value",)


class Num(Constant):
    # inherited class for all numeric constant node types
    __slots__ = ()
    _translated_fields = {"n": "value"}

    @property
    def n(self):
        # TODO phase out use of Num.n and remove this
        return self.value


class Int(Num):
    """
    An integer.

    Attributes
    ----------
    value : int
        Value of the node, represented as an integer.
    """

    __slots__ = ()


class Decimal(Num):
    """
    A decimal.

    Attributes
    ----------
    value : decimal.Decimal
        Value of the node, represented as a Decimal object.
    """

    __slots__ = ()


class Hex(Num):
    """
    A hexadecimal value, e.g. `0xFF`

    Attributes
    ----------
    value : str
        Value of the node, represented as a string taken directly from the contract source.
    """

    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(self.value) % 2:
            _raise_syntax_exc(f"Hex notation requires an even number of digits", kwargs)


class Str(Constant):
    __slots__ = ()
    _translated_fields = {"s": "value"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for c in self.value:
            if ord(c) >= 256:
                raise _raise_syntax_exc(
                    f"'{c}' is not an allowed string literal character", kwargs
                )

    @property
    def s(self):
        # TODO phase out use of Str.s and remove this
        return self.value


class Bytes(Constant):
    __slots__ = ()
    _translated_fields = {"s": "value"}

    @property
    def s(self):
        return self.value


class List(srilangNode):
    __slots__ = ("elts",)


class Tuple(srilangNode):
    __slots__ = ("elts",)


class Dict(srilangNode):
    __slots__ = ("keys", "values")


class NameConstant(Constant):
    __slots__ = ("value",)


class Name(srilangNode):
    __slots__ = ("id",)


class Expr(srilangNode):
    __slots__ = ("value",)


class UnaryOp(srilangNode):
    __slots__ = (
        "op",
        "operand",
    )

    def evaluate(self) -> srilangNode:
        """
        Attempt to evaluate the unary operation.

        Returns
        -------
        Int | Decimal
            Node representing the result of the evaluation.
        """
        if isinstance(self.op, Not) and not isinstance(self.operand, NameConstant):
            raise UnfoldableNode("Node contains invalid field(s) for evaluation")
        if isinstance(self.op, USub) and not isinstance(self.operand, (Int, Decimal)):
            raise UnfoldableNode("Node contains invalid field(s) for evaluation")

        value = self.op._op(self.operand.value)
        return type(self.operand).from_node(self, value=value)


class USub(srilangNode):
    __slots__ = ()
    _description = "negation"
    _op = operator.neg


class Not(srilangNode):
    __slots__ = ()
    _op = operator.not_


class BinOp(srilangNode):
    __slots__ = (
        "left",
        "op",
        "right",
    )

    def evaluate(self) -> srilangNode:
        """
        Attempt to evaluate the arithmetic operation.

        Returns
        -------
        Int | Decimal
            Node representing the result of the evaluation.
        """
        left, right = self.left, self.right
        if type(left) is not type(right):
            raise UnfoldableNode("Node contains invalid field(s) for evaluation")
        if not isinstance(left, (Int, Decimal)):
            raise UnfoldableNode("Node contains invalid field(s) for evaluation")

        value = self.op._op(left.value, right.value)
        return type(left).from_node(self, value=value)


class Add(srilangNode):
    __slots__ = ()
    _description = "addition"
    _op = operator.add


class Sub(srilangNode):
    __slots__ = ()
    _description = "subtraction"
    _op = operator.sub


class Mult(srilangNode):
    __slots__ = ()
    _description = "multiplication"

    def _op(self, left, right):
        assert type(left) is type(right)
        value = left * right
        if isinstance(left, decimal.Decimal):
            return value.quantize(decimal.Decimal("1.0000000000"), decimal.ROUND_DOWN)
        else:
            return value


class Div(srilangNode):
    __slots__ = ()
    _description = "division"

    def _op(self, left, right):
        # evaluate the operation using true division or floor division
        assert type(left) is type(right)
        if not right:
            raise ZeroDivisionException("Division by zero")

        if isinstance(left, decimal.Decimal):
            value = left / right
            if value < 0:
                # the EVM always truncates toward zero
                value = -(-left / right)
            # ensure that the result is truncated at 10 decimal places
            return value.quantize(decimal.Decimal("1.0000000000"), decimal.ROUND_DOWN)
        else:
            value = left // right
            if value < 0:
                return -(-left // right)
            return value


class Mod(srilangNode):
    __slots__ = ()
    _description = "modulus"

    def _op(self, left, right):
        if not right:
            raise ZeroDivisionException("Modulo by zero")

        value = abs(left) % abs(right)
        if left < 0:
            value = -value
        return value


class Pow(srilangNode):
    __slots__ = ()
    _description = "exponentiation"

    def _op(self, left, right):
        if isinstance(left, decimal.Decimal):
            raise TypeMismatch(
                "Cannot perform exponentiation on decimal values.", self._parent
            )
        return int(left ** right)


class BoolOp(srilangNode):
    __slots__ = (
        "op",
        "values",
    )

    def evaluate(self) -> srilangNode:
        """
        Attempt to evaluate the boolean operation.

        Returns
        -------
        NameConstant
            Node representing the result of the evaluation.
        """
        if next((i for i in self.values if not isinstance(i, NameConstant)), None):
            raise UnfoldableNode("Node contains invalid field(s) for evaluation")

        values = [i.value for i in self.values]
        if None in values:
            raise UnfoldableNode("Node contains invalid field(s) for evaluation")

        value = self.op._op(values)
        return NameConstant.from_node(self, value=value)


class And(srilangNode):
    __slots__ = ()
    _description = "greater-or-equal"
    _op = all


class Or(srilangNode):
    __slots__ = ()
    _description = "less-or-equal"
    _op = any


class Compare(srilangNode):
    """
    A comparison of two values.

    Attributes
    ----------
    left : srilangNode
        The left-hand value in the comparison.
    op : srilangNode
        The comparison operator.
    right : srilangNode
        The right-hand value in the comparison.
    """

    __slots__ = ("left", "op", "right")

    def __init__(self, *args, **kwargs):
        if len(kwargs["ops"]) > 1 or len(kwargs["comparators"]) > 1:
            _raise_syntax_exc(
                "Cannot have a comparison with more than two elements", kwargs
            )

        kwargs["op"] = kwargs.pop("ops")[0]
        kwargs["right"] = kwargs.pop("comparators")[0]
        super().__init__(*args, **kwargs)

    def evaluate(self) -> srilangNode:
        """
        Attempt to evaluate the comparison.

        Returns
        -------
        NameConstant
            Node representing the result of the evaluation.
        """
        left, right = self.left, self.right
        if not isinstance(left, Constant):
            raise UnfoldableNode("Node contains invalid field(s) for evaluation")

        if isinstance(self.op, In):
            if not isinstance(right, List):
                raise UnfoldableNode("Node contains invalid field(s) for evaluation")
            if next((i for i in right.elts if not isinstance(i, Constant)), None):
                raise UnfoldableNode("Node contains invalid field(s) for evaluation")
            if len(set([type(i) for i in right.elts])) > 1:
                raise UnfoldableNode("List contains multiple literal types")
            value = self.op._op(left.value, [i.value for i in right.elts])
            return NameConstant.from_node(self, value=value)

        if not isinstance(left, type(right)):
            raise UnfoldableNode("Cannot compare different literal types")

        if not isinstance(self.op, (Eq, NotEq)) and not isinstance(
            left, (Int, Decimal)
        ):
            raise TypeMismatch(
                f"Invalid literal types for {self.op.description} comparison", self
            )

        value = self.op._op(left.value, right.value)
        return NameConstant.from_node(self, value=value)


class Eq(srilangNode):
    __slots__ = ()
    _description = "equality"
    _op = operator.eq


class NotEq(srilangNode):
    __slots__ = ()
    _description = "non-equality"
    _op = operator.ne


class Lt(srilangNode):
    __slots__ = ()
    _description = "less than"
    _op = operator.lt


class LtE(srilangNode):
    __slots__ = ()
    _description = "less-or-equal"
    _op = operator.le


class Gt(srilangNode):
    __slots__ = ()
    _description = "greater than"
    _op = operator.gt


class GtE(srilangNode):
    __slots__ = ()
    _description = "greater-or-equal"
    _op = operator.ge


class In(srilangNode):
    __slots__ = ()

    def _op(self, left, right):
        return left in right


class Call(srilangNode):
    __slots__ = ("func", "args", "keywords", "keyword")


class keyword(srilangNode):
    __slots__ = ("arg", "value")


class Attribute(srilangNode):
    __slots__ = (
        "attr",
        "value",
    )


class Subscript(srilangNode):
    __slots__ = ("slice", "value")

    def evaluate(self) -> srilangNode:
        """
        Attempt to evaluate the subscript.

        This method reduces an indexed reference to a literal array into the value
        within the array, e.g. `["foo", "bar"][1]` becomes `"bar"`

        Returns
        -------
        srilangNode
            Node representing the result of the evaluation.
        """
        if not isinstance(self.value, List):
            raise UnfoldableNode("Subscript object is not a literal list")
        elts = self.value.elts
        if len(set([type(i) for i in elts])) > 1:
            raise UnfoldableNode("List contains multiple node types")
        idx = self.slice.get("value.value")
        if not isinstance(idx, int) or idx < 0 or idx >= len(elts):
            raise UnfoldableNode("Invalid index value")

        return elts[idx]


class Index(srilangNode):
    __slots__ = ("value",)


class Assign(srilangNode):
    """
    An assignment.

    Attributes
    ----------
    target : srilangNode
        Left-hand side of the assignment.
    value : srilangNode
        Right-hand side of the assignment.
    """

    __slots__ = ("target", "value")

    def __init__(self, *args, **kwargs):
        if len(kwargs["targets"]) > 1:
            _raise_syntax_exc("Assignment statement must have one target", kwargs)

        kwargs["target"] = kwargs.pop("targets")[0]
        super().__init__(*args, **kwargs)


class AnnAssign(srilangNode):
    __slots__ = ("target", "annotation", "value", "simple")


class AugAssign(srilangNode):
    __slots__ = ("op", "target", "value")


class Raise(srilangNode):
    __slots__ = ("exc",)
    _only_empty_fields = ("cause",)


class Assert(srilangNode):
    __slots__ = ("test", "msg")


class Pass(srilangNode):
    __slots__ = ()


class Import(srilangNode):
    __slots__ = ("names",)


class ImportFrom(srilangNode):
    __slots__ = ("level", "module", "names")


class alias(srilangNode):
    __slots__ = ("name", "asname")


class If(srilangNode):
    __slots__ = ("test", "body", "orelse")


class For(srilangNode):
    __slots__ = ("iter", "target", "body")
    _only_empty_fields = ("orelse",)


class Break(srilangNode):
    __slots__ = ()


class Continue(srilangNode):
    __slots__ = ()
