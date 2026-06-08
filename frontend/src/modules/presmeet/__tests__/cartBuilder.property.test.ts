/**
 * Property-based tests for the cart builder utility.
 *
 * Feature: presmeet-v3
 * Tests Properties 8 and 9 from the design document.
 *
 * Uses fast-check with minimum 100 iterations per property.
 */

import * as fc from 'fast-check';
import { buildCartItems } from '../utils/cartBuilder';
import {
  BookingFormData,
  DelegateFormData,
  GuestFormData,
  TransferFormData,
  PresMeetConfig,
  Gender,
  TshirtSize,
  TransferDirection,
  Airport,
} from '../types/presmeet';

// --- Arbitraries ---

const genderArb: fc.Arbitrary<Gender> = fc.constantFrom('male', 'female');
const tshirtSizeArb: fc.Arbitrary<TshirtSize> = fc.constantFrom('S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL');
const directionArb: fc.Arbitrary<TransferDirection> = fc.constantFrom('pickup', 'dropoff');
const airportArb: fc.Arbitrary<Airport> = fc.constantFrom('AMS', 'RTM', 'EIN');

const tshirtArb = fc.record({
  gender: genderArb,
  size: tshirtSizeArb,
});

const delegateArb: fc.Arbitrary<DelegateFormData> = fc.record({
  name: fc.string({ minLength: 1, maxLength: 50 }),
  role: fc.string({ minLength: 1, maxLength: 30 }),
  attend_party: fc.boolean(),
  tshirt: fc.option(tshirtArb, { nil: undefined }),
});

const guestArb: fc.Arbitrary<GuestFormData> = fc.record({
  name: fc.string({ minLength: 1, maxLength: 50 }),
  tshirt: fc.option(tshirtArb, { nil: undefined }),
});

const transferArb: fc.Arbitrary<TransferFormData> = fc.record({
  direction: directionArb,
  airport: airportArb,
  flight: fc.string({ minLength: 2, maxLength: 10 }),
  date: fc.date({ min: new Date('2025-01-01'), max: new Date('2026-12-31') }).map(d => d.toISOString().split('T')[0]),
  time: fc.integer({ min: 0, max: 23 }).chain(h =>
    fc.integer({ min: 0, max: 59 }).map(m =>
      `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
    )
  ),
  persons: fc.integer({ min: 1, max: 10 }),
});

const partyTicketUnitPriceArb = fc.double({ min: 1, max: 500, noNaN: true, noDefaultInfinity: true })
  .map(v => Math.round(v * 100) / 100);

function configArb(partyPrice: number): fc.Arbitrary<PresMeetConfig> {
  return fc.record({
    product_types: fc.constant([
      {
        product_type: 'meeting_ticket' as const,
        max_per_club: 10,
        min_per_club: 1,
        unit_price: 50,
        required_attributes: {},
      },
      {
        product_type: 'party_ticket' as const,
        max_per_club: 20,
        min_per_club: 0,
        unit_price: partyPrice,
        required_attributes: {},
      },
      {
        product_type: 'tshirt' as const,
        max_per_club: 20,
        min_per_club: 0,
        unit_price: 25,
        required_attributes: {},
      },
      {
        product_type: 'airport_transfer' as const,
        max_per_club: 10,
        min_per_club: 0,
        unit_price: 5,
        required_attributes: {},
      },
    ]),
    event: fc.constant({
      event_id: 'evt_test',
      start_date: '2025-06-01',
      end_date: '2025-06-03',
    }),
  });
}

function formDataArb(delegates: DelegateFormData[]): fc.Arbitrary<BookingFormData> {
  return fc.record({
    delegates: fc.constant(delegates),
    guests: fc.array(guestArb, { minLength: 0, maxLength: 5 }),
    transfers: fc.array(transferArb, { minLength: 0, maxLength: 3 }),
  });
}

// --- Property Tests ---

describe('cartBuilder property tests', () => {
  /**
   * Property 8: Delegate party ticket cart item generation
   *
   * For any delegate with attend_party set to true, buildCartItems produces
   * a party_ticket cart item with that delegate's name in the attributes,
   * person_type "delegate", and the configured party_ticket unit price.
   *
   * **Validates: Requirements 7.1, 2.1**
   */
  it('Property 8: delegates with attend_party=true produce party_ticket items with correct attributes', () => {
    fc.assert(
      fc.property(
        fc.array(delegateArb, { minLength: 1, maxLength: 10 }),
        partyTicketUnitPriceArb,
        (delegates, partyPrice) => {
          const config: PresMeetConfig = {
            product_types: [
              { product_type: 'meeting_ticket', max_per_club: 10, min_per_club: 1, unit_price: 50, required_attributes: {} },
              { product_type: 'party_ticket', max_per_club: 20, min_per_club: 0, unit_price: partyPrice, required_attributes: {} },
              { product_type: 'tshirt', max_per_club: 20, min_per_club: 0, unit_price: 25, required_attributes: {} },
              { product_type: 'airport_transfer', max_per_club: 10, min_per_club: 0, unit_price: 5, required_attributes: {} },
            ],
            event: { event_id: 'evt_test', start_date: '2025-06-01', end_date: '2025-06-03' },
          };

          const formData: BookingFormData = {
            delegates,
            guests: [],
            transfers: [],
          };

          const result = buildCartItems(formData, config);

          // For each delegate with attend_party: true, there must be a matching party_ticket
          const partyDelegates = delegates.filter(d => d.attend_party);

          for (const delegate of partyDelegates) {
            const matchingItem = result.items.find(
              item =>
                item.product_type === 'party_ticket' &&
                item.attributes.name === delegate.name &&
                item.attributes.person_type === 'delegate'
            );

            // Must exist
            expect(matchingItem).toBeDefined();

            // Must have correct unit price
            expect(matchingItem!.unit_price).toBe(partyPrice);
          }

          // Count of delegate party tickets should equal number of delegates with attend_party
          const delegatePartyTickets = result.items.filter(
            item => item.product_type === 'party_ticket' && item.attributes.person_type === 'delegate'
          );
          expect(delegatePartyTickets.length).toBe(partyDelegates.length);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9: Order total includes delegate party tickets
   *
   * For any set of delegates where N delegates have attend_party: true,
   * the total computed by buildCartItems SHALL include N × party_ticket_unit_price
   * in addition to all other item costs.
   *
   * **Validates: Requirements 7.2, 7.3**
   */
  it('Property 9: total includes N × party_ticket_unit_price for N delegates with attend_party=true', () => {
    fc.assert(
      fc.property(
        fc.array(delegateArb, { minLength: 1, maxLength: 10 }),
        fc.array(guestArb, { minLength: 0, maxLength: 5 }),
        fc.array(transferArb, { minLength: 0, maxLength: 3 }),
        partyTicketUnitPriceArb,
        (delegates, guests, transfers, partyPrice) => {
          const meetingPrice = 50;
          const tshirtPrice = 25;
          const transferPrice = 5;

          const config: PresMeetConfig = {
            product_types: [
              { product_type: 'meeting_ticket', max_per_club: 10, min_per_club: 1, unit_price: meetingPrice, required_attributes: {} },
              { product_type: 'party_ticket', max_per_club: 20, min_per_club: 0, unit_price: partyPrice, required_attributes: {} },
              { product_type: 'tshirt', max_per_club: 20, min_per_club: 0, unit_price: tshirtPrice, required_attributes: {} },
              { product_type: 'airport_transfer', max_per_club: 10, min_per_club: 0, unit_price: transferPrice, required_attributes: {} },
            ],
            event: { event_id: 'evt_test', start_date: '2025-06-01', end_date: '2025-06-03' },
          };

          const formData: BookingFormData = { delegates, guests, transfers };

          const result = buildCartItems(formData, config);

          // Calculate expected total manually
          const N = delegates.filter(d => d.attend_party).length;
          const delegatePartyTotal = N * partyPrice;

          const meetingTotal = delegates.length * meetingPrice;
          const guestPartyTotal = guests.length * partyPrice;
          const delegateTshirtTotal = delegates.filter(d => d.tshirt).length * tshirtPrice;
          const guestTshirtTotal = guests.filter(g => g.tshirt).length * tshirtPrice;
          const transferTotal = transfers.reduce((sum, t) => sum + t.persons * transferPrice, 0);

          const expectedTotal =
            meetingTotal +
            delegatePartyTotal +
            guestPartyTotal +
            delegateTshirtTotal +
            guestTshirtTotal +
            transferTotal;

          // Use a small epsilon for floating point comparison
          expect(Math.abs(result.totalAmount - expectedTotal)).toBeLessThan(0.01);
        }
      ),
      { numRuns: 100 }
    );
  });
});
