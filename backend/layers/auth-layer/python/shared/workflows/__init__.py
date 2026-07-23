"""Workflow framework — state machine engine for membership and order transitions.

Re-exports core types, engine, dispatcher, and audit.
"""

from shared.workflows.types import Transition, TransitionResult
from shared.workflows.engine import WorkflowEngine
from shared.workflows.dispatcher import ActionDispatcher
from shared.workflows.audit import write_workflow_audit

__all__ = [
    "Transition",
    "TransitionResult",
    "WorkflowEngine",
    "ActionDispatcher",
    "write_workflow_audit",
]
