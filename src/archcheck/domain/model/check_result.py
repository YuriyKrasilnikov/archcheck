"""Check result aggregate for architecture analysis."""

from dataclasses import dataclass

from archcheck.domain.model.check_stats import CheckStats
from archcheck.domain.model.coverage_report import CoverageReport
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.domain.model.violation import Violation


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of architecture check.

    Immutable aggregate containing all analysis results.
    Used by ReporterProtocol.report() method.

    Attributes:
        violations: All violations found
        coverage: Coverage analysis report
        merged_graph: Merged AST + Runtime call graph
        stats: Analysis statistics
    """

    violations: tuple[Violation, ...]
    coverage: CoverageReport
    merged_graph: MergedCallGraph
    stats: CheckStats

    @property
    def passed(self) -> bool:
        """Check if analysis passed (no violations)."""
        return len(self.violations) == 0

    @property
    def violation_count(self) -> int:
        """Number of violations."""
        return len(self.violations)

    @property
    def error_count(self) -> int:
        """Number of ERROR severity violations."""
        from archcheck.domain.model.enums import Severity

        return sum(1 for v in self.violations if v.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        """Number of WARNING severity violations."""
        from archcheck.domain.model.enums import Severity

        return sum(1 for v in self.violations if v.severity == Severity.WARNING)

    @classmethod
    def empty(cls) -> CheckResult:
        """Create empty check result (passed, no violations)."""
        return cls(
            violations=(),
            coverage=CoverageReport.empty(),
            merged_graph=MergedCallGraph.empty(),
            stats=CheckStats.empty(),
        )
