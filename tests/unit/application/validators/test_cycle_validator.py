"""Tests for validators/cycle_validator.py."""

from archcheck.application.validators.cycle_validator import CycleValidator
from archcheck.domain.model.configuration import ArchitectureConfig
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from tests.factories import make_merged_graph


class TestCycleValidatorFromConfig:
    """Tests for CycleValidator.from_config."""

    def test_always_enabled(self) -> None:
        """CycleValidator is always enabled regardless of config."""
        config = ArchitectureConfig()

        result = CycleValidator.from_config(config)

        assert result is not None
        assert isinstance(result, CycleValidator)


class TestCycleValidatorValidate:
    """Tests for CycleValidator.validate."""

    def test_no_cycles_no_violations(self) -> None:
        """Graph with no cycles produces no violations."""
        graph = make_merged_graph(
            internal_edges={("a.a", "b.b"): 1, ("b.b", "c.c"): 1},  # a → b → c (no cycle)
        )
        config = ArchitectureConfig()
        validator = CycleValidator()

        result = validator.validate(graph, config)

        assert result == ()

    def test_simple_cycle_produces_violation(self) -> None:
        """Graph with cycle produces violation."""
        graph = make_merged_graph(
            internal_edges={("a.a", "b.b"): 1, ("b.b", "a.a"): 1},  # a → b → a (cycle!)
        )
        config = ArchitectureConfig()
        validator = CycleValidator()

        result = validator.validate(graph, config)

        assert len(result) == 1
        assert "circular" in result[0].message.lower()

    def test_empty_graph_no_violations(self) -> None:
        """Empty graph produces no violations."""
        graph = MergedCallGraph.empty()
        config = ArchitectureConfig()
        validator = CycleValidator()

        result = validator.validate(graph, config)

        assert result == ()

    def test_larger_cycle(self) -> None:
        """Detects cycles with more than 2 nodes."""
        graph = make_merged_graph(
            internal_edges={
                ("a.a", "b.b"): 1,
                ("b.b", "c.c"): 1,
                ("c.c", "a.a"): 1,  # a → b → c → a (3-node cycle)
            },
        )
        config = ArchitectureConfig()
        validator = CycleValidator()

        result = validator.validate(graph, config)

        assert len(result) == 1
