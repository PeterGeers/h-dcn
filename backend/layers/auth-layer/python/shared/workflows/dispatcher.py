"""Action dispatcher for workflow transitions.

Executes mandatory actions and best-effort side effects for state transitions.
Mandatory actions must all succeed — if any fails, the transition is rolled back.
Side effect failures are logged but don't invalidate the transition.
"""

import logging
from typing import Callable

from .types import Transition, TransitionResult

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """
    Executes workflow actions with mandatory/optional distinction.

    Mandatory actions (Transition.actions): ALL must succeed.
    If any fails, the transition should be rolled back.

    Side effects (Transition.side_effects): best-effort.
    Failures are logged but don't invalidate the transition.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Callable[[dict], None]] = {}

    def register(self, name: str, fn: Callable[[dict], None]) -> None:
        """Register a named action function."""
        self._registry[name] = fn

    def register_many(self, actions: dict[str, Callable[[dict], None]]) -> None:
        """Register multiple actions at once."""
        self._registry.update(actions)

    def execute_transition(
        self, transition: Transition, result: TransitionResult, context: dict
    ) -> TransitionResult:
        """
        Execute all actions for a transition. Updates the result in-place.

        Flow:
        1. Run mandatory actions sequentially
        2. If ANY mandatory action fails → stop, set success=False, skip side effects
        3. If all mandatory actions succeed → run side effects (best-effort)
        4. Side effect failures are logged but don't affect result.success
        """
        # Execute mandatory actions
        for action_name in transition['actions']:
            if action_name not in self._registry:
                result.success = False
                result.new_state = None
                result.failures.append(f"Unknown mandatory action: {action_name}")
                result.error = f"Mandatory action '{action_name}' not registered"
                return result

            try:
                self._registry[action_name](context)
                result.actions_executed.append(action_name)
            except Exception as e:
                logger.error(f"Mandatory action '{action_name}' failed: {e}")
                result.success = False
                result.new_state = None
                result.failures.append(f"{action_name}: {e}")
                result.error = f"Mandatory action '{action_name}' failed: {e}"
                return result  # Stop — don't run side effects

        # Execute side effects (best-effort)
        for effect_name in transition.get('side_effects', []):
            if effect_name not in self._registry:
                result.failures.append(f"Unknown side effect: {effect_name}")
                logger.warning(f"Side effect '{effect_name}' not registered, skipping")
                continue

            try:
                self._registry[effect_name](context)
                result.side_effects_executed.append(effect_name)
            except Exception as e:
                logger.warning(f"Side effect '{effect_name}' failed (non-blocking): {e}")
                result.failures.append(f"{effect_name}: {e}")

        return result
