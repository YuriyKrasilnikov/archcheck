"""Class analyzer."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from archcheck.domain.model.class_ import Class
from archcheck.infrastructure.analyzers.base import (
    extract_base_names,
    extract_init_attributes,
    get_docstring,
    get_visibility,
    has_decorator,
    make_location,
)
from archcheck.infrastructure.analyzers.decorator_analyzer import DecoratorAnalyzer
from archcheck.infrastructure.analyzers.function_analyzer import FunctionAnalyzer

if TYPE_CHECKING:
    from pathlib import Path

    from archcheck.domain.model.function import Function
    from archcheck.domain.model.symbol_table import SymbolTable


class ClassAnalyzer:
    """Extracts class information from Python AST.

    Stateless analyzer - no state between analyze() calls.
    """

    def __init__(self) -> None:
        self._decorator_analyzer = DecoratorAnalyzer()
        self._function_analyzer = FunctionAnalyzer()

    def analyze(
        self,
        node: ast.ClassDef,
        path: Path,
        module_name: str,
        symbol_table: SymbolTable | None = None,
        known_classes: frozenset[str] | None = None,
    ) -> Class:
        """Analyze class AST node.

        Args:
            node: ClassDef AST node
            path: Source file path
            module_name: Fully qualified module name
            symbol_table: Symbol table for name resolution
            known_classes: Known class names in module for CONSTRUCTOR detection

        Returns:
            Class object

        Raises:
            TypeError: If required parameters are None (FAIL-FIRST)
            ValueError: If module_name is empty (FAIL-FIRST)
        """
        # FAIL-FIRST: validate required parameters
        if node is None:
            raise TypeError("node must not be None")
        if path is None:
            raise TypeError("path must not be None")
        if not module_name:
            raise ValueError("module_name must be non-empty string")

        name = node.name
        qualified_name = f"{module_name}.{name}"

        # Extract base classes
        bases = extract_base_names(node)

        # Analyze decorators
        decorators = self._decorator_analyzer.analyze(node.decorator_list, path)

        # Check for special class types
        is_dataclass = has_decorator(node.decorator_list, "dataclass")
        is_abstract = self._is_abstract_class(node, bases)
        is_protocol = self._is_protocol_class(bases)
        is_exception = self._is_exception_class(bases)

        # Extract methods
        methods = self._extract_methods(node, path, module_name, name, symbol_table, known_classes)

        # Extract class attributes
        attributes = self._extract_class_attributes(node, methods)

        # Get docstring
        docstring = get_docstring(node)

        return Class(
            name=name,
            qualified_name=qualified_name,
            bases=bases,
            decorators=decorators,
            methods=methods,
            attributes=attributes,
            location=make_location(node, path),
            visibility=get_visibility(name),
            is_abstract=is_abstract,
            is_dataclass=is_dataclass,
            is_protocol=is_protocol,
            is_exception=is_exception,
            docstring=docstring,
            di_info=None,  # DI analysis is separate concern
        )

    def _extract_methods(
        self,
        node: ast.ClassDef,
        path: Path,
        module_name: str,
        class_name: str,
        symbol_table: SymbolTable | None,
        known_classes: frozenset[str] | None,
    ) -> tuple[Function, ...]:
        """Extract methods from class body.

        Args:
            node: ClassDef AST node
            path: Source file path
            module_name: Fully qualified module name
            class_name: Class name
            symbol_table: Symbol table for name resolution
            known_classes: Known class names for CONSTRUCTOR detection

        Returns:
            Tuple of Function objects for methods
        """
        methods: list[Function] = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                method = self._function_analyzer.analyze(
                    item,
                    path,
                    module_name,
                    class_name,
                    symbol_table,
                    known_classes,
                )
                methods.append(method)

        return tuple(methods)

    def _extract_class_attributes(
        self,
        node: ast.ClassDef,
        methods: tuple[Function, ...],
    ) -> tuple[str, ...]:
        """Extract class-level attributes.

        Includes:
        - Class variables (assigned at class level)
        - Instance attributes from __init__

        Args:
            node: ClassDef AST node
            methods: Already extracted methods

        Returns:
            Tuple of attribute names
        """
        attributes: set[str] = set()

        # Class-level assignments
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.add(target.id)
            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    attributes.add(item.target.id)

        # Instance attributes from __init__
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_attrs = extract_init_attributes(item)
                attributes.update(init_attrs)
                break

        return tuple(sorted(attributes))

    def _is_abstract_class(
        self,
        node: ast.ClassDef,
        bases: tuple[str, ...],
    ) -> bool:
        """Check if class is abstract.

        A class is abstract if:
        - It has @abstractmethod decorated methods
        - It inherits from ABC or ABCMeta

        Args:
            node: ClassDef AST node
            bases: Base class names

        Returns:
            True if abstract
        """
        # Check if inherits from ABC
        abc_bases = {"ABC", "abc.ABC", "ABCMeta", "abc.ABCMeta"}
        if any(base in abc_bases for base in bases):
            return True

        # Check for abstract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                if has_decorator(item.decorator_list, "abstractmethod"):
                    return True

        return False

    def _is_protocol_class(self, bases: tuple[str, ...]) -> bool:
        """Check if class is a Protocol.

        Args:
            bases: Base class names

        Returns:
            True if Protocol
        """
        protocol_bases = {"Protocol", "typing.Protocol", "typing_extensions.Protocol"}
        return any(base in protocol_bases for base in bases)

    def _is_exception_class(self, bases: tuple[str, ...]) -> bool:
        """Check if class is an exception.

        Args:
            bases: Base class names

        Returns:
            True if inherits from exception class
        """
        exception_bases = {
            "Exception",
            "BaseException",
            "RuntimeError",
            "ValueError",
            "TypeError",
            "KeyError",
            "IndexError",
            "AttributeError",
            "OSError",
            "IOError",
            "ImportError",
            "StopIteration",
            "GeneratorExit",
            "SystemExit",
            "KeyboardInterrupt",
        }
        return any(base in exception_bases for base in bases)
