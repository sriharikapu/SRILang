import copy
import types

from srilang.settings import srilang_ERROR_CONTEXT_LINES, srilang_ERROR_LINE_NUMBERS


class srilangException(Exception):
    """
    Base srilang exception class.

    This exception is not raised directly. Other exceptions inherit it in
    order to display source annotations in the error string.
    """
    def __init__(self, message='Error Message not found.', item=None):
        """
        Exception initializer.

        Arguments
        ---------
        message : str
            Error message to display with the exception.
        item : srilangNode | tuple, optional
            srilang ast node or tuple of (lineno, col_offset) indicating where
            the exception occured.
        """
        self.message = message
        self.lineno = None
        self.col_offset = None

        if isinstance(item, tuple):
            self.lineno, self.col_offset = item[:2]
        elif hasattr(item, 'lineno'):
            self.lineno = item.lineno
            self.col_offset = item.col_offset
            self.source_code = item.full_source_code

    def with_annotation(self, node):
        """
        Creates a copy of this exception with a modified source annotation.

        Arguments
        ---------
        node : srilangNode
            AST node to obtain the source offset from.

        Returns
        -------
        A copy of the exception with the new offset applied.
        """
        exc = copy.copy(self)
        exc.lineno = node.lineno
        exc.col_offset = node.col_offset
        exc.source_code = node.full_source_code
        return exc

    def __str__(self):
        lineno, col_offset = self.lineno, self.col_offset

        if lineno is not None and hasattr(self, 'source_code'):
            from srilang.utils import annotate_source_code

            source_annotation = annotate_source_code(
                self.source_code,
                lineno,
                col_offset,
                context_lines=srilang_ERROR_CONTEXT_LINES,
                line_numbers=srilang_ERROR_LINE_NUMBERS,
            )
            col_offset_str = '' if col_offset is None else str(col_offset)
            return f'line {lineno}:{col_offset_str} {self.message}\n{source_annotation}'

        elif lineno is not None and col_offset is not None:
            return f'line {lineno}:{col_offset} {self.message}'

        return self.message


class SyntaxException(srilangException):

    """Invalid syntax."""

    def __init__(self, message, source_code, lineno, col_offset):
        item = types.SimpleNamespace()  # TODO: Create an actual object for this
        item.lineno = lineno
        item.col_offset = col_offset
        item.full_source_code = source_code
        super().__init__(message, item)


class NatSpecSyntaxException(SyntaxException):
    """Invalid syntax within NatSpec docstring."""


class StructureException(srilangException):
    """Invalid structure for parsable syntax."""


class VersionException(srilangException):
    """Version string is malformed or incompatible with this compiler version."""


class VariableDeclarationException(srilangException):
    """Invalid variable declaration."""


class FunctionDeclarationException(srilangException):
    """Invalid function declaration."""


class EventDeclarationException(srilangException):
    """Invalid event declaration."""


class UndeclaredDefinition(srilangException):
    """Reference to a definition that has not been declared."""


class NamespaceCollision(srilangException):
    """Assignment to a name that is already in use."""


class InvalidLiteral(srilangException):
    """Invalid literal value."""


class InvalidAttribute(srilangException):
    """Reference to an attribute that does not exist."""


class InvalidReference(srilangException):
    """Invalid reference to an existing definition."""


class InvalidOperation(srilangException):
    """Invalid operator for a given type."""


class InvalidType(srilangException):
    """Type is invalid for an action."""


class TypeMismatch(srilangException):
    """Attempt to perform an action between multiple objects of incompatible types."""


class ArgumentException(srilangException):
    """Call to a function with invalid arguments."""


class CallViolation(srilangException):
    """Illegal function call."""


class ConstancyViolation(srilangException):
    """State-changing action in a constant context."""


class NonPayableViolation(srilangException):
    """msg.value in a nonpayable function."""


class InterfaceViolation(srilangException):
    """Interface is not fully implemented."""


class ArrayIndexException(srilangException):
    """Array index out of range."""


class ZeroDivisionException(srilangException):
    """Second argument to a division or modulo operation was zero."""


class OverflowException(srilangException):
    """Numeric value out of range for the given type."""


class EvmVersionException(srilangException):
    """Invalid action for the active EVM ruleset."""


class JSONError(Exception):

    """Invalid compiler input JSON."""

    def __init__(self, msg, lineno=None, col_offset=None):
        super().__init__(msg)
        self.lineno = lineno
        self.col_offset = col_offset


class ParserException(Exception):
    """Contract source cannot be parsed."""


class srilangInternalException(Exception):
    """
    Base srilang internal exception class.

    This exception is not raised directly, it is subclassed by other internal
    exceptions.

    Internal exceptions are raised as a means of passing information between
    compiler processes. They should never be exposed to the user.
    """
    def __init__(self, message=""):
        self.message = message

    def __str__(self):
        return f"{self.message} Please create an issue."


class CompilerPanic(srilangInternalException):
    """Unexpected error during compilation."""


class UnfoldableNode(srilangInternalException):
    """Constant folding logic cannot be applied to an AST node."""
