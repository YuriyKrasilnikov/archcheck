"""Check statistics for architecture analysis results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckStats:
    """Statistics from architecture check.

    Immutable value object tracking analysis metrics.

    Attributes:
        modules_analyzed: Number of modules analyzed
        functions_analyzed: Number of functions analyzed
        classes_analyzed: Number of classes analyzed
        edges_analyzed: Number of call graph edges analyzed
        validators_run: Number of validators executed
        visitors_run: Number of visitors executed
        analysis_time_ms: Total analysis time in milliseconds
    """

    modules_analyzed: int
    functions_analyzed: int
    classes_analyzed: int
    edges_analyzed: int
    validators_run: int
    visitors_run: int
    analysis_time_ms: float

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if self.modules_analyzed < 0:
            raise ValueError(f"modules_analyzed must be >= 0, got {self.modules_analyzed}")
        if self.functions_analyzed < 0:
            raise ValueError(f"functions_analyzed must be >= 0, got {self.functions_analyzed}")
        if self.classes_analyzed < 0:
            raise ValueError(f"classes_analyzed must be >= 0, got {self.classes_analyzed}")
        if self.edges_analyzed < 0:
            raise ValueError(f"edges_analyzed must be >= 0, got {self.edges_analyzed}")
        if self.validators_run < 0:
            raise ValueError(f"validators_run must be >= 0, got {self.validators_run}")
        if self.visitors_run < 0:
            raise ValueError(f"visitors_run must be >= 0, got {self.visitors_run}")
        if self.analysis_time_ms < 0:
            raise ValueError(f"analysis_time_ms must be >= 0, got {self.analysis_time_ms}")

    @classmethod
    def empty(cls) -> CheckStats:
        """Create empty check stats."""
        return cls(
            modules_analyzed=0,
            functions_analyzed=0,
            classes_analyzed=0,
            edges_analyzed=0,
            validators_run=0,
            visitors_run=0,
            analysis_time_ms=0.0,
        )
