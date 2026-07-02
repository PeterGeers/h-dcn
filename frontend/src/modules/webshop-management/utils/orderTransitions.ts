/**
 * Order Fulfilment State Machine (Frontend)
 *
 * Mirrors the backend VALID_TRANSITIONS map for determining
 * which transitions are available to the admin in the UI.
 *
 * Validates: Requirements 4.1, 4.4, 5.4
 */

import { OrderStatus } from '../types/admin.types';

type Actor = 'admin' | 'customer' | 'system';

interface TransitionConfig {
  actors: Actor[];
  preconditions: string[];
  /** Label shown on the action button */
  label: string;
}

/**
 * Valid transitions map — source of truth for frontend UI.
 * Must stay in sync with backend shared/order_state_machine.py VALID_TRANSITIONS.
 */
const VALID_TRANSITIONS: Record<string, Record<string, TransitionConfig>> = {
  draft: {
    submitted: { actors: ['customer', 'system'], preconditions: [], label: 'Indienen' },
  },
  submitted: {
    paid: { actors: ['system'], preconditions: [], label: 'Betaald' },
    payment_failed: { actors: ['system'], preconditions: [], label: 'Betaling mislukt' },
    locked: { actors: ['admin'], preconditions: [], label: 'Vergrendelen' },
  },
  locked: {
    submitted: { actors: ['admin'], preconditions: [], label: 'Ontgrendelen' },
    paid: { actors: ['system'], preconditions: [], label: 'Betaald' },
  },
  payment_failed: {
    submitted: { actors: ['customer'], preconditions: [], label: 'Opnieuw proberen' },
  },
  paid: {
    order_received: { actors: ['admin'], preconditions: [], label: 'Ontvangen' },
    ready_for_pickup: { actors: ['admin'], preconditions: [], label: 'Klaarzetten voor afhaal' },
  },
  order_received: {
    picked: { actors: ['admin'], preconditions: [], label: 'Gepickt' },
  },
  picked: {
    packed: { actors: ['admin'], preconditions: [], label: 'Ingepakt' },
  },
  packed: {
    shipped: { actors: ['admin'], preconditions: ['tracking_number'], label: 'Verzonden' },
  },
  shipped: {
    delivered: { actors: ['admin'], preconditions: [], label: 'Bezorgd' },
  },
  delivered: {
    completed: { actors: ['admin'], preconditions: [], label: 'Afgerond' },
    return_requested: { actors: ['admin', 'customer'], preconditions: [], label: 'Retour aangevraagd' },
  },
  return_requested: {
    return_received: { actors: ['admin'], preconditions: [], label: 'Retour ontvangen' },
  },
  return_received: {
    completed: { actors: ['admin'], preconditions: [], label: 'Afgerond' },
  },
  ready_for_pickup: {
    picked_up: { actors: ['admin'], preconditions: [], label: 'Uitgereikt' },
  },
  picked_up: {
    completed: { actors: ['admin'], preconditions: [], label: 'Afgerond' },
  },
  completed: {},
};

export interface AvailableTransition {
  target: OrderStatus;
  label: string;
  requiresTrackingNumber: boolean;
}

/**
 * Get valid transitions for the admin actor from the given status.
 * Optionally filter by source_id to show context-appropriate actions.
 */
export function getAdminTransitions(
  currentStatus: OrderStatus,
  sourceId?: string
): AvailableTransition[] {
  const targets = VALID_TRANSITIONS[currentStatus];
  if (!targets) return [];

  const isEventOrder = sourceId && sourceId !== 'webshop';

  const transitions: AvailableTransition[] = [];
  for (const [target, config] of Object.entries(targets)) {
    if (!config.actors.includes('admin')) continue;

    // Context-aware filtering:
    // - Event orders skip webshop-specific transitions (order_received → picked → packed → shipped)
    // - Webshop orders skip event-specific transitions (ready_for_pickup → picked_up)
    if (isEventOrder && ['order_received', 'picked', 'packed', 'shipped', 'delivered'].includes(target)) {
      continue;
    }
    if (!isEventOrder && ['ready_for_pickup', 'picked_up'].includes(target)) {
      continue;
    }

    transitions.push({
      target: target as OrderStatus,
      label: config.label,
      requiresTrackingNumber: config.preconditions.includes('tracking_number'),
    });
  }

  return transitions;
}

/**
 * Check whether a transition requires tracking info.
 */
export function transitionRequiresTracking(target: OrderStatus): boolean {
  return target === 'shipped';
}
