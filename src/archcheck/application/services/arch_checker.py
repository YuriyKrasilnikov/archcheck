"""Main facade for architecture checking.

ArchChecker is the primary entry point for running architecture analysis.
Composition-based: accepts validators and reporter.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Self

from archcheck.application.validators import default_validators, validators_from_config
from archcheck.domain.model.check_result import CheckResult
from archcheck.domain.model.check_stats import CheckStats
from archcheck.domain.model.configuration import ArchitectureConfig
from archcheck.domain.model.coverage_report import CoverageReport
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.domain.model.violation import Violation
from archcheck.domain.ports.reporter import ReporterProtocol
from archcheck.domain.ports.validator import ValidatorProtocol

if TYPE_CHECKING:
    from archcheck.domain.model.codebase import Codebase


class ArchChecker:
    """Main facade for architecture checking.

    Composition-based: accepts validators and reporter as dependencies.
    Runs validators against MergedCallGraph and produces CheckResult.

    Factory methods:
    - with_defaults(): Default validators (cycle detection)
    - from_config(): Validators based on ArchitectureConfig

    Example:
        codebase = parser.parse_directory(Path("src/myapp"), "myapp")
        checker = ArchChecker.with_defaults(codebase)
        result = checker.check()
        if not result.passed:
            print(f"Violations: {result.violation_count}")
    """

    def __init__(
        self,
        codebase: Codebase,
        merged_graph: MergedCallGraph,
        *,
        validators: Sequence[ValidatorProtocol] = (),
        reporter: ReporterProtocol | None = None,
    ) -> None:
        """Initialize checker with dependencies.

        Args:
            codebase: Parsed codebase
            merged_graph: Merged AST + Runtime call graph
            validators: Validators to run
            reporter: Optional reporter for output
        """
        self._codebase = codebase
        self._merged_graph = merged_graph
        self._validators = tuple(validators)
        self._reporter = reporter

    @classmethod
    def with_defaults(
        cls,
        codebase: Codebase,
        merged_graph: MergedCallGraph,
        *,
        reporter: ReporterProtocol | None = None,
    ) -> Self:
        """Create checker with default validators.

        Uses default validators (cycle detection only).

        Args:
            codebase: Parsed codebase
            merged_graph: Merged call graph
            reporter: Optional reporter

        Returns:
            ArchChecker with default validators
        """
        return cls(
            codebase,
            merged_graph,
            validators=default_validators(),
            reporter=reporter,
        )

    @classmethod
    def from_config(
        cls,
        codebase: Codebase,
        merged_graph: MergedCallGraph,
        config: ArchitectureConfig,
        *,
        registry: object | None = None,
        reporter: ReporterProtocol | None = None,
    ) -> Self:
        """Create checker with validators based on config.

        Validators are enabled/disabled based on config fields.

        Args:
            codebase: Parsed codebase
            merged_graph: Merged call graph
            config: Architecture configuration
            registry: Optional StaticAnalysisRegistry for DI-aware validation
            reporter: Optional reporter

        Returns:
            ArchChecker with config-based validators
        """
        return cls(
            codebase,
            merged_graph,
            validators=validators_from_config(config, registry),
            reporter=reporter,
        )

    def check(self, config: ArchitectureConfig | None = None) -> CheckResult:
        """Run architecture check and return result.

        Executes all validators against the merged graph.
        Reports result if reporter is configured.

        Args:
            config: Optional config override (uses empty config if None)

        Returns:
            CheckResult with violations, coverage, and stats
        """
        start_time = time.perf_counter()

        config = config or ArchitectureConfig()

        # Run validators
        all_violations = self._run_validators(config)

        # Build coverage report
        coverage = self._build_coverage()

        # Build stats
        end_time = time.perf_counter()
        stats = self._build_stats(end_time - start_time)

        # Create result
        result = CheckResult(
            violations=all_violations,
            coverage=coverage,
            merged_graph=self._merged_graph,
            stats=stats,
        )

        # Report if reporter configured
        if self._reporter is not None:
            self._reporter.report(result)

        return result

    def _run_validators(
        self,
        config: ArchitectureConfig,
    ) -> tuple[Violation, ...]:
        """Run all validators and collect violations.

        Args:
            config: Architecture configuration

        Returns:
            Tuple of all violations from all validators
        """
        all_violations: list[Violation] = []

        for validator in self._validators:
            violations = validator.validate(self._merged_graph, config)
            all_violations.extend(violations)

        return tuple(all_violations)

    def _build_coverage(self) -> CoverageReport:
        """Build coverage report from merged graph.

        Returns:
            CoverageReport (empty for now - full implementation in Phase 4)
        """
        # TODO: Implement proper coverage analysis in Phase 4
        return CoverageReport.empty()

    def _build_stats(self, analysis_time_s: float) -> CheckStats:
        """Build check statistics.

        Args:
            analysis_time_s: Analysis time in seconds

        Returns:
            CheckStats with analysis metrics
        """
        return CheckStats(
            modules_analyzed=len(self._codebase.modules),
            functions_analyzed=sum(len(m.functions) for m in self._codebase.modules.values()),
            classes_analyzed=sum(len(m.classes) for m in self._codebase.modules.values()),
            edges_analyzed=self._merged_graph.edge_count,
            validators_run=len(self._validators),
            visitors_run=0,  # No visitors in Phase 3
            analysis_time_ms=analysis_time_s * 1000,
        )

    @property
    def validator_count(self) -> int:
        """Number of configured validators."""
        return len(self._validators)
