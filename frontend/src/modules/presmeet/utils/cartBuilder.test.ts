/**
 * Unit tests for cartBuilder utility.
 *
 * Tests core behaviors:
 * - Party ticket generation for delegates with attend_party: true
 * - Airport transfer items carry persons attribute
 * - Total calculation multiplies transfer unit_price × persons
 */

import { buildCartItems, CartBuildResult } from './cartBuilder';
import { BookingFormData, PresMeetConfig } from '../types/presmeet';

const mockConfig: PresMeetConfig = {
  product_types: [
    {
      product_type: 'meeting_ticket',
      max_per_club: 3,
      min_per_club: 1,
      unit_price: 50,
      required_attributes: {},
    },
    {
      product_type: 'party_ticket',
      max_per_club: 13,
      min_per_club: 0,
      unit_price: 99.5,
      required_attributes: {},
    },
    {
      product_type: 'tshirt',
      max_per_club: 13,
      min_per_club: 0,
      unit_price: 25,
      required_attributes: {},
    },
    {
      product_type: 'airport_transfer',
      max_per_club: 20,
      min_per_club: 0,
      unit_price: 5,
      required_attributes: {},
    },
  ],
  event: {
    event_id: 'evt-2025',
    start_date: '2025-06-01',
    end_date: '2025-06-05',
  },
};

describe('buildCartItems', () => {
  it('generates meeting_ticket items for each delegate', () => {
    const formData: BookingFormData = {
      delegates: [
        { name: 'Alice', role: 'President', attend_party: false },
        { name: 'Bob', role: 'Treasurer', attend_party: false },
      ],
      guests: [],
      transfers: [],
    };

    const result = buildCartItems(formData, mockConfig);

    const meetingTickets = result.items.filter((i) => i.product_type === 'meeting_ticket');
    expect(meetingTickets).toHaveLength(2);
    expect(meetingTickets[0].attributes.name).toBe('Alice');
    expect(meetingTickets[1].attributes.name).toBe('Bob');
    expect(meetingTickets[0].unit_price).toBe(50);
  });

  it('generates party_ticket items for delegates with attend_party: true', () => {
    const formData: BookingFormData = {
      delegates: [
        { name: 'Alice', role: 'President', attend_party: true },
        { name: 'Bob', role: 'Treasurer', attend_party: false },
        { name: 'Charlie', role: 'Secretary', attend_party: true },
      ],
      guests: [],
      transfers: [],
    };

    const result = buildCartItems(formData, mockConfig);

    const partyTickets = result.items.filter((i) => i.product_type === 'party_ticket');
    expect(partyTickets).toHaveLength(2);

    // Check delegate party tickets have correct attributes
    expect(partyTickets[0].attributes.name).toBe('Alice');
    expect(partyTickets[0].attributes.person_type).toBe('delegate');
    expect(partyTickets[0].unit_price).toBe(99.5);

    expect(partyTickets[1].attributes.name).toBe('Charlie');
    expect(partyTickets[1].attributes.person_type).toBe('delegate');
  });

  it('generates party_ticket items for guests with person_type "guest"', () => {
    const formData: BookingFormData = {
      delegates: [],
      guests: [{ name: 'Diana' }, { name: 'Eve' }],
      transfers: [],
    };

    const result = buildCartItems(formData, mockConfig);

    const partyTickets = result.items.filter((i) => i.product_type === 'party_ticket');
    expect(partyTickets).toHaveLength(2);
    expect(partyTickets[0].attributes.name).toBe('Diana');
    expect(partyTickets[0].attributes.person_type).toBe('guest');
    expect(partyTickets[1].attributes.name).toBe('Eve');
    expect(partyTickets[1].attributes.person_type).toBe('guest');
  });

  it('airport_transfer items carry persons attribute from form data', () => {
    const formData: BookingFormData = {
      delegates: [],
      guests: [],
      transfers: [
        {
          direction: 'pickup',
          airport: 'AMS',
          flight: 'KL1234',
          date: '2025-06-01',
          time: '14:00',
          persons: 3,
        },
      ],
    };

    const result = buildCartItems(formData, mockConfig);

    const transfers = result.items.filter((i) => i.product_type === 'airport_transfer');
    expect(transfers).toHaveLength(1);
    expect(transfers[0].attributes.persons).toBe(3);
    expect(transfers[0].attributes.direction).toBe('pickup');
    expect(transfers[0].attributes.airport).toBe('AMS');
  });

  it('total calculation multiplies transfer unit_price × persons', () => {
    const formData: BookingFormData = {
      delegates: [],
      guests: [],
      transfers: [
        {
          direction: 'pickup',
          airport: 'AMS',
          flight: 'KL1234',
          date: '2025-06-01',
          time: '14:00',
          persons: 4,
        },
      ],
    };

    const result = buildCartItems(formData, mockConfig);

    // Transfer price is 5, persons is 4 → total should be 20
    expect(result.totalAmount).toBe(20);
  });

  it('calculates correct total with mixed items', () => {
    const formData: BookingFormData = {
      delegates: [
        { name: 'Alice', role: 'President', attend_party: true, tshirt: { gender: 'female', size: 'M' } },
        { name: 'Bob', role: 'Treasurer', attend_party: false },
      ],
      guests: [{ name: 'Diana' }],
      transfers: [
        {
          direction: 'pickup',
          airport: 'AMS',
          flight: 'KL1234',
          date: '2025-06-01',
          time: '14:00',
          persons: 2,
        },
      ],
    };

    const result = buildCartItems(formData, mockConfig);

    // 2 meeting_tickets: 2 × 50 = 100
    // 1 delegate party_ticket (Alice): 1 × 99.5 = 99.5
    // 1 guest party_ticket (Diana): 1 × 99.5 = 99.5
    // 1 tshirt (Alice): 1 × 25 = 25
    // 1 transfer (2 persons): 2 × 5 = 10
    // Total: 100 + 99.5 + 99.5 + 25 + 10 = 334
    expect(result.totalAmount).toBe(334);
    expect(result.itemCount).toBe(6);
  });

  it('returns empty result for empty form data', () => {
    const formData: BookingFormData = {
      delegates: [],
      guests: [],
      transfers: [],
    };

    const result = buildCartItems(formData, mockConfig);

    expect(result.items).toHaveLength(0);
    expect(result.totalAmount).toBe(0);
    expect(result.itemCount).toBe(0);
  });
});
