"""Filter type alias.

Python 3.14 PEP 695 type alias syntax.
Filter function: takes Event, returns True to include.
"""

from collections.abc import Callable

from archcheck.domain.events import Event

type Filter = Callable[[Event], bool]
