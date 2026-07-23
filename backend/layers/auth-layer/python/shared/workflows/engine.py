"""Lightweight state machine engine. No dependencies, no magic.

The engine evaluates transitions and returns results. It does NOT execute
actions, persist state, or interact with any external services.

CRITICAL: This module MUST NOT import any AWS SDK modules (boto3, botocore, aws_*).
"""

import logging
from .types import Transition, TransitionResult

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Lightweight state machine engine. No dependencies, no magic."""

    def __init__(self, transitions: list[Transition]):
        self._transitions = transitions

    def get_allowed_events(self, current_state: str) -> list[str]:
        """Return all events that are valid from the current state.

        Never raises — returns empty list on any error.
        """
        try:
            return list({
                t['event'] for t in self._transitions
                if t['from_state'] == current_state
            })
        except Exception as e:
            logger.error(f"Error in get_allowed_events: {e}")
            return []

    def can_transition(
        self, current_state: str, event: str, context: dict | None = None
    ) -> Transition | None:
        """Check if a transition is allowed. Returns the transition or None.

        Never raises — returns None on any error (including guard exceptions).
        """
        try:
            context = context or {}
            for t in self._transitions:
                if t['from_state'] == current_state and t['event'] == event:
                    guard = t.get('guard')
                    if guard is None:
                        return t
                    try:
                        if guard(context):
                            return t
                    except Exception as e:
                        logger.warning(
                            f"Guard failed for transition '{event}' "
                            f"from '{current_state}': {e}"
                        )
                        continue
            return None
        except Exception as e:
            logger.error(f"Error in can_transition: {e}")
            return None

    def execute(
        self, current_state: str, event: str, context: dict | None = None
    ) -> TransitionResult:
        """Attempt a state transition.

        Returns a TransitionResult with full details about what happened.
        The engine only evaluates — it does NOT execute actions or persist state.

        CRITICAL: This method NEVER raises exceptions. Any internal error
        is caught and returned as success=False with an error message.
        """
        try:
            context = context or {}
            transition = self.can_transition(current_state, event, context)

            if not transition:
                return TransitionResult(
                    success=False,
                    old_state=current_state,
                    new_state=None,
                    event=event,
                    error=f"Transition '{event}' not allowed from state '{current_state}'",
                )

            return TransitionResult(
                success=True,
                old_state=current_state,
                new_state=transition['to_state'],
                event=event,
            )
        except Exception as e:
            logger.error(f"Unexpected error in execute: {e}")
            return TransitionResult(
                success=False,
                old_state=current_state,
                new_state=None,
                event=event,
                error=f"Internal engine error: {e}",
            )
