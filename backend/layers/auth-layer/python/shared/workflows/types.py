"""Core types for the workflow framework.

Provides the Transition definition (TypedDict) and TransitionResult dataclass
used throughout the workflow engine.
"""

from dataclasses import dataclass, field
from typing import TypedDict, Callable, NotRequired


class Transition(TypedDict):
    """A single workflow transition definition.

    Defines what event triggers a state change, optional guard conditions,
    mandatory actions (must all succeed), and best-effort side effects.
    """

    from_state: str
    to_state: str
    event: str
    guard: NotRequired[Callable[[dict], bool] | None]
    actions: list[str]          # MUST all succeed — rollback if any fails
    side_effects: list[str]     # Best-effort — failures logged, don't block transition


@dataclass
class TransitionResult:
    """Rich result object from a workflow transition attempt."""

    success: bool
    old_state: str
    new_state: str | None
    event: str
    actions_executed: list[str] = field(default_factory=list)
    side_effects_executed: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    error: str | None = None
