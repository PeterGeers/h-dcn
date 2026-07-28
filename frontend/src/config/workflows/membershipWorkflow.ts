/**
 * Membership Workflow Configuration
 *
 * Defines the complete membership lifecycle state machine for the frontend.
 * Mirrors the backend workflow engine (backend/layers/auth-layer/python/shared/workflows/membership.py)
 * but the backend remains the authority — this config drives UI rendering only.
 *
 * Validates: Requirements 6.1, 6.3
 */

import type { MemberWorkflowState, TransitionConfig, WorkflowDefinition } from './types';

// ============================================================================
// STATUS ↔ STATE MAPPINGS
// ============================================================================

/**
 * Maps DynamoDB status values (Dutch) to workflow engine states (English).
 * Used when reading a member record to determine the current workflow state.
 */
export const STATUS_TO_STATE: Record<string, MemberWorkflowState> = {
  Aangemeld: 'applied',
  wachtRegio: 'pending',
  wachtBetaling: 'wait_payment',
  Actief: 'active',
  Opgezegd: 'cancelled',
  Geschorst: 'suspended',
};

/**
 * Maps workflow engine states back to DynamoDB status values.
 * Used when displaying the status in DynamoDB terminology.
 */
export const STATE_TO_STATUS: Record<MemberWorkflowState, string> = {
  applied: 'Aangemeld',
  pending: 'wachtRegio',
  wait_payment: 'wachtBetaling',
  active: 'Actief',
  cancelled: 'Opgezegd',
  suspended: 'Geschorst',
};

// ============================================================================
// MEMBER STATES
// ============================================================================

/**
 * Ordered list of all workflow states in lifecycle order.
 */
export const MEMBER_STATES: readonly MemberWorkflowState[] = [
  'draft',
  'applied',
  'pending',
  'wait_payment',
  'active',
  'cancelled',
  'suspended',
];

// ============================================================================
// TRANSITION DEFINITIONS
// ============================================================================

/**
 * Transitions available from the 'draft' state.
 * SUBMIT moves to 'applied' (application formally submitted).
 * Only verzoek_lid users can execute this on their own record.
 */
const draftTransitions: TransitionConfig[] = [
  {
    event: 'SUBMIT',
    target: 'applied',
    label: 'workflows.membership.submit',
    actors: ['verzoek_lid'],
    confirmMessage: 'workflows.membership.confirm.submit',
    description: 'workflows.membership.description.submit',
  },
];

/**
 * Transitions available from the 'applied' state.
 * APPROVE moves to 'pending' (awaiting region assignment).
 */
const appliedTransitions: TransitionConfig[] = [
  {
    event: 'APPROVE',
    target: 'pending',
    label: 'workflows.membership.approve',
    actors: ['Members_CRUD', 'Members_Status_Approve'],
    confirmMessage: 'workflows.membership.confirm.approve',
    description: 'workflows.membership.description.approve',
  },
];

/**
 * Transitions available from the 'pending' state.
 * APPROVE moves to 'wait_payment' (requires regio to be assigned).
 */
const pendingTransitions: TransitionConfig[] = [
  {
    event: 'APPROVE',
    target: 'wait_payment',
    label: 'workflows.membership.approve',
    actors: ['Members_CRUD', 'Members_Status_Approve'],
    requiredFields: ['regio'],
    confirmMessage: 'workflows.membership.confirm.approvePayment',
    description: 'workflows.membership.description.approvePayment',
  },
];

/**
 * Transitions available from the 'wait_payment' state.
 * PAYMENT_RECEIVED activates the member.
 */
const waitPaymentTransitions: TransitionConfig[] = [
  {
    event: 'PAYMENT_RECEIVED',
    target: 'active',
    label: 'workflows.membership.paymentReceived',
    actors: ['Members_CRUD', 'Members_Status_Approve'],
    confirmMessage: 'workflows.membership.confirm.paymentReceived',
    description: 'workflows.membership.description.paymentReceived',
  },
];

/**
 * Transitions available from the 'active' state.
 * CANCEL ends the membership; SUSPEND temporarily blocks it (requires reason, min 10 chars).
 */
const activeTransitions: TransitionConfig[] = [
  {
    event: 'CANCEL',
    target: 'cancelled',
    label: 'workflows.membership.cancel',
    actors: ['Members_CRUD', 'Members_Status_Approve'],
    confirmMessage: 'workflows.membership.confirm.cancel',
    description: 'workflows.membership.description.cancel',
  },
  {
    event: 'SUSPEND',
    target: 'suspended',
    label: 'workflows.membership.suspend',
    actors: ['Members_CRUD'],
    requiredFields: ['reason'],
    confirmMessage: 'workflows.membership.confirm.suspend',
    description: 'workflows.membership.description.suspend',
  },
];

/**
 * Transitions available from the 'suspended' state.
 * REACTIVATE returns the member to active.
 */
const suspendedTransitions: TransitionConfig[] = [
  {
    event: 'REACTIVATE',
    target: 'active',
    label: 'workflows.membership.reactivate',
    actors: ['Members_CRUD'],
    confirmMessage: 'workflows.membership.confirm.reactivate',
    description: 'workflows.membership.description.reactivate',
  },
];

// ============================================================================
// WORKFLOW DEFINITION
// ============================================================================

/**
 * Complete membership workflow definition.
 * Maps every state to its available transitions, including actor permissions
 * and required fields for each transition.
 */
export const membershipWorkflow: WorkflowDefinition = {
  states: {
    draft: { transitions: draftTransitions },
    applied: { transitions: appliedTransitions },
    pending: { transitions: pendingTransitions },
    wait_payment: { transitions: waitPaymentTransitions },
    active: { transitions: activeTransitions },
    cancelled: { transitions: [] },
    suspended: { transitions: suspendedTransitions },
  },
};
