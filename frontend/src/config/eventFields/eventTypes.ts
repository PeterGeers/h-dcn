/**
 * Event Type Taxonomy
 *
 * Hierarchical event classification system for H-DCN.
 * Single source of truth — used by Field Registry, types, and backend validation.
 *
 * Structure:
 *   EventCategory → EventType (subtypes within each category)
 *   ParticipationMode (orthogonal axis: open vs closed)
 *   LinkedRegio (for region-scoped events like RLV, regio_rit)
 */

// ============================================================================
// CATEGORIES (top-level grouping)
// ============================================================================

export const EVENT_CATEGORIES = ['vergadering', 'rally', 'rit', 'overig'] as const;
export type EventCategory = (typeof EVENT_CATEGORIES)[number];

// ============================================================================
// TYPES (subtypes within each category)
// ============================================================================

export const EVENT_TYPES_BY_CATEGORY = {
  vergadering: ['presmeet', 'alv', 'rlv', 'vbv', 'vergader_queue'],
  rally: ['internationaal_treffen', 'nationaal_treffen'],
  rit: ['openingsrit', 'regio_rit', 'tourweekend', 'sluitingsrit'],
  overig: ['webshop', 'other'],
} as const satisfies Record<EventCategory, readonly string[]>;

/** Flat list of all valid event types */
export const EVENT_TYPES = Object.values(EVENT_TYPES_BY_CATEGORY).flat();
export type EventType = (typeof EVENT_TYPES_BY_CATEGORY)[EventCategory][number];

// ============================================================================
// PARTICIPATION MODE (orthogonal to category/type)
// ============================================================================

export const PARTICIPATION_MODES = ['open', 'members', 'closed'] as const;
export type ParticipationMode = (typeof PARTICIPATION_MODES)[number];

// ============================================================================
// ORDER FLOW (how the ordering process works)
// ============================================================================

export const ORDER_FLOWS = ['catalog', 'attendee'] as const;
export type OrderFlow = (typeof ORDER_FLOWS)[number];

export const ORDER_FLOW_LABELS: Record<OrderFlow, string> = {
  catalog: 'Catalogus (webshop-achtig)',
  attendee: 'Per deelnemer (registry-based)',
};

// ============================================================================
// LINKED REGIO (for region-scoped events: RLV, regio_rit)
// ============================================================================

/**
 * Regions that can be linked to an event.
 * 'regio_all' means the event applies to all regions (e.g., national ALV).
 * The rest match the member regio enum in memberFields.
 */
export const EVENT_REGIOS = [
  'regio_all',
  'Noord-Holland',
  'Zuid-Holland',
  'Friesland',
  'Utrecht',
  'Oost',
  'Limburg',
  'Groningen/Drenthe',
  'Brabant/Zeeland',
  'Duitsland',
  'Overig',
] as const;
export type EventRegio = (typeof EVENT_REGIOS)[number];

/**
 * Event types that require a linked_regio value.
 */
export const REGIO_LINKED_EVENT_TYPES: EventType[] = ['rlv', 'regio_rit'];

// ============================================================================
// LABELS (Dutch display names for UI)
// ============================================================================

export const EVENT_CATEGORY_LABELS: Record<EventCategory, string> = {
  vergadering: 'Vergaderingen / Meetings',
  rally: 'Rallies',
  rit: 'Ritten',
  overig: 'Overig',
};

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  presmeet: 'PresMeet',
  alv: 'ALV (Algemene Ledenvergadering)',
  rlv: 'RLV (Regio Vergadering)',
  vbv: 'VBV',
  vergader_queue: 'Vergader Queue',
  internationaal_treffen: 'Internationaal Treffen',
  nationaal_treffen: 'Nationaal Treffen',
  openingsrit: 'Openingsrit',
  regio_rit: 'Regio Rit',
  tourweekend: 'Tourweekend',
  sluitingsrit: 'Sluitingsrit',
  webshop: 'Webshop',
  other: 'Anders',
};

export const PARTICIPATION_MODE_LABELS: Record<ParticipationMode, string> = {
  open: 'Open (deelname voor iedereen)',
  members: 'Leden (alleen H-DCN leden)',
  closed: 'Besloten (alleen genodigden)',
};

// ============================================================================
// HELPERS
// ============================================================================

/** Get the category for a given event type */
export function getCategoryForType(eventType: EventType): EventCategory {
  for (const [category, types] of Object.entries(EVENT_TYPES_BY_CATEGORY)) {
    if ((types as readonly string[]).includes(eventType)) {
      return category as EventCategory;
    }
  }
  return 'overig';
}

/** Get all event types for a given category */
export function getTypesForCategory(category: EventCategory): readonly string[] {
  return EVENT_TYPES_BY_CATEGORY[category];
}

/** Check if an event type requires a linked regio */
export function requiresLinkedRegio(eventType: EventType): boolean {
  return REGIO_LINKED_EVENT_TYPES.includes(eventType);
}
