"""Function parameter value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Parameter:
    """Function/method parameter.

    Attributes:
        name: Parameter name
        annotation: Type annotation as string, None if untyped
        default: Default value as string, None if required
        is_positional_only: Before / in signature
        is_keyword_only: After * in signature
        is_variadic: *args parameter
        is_variadic_keyword: **kwargs parameter
    """

    name: str
    annotation: str | None = None
    default: str | None = None
    is_positional_only: bool = False
    is_keyword_only: bool = False
    is_variadic: bool = False
    is_variadic_keyword: bool = False

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("parameter name must not be empty")

        if self.is_variadic and self.is_variadic_keyword:
            raise ValueError("parameter cannot be both *args and **kwargs")

        if self.is_positional_only and self.is_keyword_only:
            raise ValueError("parameter cannot be both positional-only and keyword-only")

        if self.is_variadic and (self.is_positional_only or self.is_keyword_only):
            raise ValueError("*args cannot be positional-only or keyword-only")

        if self.is_variadic_keyword and (self.is_positional_only or self.is_keyword_only):
            raise ValueError("**kwargs cannot be positional-only or keyword-only")
