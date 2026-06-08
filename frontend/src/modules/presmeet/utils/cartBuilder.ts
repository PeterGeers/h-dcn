/**
 * Cart builder utility — generates cart items from booking form data.
 *
 * Extracted from BookingForm for testability and reuse in overview/PDF contexts.
 * Handles:
 * - Meeting ticket items for each delegate
 * - Party ticket items for delegates with attend_party: true
 * - Party ticket items for guests
 * - T-shirt items for delegates and guests
 * - Airport transfer items with persons-based total calculation
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 8.1, 8.2
 */

import {
  CartItem,
  BookingFormData,
  PresMeetConfig,
  ProductType,
  ProductTypeConfig,
} from '../types/presmeet';

export interface CartBuildResult {
  items: CartItem[];
  totalAmount: number;
  itemCount: number;
}

/**
 * Get the unit price for a product type from config, with sensible defaults.
 */
function getUnitPrice(config: PresMeetConfig, productType: ProductType): number {
  const typeConfig = config.product_types.find(
    (pt: ProductTypeConfig) => pt.product_type === productType
  );
  if (typeConfig) return typeConfig.unit_price;

  // Fallback defaults matching the existing BookingForm logic
  const defaults: Record<ProductType, number> = {
    meeting_ticket: 50,
    party_ticket: 99.5,
    tshirt: 25,
    airport_transfer: 5,
  };
  return defaults[productType];
}

/**
 * Generate a unique item_id for a cart item.
 */
function generateItemId(productType: ProductType, index: number, suffix?: string): string {
  const base = `${productType}_${index}`;
  return suffix ? `${base}_${suffix}` : base;
}

/**
 * Build cart items from form data and config.
 *
 * Generates:
 * - 1 meeting_ticket per delegate (with name, role, attend_party attributes)
 * - 1 party_ticket per delegate with attend_party: true (person_type "delegate")
 * - 1 party_ticket per guest (person_type "guest")
 * - 1 tshirt per delegate/guest with tshirt selection
 * - 1 airport_transfer per transfer entry (with persons attribute)
 *
 * Total calculation:
 * - Most items: 1 × unit_price
 * - airport_transfer: persons × unit_price
 */
export function buildCartItems(
  formData: BookingFormData,
  config: PresMeetConfig
): CartBuildResult {
  const items: CartItem[] = [];

  const meetingPrice = getUnitPrice(config, 'meeting_ticket');
  const partyPrice = getUnitPrice(config, 'party_ticket');
  const tshirtPrice = getUnitPrice(config, 'tshirt');
  const transferPrice = getUnitPrice(config, 'airport_transfer');

  // --- Meeting tickets (one per delegate) ---
  formData.delegates.forEach((delegate, i) => {
    items.push({
      item_id: generateItemId('meeting_ticket', i),
      product_type: 'meeting_ticket',
      attributes: {
        name: delegate.name,
        role: delegate.role,
        attend_party: delegate.attend_party,
      },
      unit_price: meetingPrice,
    });
  });

  // --- Party tickets for delegates with attend_party: true ---
  let partyIndex = 0;
  formData.delegates.forEach((delegate) => {
    if (delegate.attend_party) {
      items.push({
        item_id: generateItemId('party_ticket', partyIndex, 'delegate'),
        product_type: 'party_ticket',
        attributes: {
          name: delegate.name,
          person_type: 'delegate',
        },
        unit_price: partyPrice,
      });
      partyIndex++;
    }
  });

  // --- Party tickets for guests ---
  formData.guests.forEach((guest) => {
    items.push({
      item_id: generateItemId('party_ticket', partyIndex, 'guest'),
      product_type: 'party_ticket',
      attributes: {
        name: guest.name,
        person_type: 'guest',
      },
      unit_price: partyPrice,
    });
    partyIndex++;
  });

  // --- T-shirts for delegates ---
  let tshirtIndex = 0;
  formData.delegates.forEach((delegate) => {
    if (delegate.tshirt) {
      items.push({
        item_id: generateItemId('tshirt', tshirtIndex),
        product_type: 'tshirt',
        attributes: {
          name: delegate.name,
          gender: delegate.tshirt.gender,
          size: delegate.tshirt.size,
        },
        unit_price: tshirtPrice,
      });
      tshirtIndex++;
    }
  });

  // --- T-shirts for guests ---
  formData.guests.forEach((guest) => {
    if (guest.tshirt) {
      items.push({
        item_id: generateItemId('tshirt', tshirtIndex),
        product_type: 'tshirt',
        attributes: {
          name: guest.name,
          gender: guest.tshirt.gender,
          size: guest.tshirt.size,
        },
        unit_price: tshirtPrice,
      });
      tshirtIndex++;
    }
  });

  // --- Airport transfers ---
  formData.transfers.forEach((transfer, i) => {
    items.push({
      item_id: generateItemId('airport_transfer', i),
      product_type: 'airport_transfer',
      attributes: {
        direction: transfer.direction,
        airport: transfer.airport,
        flight: transfer.flight,
        date: transfer.date,
        time: transfer.time,
        persons: transfer.persons,
      },
      unit_price: transferPrice,
    });
  });

  // --- Calculate total ---
  // All items: 1 × unit_price EXCEPT airport_transfer: persons × unit_price
  const totalAmount = items.reduce((sum, item) => {
    if (item.product_type === 'airport_transfer') {
      const persons = (item.attributes.persons as number) || 1;
      return sum + item.unit_price * persons;
    }
    return sum + item.unit_price;
  }, 0);

  return {
    items,
    totalAmount,
    itemCount: items.length,
  };
}
