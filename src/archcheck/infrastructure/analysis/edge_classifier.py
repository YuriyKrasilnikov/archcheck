"""Edge nature classifier for call graph analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.edge_nature import EdgeNature

if TYPE_CHECKING:
    from collections.abc import Mapping


class EdgeClassifier:
    """Classifies edge nature based on static and runtime information.

    Stateless classifier. Determines EdgeNature for each edge:
    - DIRECT: caller imports callee's module
    - PARAMETRIC: caller doesn't import callee (passed as parameter)
    - INHERITED: super() call
    - FRAMEWORK: framework code calling app code

    Usage:
        classifier = EdgeClassifier(module_imports, config.known_frameworks or frozenset())
        nature = classifier.classify("app.service.run", "app.repo.save", CallType.METHOD)
    """

    def __init__(
        self,
        module_imports: Mapping[str, frozenset[str]],
        known_frameworks: frozenset[str],
    ) -> None:
        """Initialize classifier.

        Args:
            module_imports: Mapping from module FQN to set of imported module FQNs
            known_frameworks: Set of known framework package prefixes (from config)

        Raises:
            TypeError: If module_imports or known_frameworks is None (FAIL-FIRST)
        """
        if module_imports is None:
            raise TypeError("module_imports must not be None")
        if known_frameworks is None:
            raise TypeError("known_frameworks must not be None")

        self._imports = module_imports
        self._frameworks = known_frameworks

    def classify(
        self,
        caller_fqn: str,
        callee_fqn: str,
        call_type: CallType,
    ) -> EdgeNature:
        """Classify edge nature.

        Algorithm:
        1. super() call → INHERITED
        2. caller is framework → FRAMEWORK
        3. callee's module in caller's imports → DIRECT
        4. otherwise → PARAMETRIC

        Args:
            caller_fqn: Fully qualified name of caller
            callee_fqn: Fully qualified name of callee
            call_type: How the call was made

        Returns:
            EdgeNature classification
        """
        # 1. super() call
        if call_type == CallType.SUPER:
            return EdgeNature.INHERITED

        # 2. Framework calling application
        caller_module = self._get_module(caller_fqn)
        if self._is_framework(caller_module):
            return EdgeNature.FRAMEWORK

        # 3. Direct import exists
        callee_module = self._get_module(callee_fqn)
        caller_imports = self._imports.get(caller_module, frozenset())

        if self._is_imported(callee_module, caller_imports):
            return EdgeNature.DIRECT

        # 4. Parametric (no import, but runtime edge exists)
        return EdgeNature.PARAMETRIC

    def _get_module(self, fqn: str) -> str:
        """Extract module from FQN.

        myapp.domain.User.method → myapp.domain
        myapp.utils.helper → myapp.utils
        myapp.main → myapp

        Heuristic: split by '.', find last lowercase part as module end.
        """
        parts = fqn.split(".")

        # Find module boundary (classes/functions start with uppercase or are after module)
        # Simplified: take all parts up to and including the first file-level identifier
        # A module path ends at the first CamelCase or the last part before function name

        # Better heuristic: module is typically the first N parts where N is depth
        # For "myapp.domain.User.method": module is "myapp.domain"
        # For "myapp.utils.helper": module is "myapp.utils"

        # Find first uppercase component (likely class name)
        for i, part in enumerate(parts):
            if part and part[0].isupper():
                # This is likely a class, module is parts before it
                return ".".join(parts[:i]) if i > 0 else parts[0]

        # No uppercase found - might be all lowercase function path
        # Module is all but last part (function name)
        if len(parts) > 1:
            return ".".join(parts[:-1])

        return parts[0]

    def _is_framework(self, module: str) -> bool:
        """Check if module is a known framework."""
        for fw in self._frameworks:
            if module == fw or module.startswith(fw + "."):
                return True
        return False

    def _is_imported(
        self,
        callee_module: str,
        caller_imports: frozenset[str],
    ) -> bool:
        """Check if callee's module is imported by caller.

        Handles package imports: if caller imports "myapp.domain",
        then "myapp.domain.user" is considered imported.

        Args:
            callee_module: Module of callee function
            caller_imports: Set of modules imported by caller

        Returns:
            True if callee_module is reachable through caller's imports
        """
        if callee_module in caller_imports:
            return True

        # Check if any import is a parent package of callee_module
        for imp in caller_imports:
            if callee_module.startswith(imp + "."):
                return True

        return False
