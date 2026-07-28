/**
 * Workflow Configuration System — Type Definitions
 *
 * Compile-time types for the membership workflow state machine.
 * These mirror the backend workflow engine definitions but serve as
 * the frontend's source of truth for rendering transitions and buttons.
 */

// ============================================================================
// STATE & EVENT TYPES
// ============================================================================

/**
 * All possible states in the membership workflow.
 * Maps to DynamoDB status values via STATUS_TO_STATE / STATE_TO_STATUS.
 */
export type MemberWorkflowState =
  | 'draft'
  | 'applied'
  | 'pending'
  | 'wait_payment'
  | 'active'
  | 'cancelled'
  | 'suspended';

/**
 * All possible events that can trigger a state transition.
 */
export type MemberWorkflowEvent =
  | 'APPROVE'
  | 'PAYMENT_RECEIVED'
  | 'CANCEL'
  | 'SUSPEND'
  | 'REACTIVATE';

// ============================================================================
// TRANSITION CONFIGURATION
// ============================================================================

/**
 * Describes a single transition that can be triggered from a given state.
 */
export interface TransitionConfig {
  /** The event that triggers this transition */
  event: MemberWorkflowEvent;

  /** The target state after the transition completes */
  target: MemberWorkflowState;

  /** i18n key for the action button label (e.g. 'workflows.membership.approve') */
  label: string;

  /** Cognito roles that are allowed to execute this transition */
  actors: string[];

  /** Fields that must be provided or already filled before executing (e.g. ['reason']) */
  requiredFields?: string[];

  /** i18n key for the confirmation dialog message */
  confirmMessage: string;

  /** i18n key describing what happens when this transition executes */
  description: string;
}

// ============================================================================
// WORKFLOW DEFINITION
// ============================================================================

/**
 * Configuration for a single workflow state, listing its outgoing transitions.
 */
export interface StateConfig {
  transitions: TransitionConfig[];
}

/**
 * Complete workflow definition mapping every state to its available transitions.
 */
export interface WorkflowDefinition {
  states: Record<MemberWorkflowState, StateConfig>;
}
