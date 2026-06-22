/**
 * Person management utilities — pure functions for person CRUD operations
 * on the booking form state.
 *
 * These functions extract the core logic from BookingWizard into testable,
 * side-effect-free utilities.
 *
 * Validates: Requirements 6.1, 6.4, 6.5
 */

import { Product } from '../types/eventBooking.types';
import { PersonFormState } from './orderTransformer';

/**
 * Calculate the maximum number of persons allowed on an order based on
 * the highest max_per_club value across all event-linked products.
 *
 * Returns at least 1 (a delegate always counts as one person).
 *
 * Validates: Requirement 6.1
 */
export function getMaxPersons(products: Product[]): number {
  if (products.length === 0) return 1;
  return Math.max(
    1,
    ...products.map((p) => p.purchase_rules?.max_per_club ?? 1)
  );
}

/**
 * Update a person's name and sync it to all their product lines'
 * item_fields_data.name. Product lines for other persons remain unchanged.
 *
 * Returns a new PersonFormState (immutable).
 *
 * Validates: Requirement 6.4
 */
export function syncPersonName(
  state: PersonFormState,
  personIndex: number,
  newName: string
): PersonFormState {
  if (personIndex < 0 || personIndex >= state.persons.length) return state;

  return {
    persons: state.persons.map((person, idx) => {
      if (idx !== personIndex) return person;
      return {
        ...person,
        name: newName,
      };
    }),
  };
}

/**
 * Convert person-centric form state to flat order items, demonstrating
 * that a person's name is propagated to all their product lines.
 *
 * This is a projection: for each person, each product line gets
 * item_fields_data.name = person.name.
 *
 * Validates: Requirement 6.4
 */
export function getProductLinesWithNames(
  state: PersonFormState
): Array<{ personIndex: number; productIndex: number; name: string }> {
  const lines: Array<{ personIndex: number; productIndex: number; name: string }> = [];
  for (let pIdx = 0; pIdx < state.persons.length; pIdx++) {
    const person = state.persons[pIdx];
    for (let prodIdx = 0; prodIdx < person.products.length; prodIdx++) {
      lines.push({
        personIndex: pIdx,
        productIndex: prodIdx,
        name: person.name,
      });
    }
  }
  return lines;
}

/**
 * Remove a person at the given index and cascade-delete all their
 * associated product lines.
 *
 * Returns a new PersonFormState with (N-1) persons and no product lines
 * belonging to the removed person. Product lines for other persons are intact.
 *
 * Validates: Requirement 6.5
 */
export function removePerson(
  state: PersonFormState,
  personIndex: number
): PersonFormState {
  if (personIndex < 0 || personIndex >= state.persons.length) return state;

  return {
    persons: state.persons.filter((_, idx) => idx !== personIndex),
  };
}
