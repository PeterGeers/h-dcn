/**
 * Client-side validation logic tests for PresMeet booking form.
 *
 * Validates: Requirements 4.1–4.5, 8.1–8.5
 */

import {
  validateDelegate,
  validateGuest,
  validateTransfer,
} from '../utils/validation';
import { DelegateFormData, GuestFormData, TransferFormData } from '../types/presmeet';

describe('validateDelegate', () => {
  it('valid delegate returns no errors', () => {
    const delegate: DelegateFormData = {
      name: 'Jan de Vries',
      role: 'President',
      attend_party: true,
    };
    const errors = validateDelegate(delegate, 0);
    expect(errors).toHaveLength(0);
  });

  it('missing name returns required error', () => {
    const delegate: DelegateFormData = {
      name: '',
      role: 'President',
      attend_party: false,
    };
    const errors = validateDelegate(delegate, 0);
    expect(errors).toHaveLength(1);
    expect(errors[0].field).toBe('delegates[0].name');
    expect(errors[0].constraint).toBe('required');
  });

  it('missing role returns required error', () => {
    const delegate: DelegateFormData = {
      name: 'Jan de Vries',
      role: '',
      attend_party: false,
    };
    const errors = validateDelegate(delegate, 0);
    expect(errors).toHaveLength(1);
    expect(errors[0].field).toBe('delegates[0].role');
    expect(errors[0].constraint).toBe('required');
  });

  it('valid delegate with tshirt returns no errors', () => {
    const delegate: DelegateFormData = {
      name: 'Jan de Vries',
      role: 'Secretary',
      attend_party: true,
      tshirt: { gender: 'male', size: 'L' },
    };
    const errors = validateDelegate(delegate, 2);
    expect(errors).toHaveLength(0);
  });

  it('invalid tshirt gender returns enum error', () => {
    const delegate: DelegateFormData = {
      name: 'Jan de Vries',
      role: 'President',
      attend_party: false,
      tshirt: { gender: 'other' as any, size: 'M' },
    };
    const errors = validateDelegate(delegate, 0);
    expect(errors.some((e) => e.field === 'delegates[0].tshirt.gender' && e.constraint === 'enum')).toBe(true);
  });
});

describe('validateGuest', () => {
  it('valid guest returns no errors', () => {
    const guest: GuestFormData = {
      name: 'Maria Jansen',
    };
    const errors = validateGuest(guest, 0);
    expect(errors).toHaveLength(0);
  });

  it('missing name returns required error', () => {
    const guest: GuestFormData = {
      name: '',
    };
    const errors = validateGuest(guest, 1);
    expect(errors).toHaveLength(1);
    expect(errors[0].field).toBe('guests[1].name');
    expect(errors[0].constraint).toBe('required');
  });

  it('valid guest with tshirt returns no errors', () => {
    const guest: GuestFormData = {
      name: 'Maria Jansen',
      tshirt: { gender: 'female', size: 'S' },
    };
    const errors = validateGuest(guest, 0);
    expect(errors).toHaveLength(0);
  });
});

describe('validateTransfer', () => {
  const validTransfer: TransferFormData = {
    direction: 'pickup',
    airport: 'AMS',
    flight: 'KL1234',
    date: '2025-09-16',
    time: '14:30',
    persons: 3,
  };

  it('valid transfer returns no errors', () => {
    const errors = validateTransfer(validTransfer, 0, '2025-09-15', '2025-09-18');
    expect(errors).toHaveLength(0);
  });

  it('date outside event range returns error', () => {
    const transfer: TransferFormData = {
      ...validTransfer,
      date: '2025-09-20', // after event end
    };
    const errors = validateTransfer(transfer, 0, '2025-09-15', '2025-09-18');
    expect(errors.some((e) => e.field === 'transfers[0].date' && e.constraint === 'range')).toBe(true);
  });

  it('date before event start returns error', () => {
    const transfer: TransferFormData = {
      ...validTransfer,
      date: '2025-09-10', // before event start
    };
    const errors = validateTransfer(transfer, 0, '2025-09-15', '2025-09-18');
    expect(errors.some((e) => e.field === 'transfers[0].date' && e.constraint === 'range')).toBe(true);
  });

  it('invalid flight length (too short) returns error', () => {
    const transfer: TransferFormData = {
      ...validTransfer,
      flight: 'X', // less than 2 chars
    };
    const errors = validateTransfer(transfer, 0, '2025-09-15', '2025-09-18');
    expect(errors.some((e) => e.field === 'transfers[0].flight' && e.constraint === 'min_length')).toBe(true);
  });

  it('invalid flight length (too long) returns error', () => {
    const transfer: TransferFormData = {
      ...validTransfer,
      flight: 'ABCDEFGHIJK', // more than 10 chars
    };
    const errors = validateTransfer(transfer, 0, '2025-09-15', '2025-09-18');
    expect(errors.some((e) => e.field === 'transfers[0].flight' && e.constraint === 'max_length')).toBe(true);
  });

  it('invalid time format returns error', () => {
    const transfer: TransferFormData = {
      ...validTransfer,
      time: '25:99',
    };
    const errors = validateTransfer(transfer, 0, '2025-09-15', '2025-09-18');
    expect(errors.some((e) => e.field === 'transfers[0].time' && e.constraint === 'format')).toBe(true);
  });

  it('persons out of range returns error', () => {
    const transfer: TransferFormData = {
      ...validTransfer,
      persons: 51,
    };
    const errors = validateTransfer(transfer, 0, '2025-09-15', '2025-09-18');
    expect(errors.some((e) => e.field === 'transfers[0].persons' && e.constraint === 'range')).toBe(true);
  });
});
