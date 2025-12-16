"""Check functions for DSL assertions.

Internal module - not part of public API.
Each function returns Violation | None.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.location import Location
from archcheck.domain.model.violation import Violation
from archcheck.presentation.api._helpers import get_layer
from archcheck.presentation.api.patterns import CompiledPattern, matches_any

if TYPE_CHECKING:
    from archcheck.domain.model.class_ import Class
    from archcheck.domain.model.function import Function
    from archcheck.domain.model.function_edge import FunctionEdge
    from archcheck.domain.model.module import Module


def check_no_import(
    module: Module,
    patterns: tuple[CompiledPattern, ...],
) -> Violation | None:
    """Check that module doesn't import any pattern.

    Args:
        module: Module to check
        patterns: Forbidden import patterns

    Returns:
        First violation found, or None if no violation
    """
    for imp in module.imports:
        if matches_any(imp.module, patterns):
            return Violation(
                rule_name="no_import",
                message=f"module '{module.name}' imports forbidden '{imp.module}'",
                location=imp.location,
                severity=Severity.ERROR,
                category=RuleCategory.BOUNDARIES,
                subject=module.name,
                expected=f"no imports matching {', '.join(str(p) for p in patterns)}",
                actual=f"imports {imp.module}",
                suggestion=f"Remove import of {imp.module}",
            )
    return None


def check_only_import(
    module: Module,
    patterns: tuple[CompiledPattern, ...],
) -> Violation | None:
    """Check that module only imports from patterns.

    Args:
        module: Module to check
        patterns: Allowed import patterns

    Returns:
        First violation found, or None if all imports allowed
    """
    for imp in module.imports:
        if not matches_any(imp.module, patterns):
            return Violation(
                rule_name="only_import",
                message=f"module '{module.name}' imports non-allowed '{imp.module}'",
                location=imp.location,
                severity=Severity.ERROR,
                category=RuleCategory.BOUNDARIES,
                subject=module.name,
                expected=f"imports only from {', '.join(str(p) for p in patterns)}",
                actual=f"imports {imp.module}",
                suggestion=f"Remove import of {imp.module} or add to allowed list",
            )
    return None


def check_module_in_layer(
    module: Module,
    expected_layer: str,
) -> Violation | None:
    """Check that module is in expected layer.

    Args:
        module: Module to check
        expected_layer: Expected layer name

    Returns:
        Violation if module not in layer, None otherwise
    """
    actual_layer = get_layer(module.name)
    if actual_layer != expected_layer:
        return Violation(
            rule_name="be_in_layer",
            message=(
                f"module '{module.name}' is in layer '{actual_layer}', "
                f"expected '{expected_layer}'"
            ),
            location=Location(file=module.path, line=1, column=0),
            severity=Severity.ERROR,
            category=RuleCategory.BOUNDARIES,
            subject=module.name,
            expected=f"module in layer '{expected_layer}'",
            actual=f"module in layer '{actual_layer}'",
            suggestion=f"Move module to '{expected_layer}' layer",
        )
    return None


def make_no_import_check(
    patterns: tuple[CompiledPattern, ...],
) -> Callable[[Module], Violation | None]:
    """Create no_import check function with bound patterns.

    Args:
        patterns: Forbidden import patterns

    Returns:
        Check function that takes Module and returns Violation | None
    """
    def check(module: Module) -> Violation | None:
        return check_no_import(module, patterns)
    return check


def make_only_import_check(
    patterns: tuple[CompiledPattern, ...],
) -> Callable[[Module], Violation | None]:
    """Create only_import check function with bound patterns.

    Args:
        patterns: Allowed import patterns

    Returns:
        Check function that takes Module and returns Violation | None
    """
    def check(module: Module) -> Violation | None:
        return check_only_import(module, patterns)
    return check


def make_in_layer_check(
    layer: str,
) -> Callable[[Module], Violation | None]:
    """Create in_layer check function with bound layer.

    Args:
        layer: Expected layer name

    Returns:
        Check function that takes Module and returns Violation | None
    """
    def check(module: Module) -> Violation | None:
        return check_module_in_layer(module, layer)
    return check


# =============================================================================
# Class checks
# =============================================================================


def check_class_in_layer(
    cls: Class,
    expected_layer: str,
) -> Violation | None:
    """Check that class is in expected layer.

    Args:
        cls: Class to check
        expected_layer: Expected layer name

    Returns:
        Violation if class not in layer, None otherwise
    """
    actual_layer = get_layer(cls.qualified_name)
    if actual_layer != expected_layer:
        return Violation(
            rule_name="be_in_layer",
            message=(
                f"class '{cls.name}' is in layer '{actual_layer}', "
                f"expected '{expected_layer}'"
            ),
            location=cls.location,
            severity=Severity.ERROR,
            category=RuleCategory.BOUNDARIES,
            subject=cls.qualified_name,
            expected=f"class in layer '{expected_layer}'",
            actual=f"class in layer '{actual_layer}'",
            suggestion=f"Move class to '{expected_layer}' layer",
        )
    return None


def check_class_extends(
    cls: Class,
    base_pattern: CompiledPattern,
) -> Violation | None:
    """Check that class extends base matching pattern.

    Args:
        cls: Class to check
        base_pattern: Pattern for required base class

    Returns:
        Violation if class doesn't extend matching base, None otherwise
    """
    for base in cls.bases:
        if base_pattern.match(base):
            return None

    return Violation(
        rule_name="extend",
        message=f"class '{cls.name}' doesn't extend '{base_pattern}'",
        location=cls.location,
        severity=Severity.ERROR,
        category=RuleCategory.INHERITANCE,
        subject=cls.qualified_name,
        expected=f"extends class matching '{base_pattern}'",
        actual=f"bases: {', '.join(cls.bases) or 'none'}",
        suggestion=f"Add base class matching '{base_pattern}'",
    )


def check_class_implements(
    cls: Class,
    protocol_pattern: CompiledPattern,
) -> Violation | None:
    """Check that class implements protocol matching pattern.

    Args:
        cls: Class to check
        protocol_pattern: Pattern for required protocol

    Returns:
        Violation if class doesn't implement matching protocol, None otherwise
    """
    for base in cls.bases:
        if protocol_pattern.match(base):
            return None

    return Violation(
        rule_name="implement",
        message=f"class '{cls.name}' doesn't implement '{protocol_pattern}'",
        location=cls.location,
        severity=Severity.ERROR,
        category=RuleCategory.CONTRACTS,
        subject=cls.qualified_name,
        expected=f"implements protocol matching '{protocol_pattern}'",
        actual=f"bases: {', '.join(cls.bases) or 'none'}",
        suggestion=f"Implement protocol matching '{protocol_pattern}'",
    )


def check_class_max_methods(
    cls: Class,
    max_methods: int,
) -> Violation | None:
    """Check that class has at most max_methods public methods.

    Args:
        cls: Class to check
        max_methods: Maximum allowed public methods

    Returns:
        Violation if class has too many methods, None otherwise
    """
    from archcheck.domain.model.enums import Visibility

    public_methods = [m for m in cls.methods if m.visibility == Visibility.PUBLIC]
    count = len(public_methods)

    if count > max_methods:
        return Violation(
            rule_name="max_methods",
            message=f"class '{cls.name}' has {count} public methods, max {max_methods}",
            location=cls.location,
            severity=Severity.WARNING,
            category=RuleCategory.COHESION,
            subject=cls.qualified_name,
            expected=f"at most {max_methods} public methods",
            actual=f"{count} public methods",
            suggestion="Split class into smaller classes",
        )
    return None


def make_class_in_layer_check(
    layer: str,
) -> Callable[[Class], Violation | None]:
    """Create class in_layer check with bound layer."""
    def check(cls: Class) -> Violation | None:
        return check_class_in_layer(cls, layer)
    return check


def make_class_extends_check(
    pattern: CompiledPattern,
) -> Callable[[Class], Violation | None]:
    """Create class extends check with bound pattern."""
    def check(cls: Class) -> Violation | None:
        return check_class_extends(cls, pattern)
    return check


def make_class_implements_check(
    pattern: CompiledPattern,
) -> Callable[[Class], Violation | None]:
    """Create class implements check with bound pattern."""
    def check(cls: Class) -> Violation | None:
        return check_class_implements(cls, pattern)
    return check


def make_class_max_methods_check(
    max_methods: int,
) -> Callable[[Class], Violation | None]:
    """Create class max_methods check with bound limit."""
    def check(cls: Class) -> Violation | None:
        return check_class_max_methods(cls, max_methods)
    return check


# =============================================================================
# Function checks
# =============================================================================


def check_function_in_layer(
    func: Function,
    expected_layer: str,
) -> Violation | None:
    """Check that function is in expected layer.

    Args:
        func: Function to check
        expected_layer: Expected layer name

    Returns:
        Violation if function not in layer, None otherwise
    """
    actual_layer = get_layer(func.qualified_name)
    if actual_layer != expected_layer:
        return Violation(
            rule_name="be_in_layer",
            message=(
                f"function '{func.name}' is in layer '{actual_layer}', "
                f"expected '{expected_layer}'"
            ),
            location=func.location,
            severity=Severity.ERROR,
            category=RuleCategory.BOUNDARIES,
            subject=func.qualified_name,
            expected=f"function in layer '{expected_layer}'",
            actual=f"function in layer '{actual_layer}'",
            suggestion=f"Move function to '{expected_layer}' layer",
        )
    return None


def check_function_no_call(
    func: Function,
    patterns: tuple[CompiledPattern, ...],
) -> Violation | None:
    """Check that function doesn't call patterns.

    Args:
        func: Function to check
        patterns: Forbidden call patterns

    Returns:
        First violation found, or None if no violation
    """
    for call in func.body_calls:
        callee = call.resolved_fqn or call.callee_name
        if matches_any(callee, patterns):
            return Violation(
                rule_name="no_call",
                message=f"function '{func.name}' calls forbidden '{callee}'",
                location=func.location,
                severity=Severity.ERROR,
                category=RuleCategory.BOUNDARIES,
                subject=func.qualified_name,
                expected=f"no calls matching {', '.join(str(p) for p in patterns)}",
                actual=f"calls {callee}",
                suggestion=f"Remove call to {callee}",
            )
    return None


def check_function_only_call(
    func: Function,
    patterns: tuple[CompiledPattern, ...],
) -> Violation | None:
    """Check that function only calls patterns.

    Args:
        func: Function to check
        patterns: Allowed call patterns

    Returns:
        First violation found, or None if all calls allowed
    """
    for call in func.body_calls:
        callee = call.resolved_fqn or call.callee_name
        if not matches_any(callee, patterns):
            return Violation(
                rule_name="only_call",
                message=f"function '{func.name}' calls non-allowed '{callee}'",
                location=func.location,
                severity=Severity.ERROR,
                category=RuleCategory.BOUNDARIES,
                subject=func.qualified_name,
                expected=f"calls only {', '.join(str(p) for p in patterns)}",
                actual=f"calls {callee}",
                suggestion=f"Remove call to {callee} or add to allowed list",
            )
    return None


def make_function_in_layer_check(
    layer: str,
) -> Callable[[Function], Violation | None]:
    """Create function in_layer check with bound layer."""
    def check(func: Function) -> Violation | None:
        return check_function_in_layer(func, layer)
    return check


def make_function_no_call_check(
    patterns: tuple[CompiledPattern, ...],
) -> Callable[[Function], Violation | None]:
    """Create function no_call check with bound patterns."""
    def check(func: Function) -> Violation | None:
        return check_function_no_call(func, patterns)
    return check


def make_function_only_call_check(
    patterns: tuple[CompiledPattern, ...],
) -> Callable[[Function], Violation | None]:
    """Create function only_call check with bound patterns."""
    def check(func: Function) -> Violation | None:
        return check_function_only_call(func, patterns)
    return check


# =============================================================================
# Edge checks
# =============================================================================


def check_edge_not_cross_boundary(
    edge: FunctionEdge,
) -> Violation | None:
    """Check that edge doesn't cross layer boundary.

    Args:
        edge: FunctionEdge to check

    Returns:
        Violation if caller_layer != callee_layer, None otherwise
    """
    caller_layer = get_layer(edge.caller_fqn)
    callee_layer = get_layer(edge.callee_fqn)

    if caller_layer != callee_layer:
        return Violation(
            rule_name="not_cross_boundary",
            message=(
                f"edge '{edge.caller_fqn}' -> '{edge.callee_fqn}' "
                f"crosses boundary: {caller_layer} -> {callee_layer}"
            ),
            location=edge.first_location,
            severity=Severity.ERROR,
            category=RuleCategory.BOUNDARIES,
            subject=f"{edge.caller_fqn} -> {edge.callee_fqn}",
            expected="edge within same layer",
            actual=f"crosses from {caller_layer} to {callee_layer}",
            suggestion="Refactor to avoid cross-layer dependency",
        )
    return None


def check_edge_be_allowed(
    edge: FunctionEdge,
    allowed_imports: Mapping[str, frozenset[str]],
) -> Violation | None:
    """Check that edge is allowed by layer rules.

    Args:
        edge: FunctionEdge to check
        allowed_imports: Layer -> allowed target layers

    Returns:
        Violation if edge not allowed, None otherwise
    """
    caller_layer = get_layer(edge.caller_fqn)
    callee_layer = get_layer(edge.callee_fqn)

    # Same layer always allowed
    if caller_layer == callee_layer:
        return None

    # Check allowed_imports
    allowed = allowed_imports.get(caller_layer, frozenset())
    if callee_layer not in allowed:
        return Violation(
            rule_name="be_allowed",
            message=(
                f"edge '{edge.caller_fqn}' -> '{edge.callee_fqn}' "
                f"not allowed: {caller_layer} -> {callee_layer}"
            ),
            location=edge.first_location,
            severity=Severity.ERROR,
            category=RuleCategory.BOUNDARIES,
            subject=f"{edge.caller_fqn} -> {edge.callee_fqn}",
            expected=f"layer '{caller_layer}' may call: {allowed or 'none'}",
            actual=f"calls layer '{callee_layer}'",
            suggestion=f"Add '{callee_layer}' to allowed imports for '{caller_layer}'",
        )
    return None


def make_edge_not_cross_boundary_check() -> Callable[[FunctionEdge], Violation | None]:
    """Create edge not_cross_boundary check."""
    return check_edge_not_cross_boundary


def make_edge_be_allowed_check(
    allowed_imports: Mapping[str, frozenset[str]],
) -> Callable[[FunctionEdge], Violation | None]:
    """Create edge be_allowed check with bound config."""
    def check(edge: FunctionEdge) -> Violation | None:
        return check_edge_be_allowed(edge, allowed_imports)
    return check
