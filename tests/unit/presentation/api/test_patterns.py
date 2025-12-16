"""Tests for presentation/api/patterns.py."""

import pytest

from archcheck.presentation.api.patterns import (
    CompiledPattern,
    compile_pattern,
    matches_all,
    matches_any,
)


class TestCompilePatternFailFirst:
    """FAIL-FIRST validation tests."""

    def test_empty_pattern_raises(self) -> None:
        """Empty pattern raises ValueError."""
        with pytest.raises(ValueError, match="pattern must not be empty"):
            compile_pattern("")


class TestCompilePatternBasic:
    """Basic pattern compilation tests."""

    def test_exact_match(self) -> None:
        """Exact pattern matches only exact string."""
        p = compile_pattern("foo.bar")
        assert p.match("foo.bar")
        assert not p.match("foo.bar.baz")
        assert not p.match("foo")
        assert not p.match("xfoo.bar")

    def test_returns_compiled_pattern(self) -> None:
        """compile_pattern returns CompiledPattern instance."""
        result = compile_pattern("foo")
        assert isinstance(result, CompiledPattern)

    def test_original_preserved(self) -> None:
        """CompiledPattern preserves original pattern."""
        p = compile_pattern("foo.**")
        assert p.original == "foo.**"


class TestPatternSingleStar:
    """Tests for * (single segment) pattern."""

    def test_star_matches_one_segment(self) -> None:
        """* matches exactly one segment (no dots)."""
        p = compile_pattern("foo.*")
        assert p.match("foo.bar")
        assert p.match("foo.baz")
        assert not p.match("foo.bar.baz")  # Two segments after foo
        assert not p.match("foo")  # No segment after foo

    def test_star_in_middle(self) -> None:
        """* in middle matches one segment."""
        p = compile_pattern("foo.*.bar")
        assert p.match("foo.x.bar")
        assert p.match("foo.anything.bar")
        assert not p.match("foo.x.y.bar")  # Two segments
        assert not p.match("foo.bar")  # No segment

    def test_star_at_start(self) -> None:
        """* at start matches one segment."""
        p = compile_pattern("*.bar")
        assert p.match("foo.bar")
        assert p.match("x.bar")
        assert not p.match("foo.x.bar")
        assert not p.match("bar")

    def test_multiple_stars(self) -> None:
        """Multiple * each match one segment."""
        p = compile_pattern("*.*.*")
        assert p.match("a.b.c")
        assert not p.match("a.b")
        assert not p.match("a.b.c.d")


class TestPatternDoubleStar:
    """Tests for ** (any segments) pattern."""

    def test_double_star_alone(self) -> None:
        """** alone matches anything."""
        p = compile_pattern("**")
        assert p.match("")
        assert p.match("foo")
        assert p.match("foo.bar")
        assert p.match("foo.bar.baz.qux")

    def test_double_star_in_middle(self) -> None:
        """** in middle matches any number of segments."""
        p = compile_pattern("foo.**.bar")
        assert p.match("foo.bar")  # Zero segments
        assert p.match("foo.x.bar")  # One segment
        assert p.match("foo.x.y.bar")  # Two segments
        assert p.match("foo.x.y.z.bar")  # Three segments
        assert not p.match("foo.barbaz")  # No dot before bar
        assert not p.match("xfoo.bar")  # Wrong prefix


class TestPatternTrailingDoubleStar:
    """Tests for trailing .** (this AND children)."""

    def test_trailing_double_star_matches_parent(self) -> None:
        """foo.** matches foo itself."""
        p = compile_pattern("foo.**")
        assert p.match("foo")

    def test_trailing_double_star_matches_children(self) -> None:
        """foo.** matches all children."""
        p = compile_pattern("foo.**")
        assert p.match("foo.bar")
        assert p.match("foo.bar.baz")
        assert p.match("foo.a.b.c.d")

    def test_trailing_double_star_no_false_positives(self) -> None:
        """foo.** doesn't match unrelated modules."""
        p = compile_pattern("foo.**")
        assert not p.match("foobar")  # No dot
        assert not p.match("bar.foo")  # Different prefix
        assert not p.match("xfoo.bar")  # Wrong prefix

    def test_nested_trailing_double_star(self) -> None:
        """myapp.domain.** matches domain and children."""
        p = compile_pattern("myapp.domain.**")
        assert p.match("myapp.domain")
        assert p.match("myapp.domain.user")
        assert p.match("myapp.domain.user.models")
        assert not p.match("myapp.domainx")
        assert not p.match("myapp")


class TestPatternLeadingDoubleStar:
    """Tests for leading **. (any prefix)."""

    def test_leading_double_star_matches_target(self) -> None:
        """**.foo matches foo itself."""
        p = compile_pattern("**.foo")
        assert p.match("foo")

    def test_leading_double_star_matches_prefixed(self) -> None:
        """**.foo matches any prefix + foo."""
        p = compile_pattern("**.foo")
        assert p.match("bar.foo")
        assert p.match("bar.baz.foo")
        assert p.match("a.b.c.foo")

    def test_leading_double_star_no_false_positives(self) -> None:
        """**.foo doesn't match foo with suffix."""
        p = compile_pattern("**.foo")
        assert not p.match("foobar")
        assert not p.match("foo.bar")
        assert not p.match("bar.foobar")


class TestPatternQuestionMark:
    """Tests for ? (single character) pattern."""

    def test_question_matches_one_char(self) -> None:
        """? matches exactly one character."""
        p = compile_pattern("fo?")
        assert p.match("foo")
        assert p.match("for")
        assert not p.match("fo")
        assert not p.match("fooo")

    def test_question_in_segment(self) -> None:
        """? in segment matches one char."""
        p = compile_pattern("f?o.bar")
        assert p.match("foo.bar")
        assert p.match("fxo.bar")
        assert not p.match("fo.bar")
        assert not p.match("fxxo.bar")


class TestPatternCombinations:
    """Tests for combined patterns."""

    def test_star_and_double_star(self) -> None:
        """Combining * and ** in one pattern."""
        p = compile_pattern("*.**.bar")
        assert p.match("foo.bar")
        assert p.match("foo.x.bar")
        assert p.match("foo.x.y.bar")
        assert not p.match("bar")  # Missing first segment

    def test_question_and_star(self) -> None:
        """Combining ? and * in one pattern."""
        p = compile_pattern("f?o.*")
        assert p.match("foo.bar")
        assert p.match("fao.baz")
        assert not p.match("fooo.bar")

    def test_real_world_infrastructure(self) -> None:
        """Real-world: infrastructure.** pattern."""
        p = compile_pattern("myapp.infrastructure.**")
        assert p.match("myapp.infrastructure")
        assert p.match("myapp.infrastructure.db")
        assert p.match("myapp.infrastructure.db.models")
        assert p.match("myapp.infrastructure.http.client")
        assert not p.match("myapp.domain")
        assert not p.match("myapp.infrastructurex")

    def test_real_world_repository_suffix(self) -> None:
        """Real-world: *Repository pattern."""
        p = compile_pattern("*Repository")
        assert p.match("UserRepository")
        assert p.match("OrderRepository")
        assert not p.match("Repository")  # * needs at least one char
        assert not p.match("UserRepositoryImpl")


class TestCompiledPatternMethods:
    """Tests for CompiledPattern methods."""

    def test_match_none_raises(self) -> None:
        """match(None) raises TypeError."""
        p = compile_pattern("foo")
        with pytest.raises(TypeError, match="name must not be None"):
            p.match(None)  # type: ignore[arg-type]

    def test_str_returns_original(self) -> None:
        """str() returns original pattern."""
        p = compile_pattern("foo.**")
        assert str(p) == "foo.**"

    def test_repr_includes_original(self) -> None:
        """repr() includes original pattern."""
        p = compile_pattern("foo.**")
        assert repr(p) == "CompiledPattern('foo.**')"


class TestMatchesAny:
    """Tests for matches_any helper."""

    def test_matches_any_true(self) -> None:
        """Returns True if any pattern matches."""
        patterns = (compile_pattern("foo"), compile_pattern("bar"))
        assert matches_any("foo", patterns)
        assert matches_any("bar", patterns)

    def test_matches_any_false(self) -> None:
        """Returns False if no pattern matches."""
        patterns = (compile_pattern("foo"), compile_pattern("bar"))
        assert not matches_any("baz", patterns)

    def test_matches_any_empty(self) -> None:
        """Empty patterns returns False."""
        assert not matches_any("foo", ())


class TestMatchesAll:
    """Tests for matches_all helper."""

    def test_matches_all_true(self) -> None:
        """Returns True if all patterns match."""
        patterns = (compile_pattern("foo.**"), compile_pattern("**.bar"))
        assert matches_all("foo.bar", patterns)

    def test_matches_all_false(self) -> None:
        """Returns False if any pattern doesn't match."""
        patterns = (compile_pattern("foo"), compile_pattern("bar"))
        assert not matches_all("foo", patterns)

    def test_matches_all_empty(self) -> None:
        """Empty patterns returns True (vacuous truth)."""
        assert matches_all("anything", ())
