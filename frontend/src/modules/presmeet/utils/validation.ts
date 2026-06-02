/**
 * Client-side validation helpers for the PresMeet booking form.
 *
 * Validates delegate, guest, and transfer form data before submission.
 * Draft saves bypass validation (Requirement 8.6).
 */

import {
  DelegateFormData,
  GuestFormData,
  TransferFormData,
  ValidationError,
  Gender,
  TshirtSize,
  TransferDirection,
  Airport,
} from '../types/presmeet';

const VALID_GENDERS: Gender[] = ['male', 'female'];
const VALID_SIZES: TshirtSize[] = ['S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL'];
const VALID_DIRECTIONS: TransferDirection[] = ['pickup', 'dropoff'];
const VALID_AIRPORTS: Airport[] = ['AMS', 'RTM', 'EIN'];

/**
 * Validate a delegate entry. Returns a list of field-level errors.
 */
export function validateDelegate(
  delegate: DelegateFormData,
  index: number
): ValidationError[] {
  const errors: ValidationError[] = [];
  const prefix = `delegates[${index}]`;

  // Name: required, 1-100 chars
  if (!delegate.name || delegate.name.trim().length === 0) {
    errors.push({
      field: `${prefix}.name`,
      message: 'Name is required',
      constraint: 'required',
    });
  } else if (delegate.name.trim().length > 100) {
    errors.push({
      field: `${prefix}.name`,
      message: 'Name must be 100 characters or fewer',
      constraint: 'max_length',
    });
  }

  // Role: required, 1-100 chars
  if (!delegate.role || delegate.role.trim().length === 0) {
    errors.push({
      field: `${prefix}.role`,
      message: 'Role is required',
      constraint: 'required',
    });
  } else if (delegate.role.trim().length > 100) {
    errors.push({
      field: `${prefix}.role`,
      message: 'Role must be 100 characters or fewer',
      constraint: 'max_length',
    });
  }

  // T-shirt validation (optional, but if present must be complete)
  if (delegate.tshirt) {
    if (!delegate.tshirt.gender || !VALID_GENDERS.includes(delegate.tshirt.gender)) {
      errors.push({
        field: `${prefix}.tshirt.gender`,
        message: 'Gender must be male or female',
        constraint: 'enum',
      });
    }
    if (!delegate.tshirt.size || !VALID_SIZES.includes(delegate.tshirt.size)) {
      errors.push({
        field: `${prefix}.tshirt.size`,
        message: `Size must be one of: ${VALID_SIZES.join(', ')}`,
        constraint: 'enum',
      });
    }
  }

  return errors;
}

/**
 * Validate a guest entry. Returns a list of field-level errors.
 */
export function validateGuest(
  guest: GuestFormData,
  index: number
): ValidationError[] {
  const errors: ValidationError[] = [];
  const prefix = `guests[${index}]`;

  // Name: required, 1-100 chars
  if (!guest.name || guest.name.trim().length === 0) {
    errors.push({
      field: `${prefix}.name`,
      message: 'Name is required',
      constraint: 'required',
    });
  } else if (guest.name.trim().length > 100) {
    errors.push({
      field: `${prefix}.name`,
      message: 'Name must be 100 characters or fewer',
      constraint: 'max_length',
    });
  }

  // T-shirt validation (optional, but if present must be complete)
  if (guest.tshirt) {
    if (!guest.tshirt.gender || !VALID_GENDERS.includes(guest.tshirt.gender)) {
      errors.push({
        field: `${prefix}.tshirt.gender`,
        message: 'Gender must be male or female',
        constraint: 'enum',
      });
    }
    if (!guest.tshirt.size || !VALID_SIZES.includes(guest.tshirt.size)) {
      errors.push({
        field: `${prefix}.tshirt.size`,
        message: `Size must be one of: ${VALID_SIZES.join(', ')}`,
        constraint: 'enum',
      });
    }
  }

  return errors;
}

/**
 * Validate a transfer entry. Returns a list of field-level errors.
 */
export function validateTransfer(
  transfer: TransferFormData,
  index: number,
  eventStartDate?: string,
  eventEndDate?: string
): ValidationError[] {
  const errors: ValidationError[] = [];
  const prefix = `transfers[${index}]`;

  // Direction: required, must be pickup or dropoff
  if (!transfer.direction || !VALID_DIRECTIONS.includes(transfer.direction)) {
    errors.push({
      field: `${prefix}.direction`,
      message: 'Direction must be pickup or dropoff',
      constraint: 'enum',
    });
  }

  // Airport: required, must be AMS, RTM, or EIN
  if (!transfer.airport || !VALID_AIRPORTS.includes(transfer.airport)) {
    errors.push({
      field: `${prefix}.airport`,
      message: 'Airport must be AMS, RTM, or EIN',
      constraint: 'enum',
    });
  }

  // Flight: required, 2-10 chars
  if (!transfer.flight || transfer.flight.trim().length === 0) {
    errors.push({
      field: `${prefix}.flight`,
      message: 'Flight number is required',
      constraint: 'required',
    });
  } else if (transfer.flight.trim().length < 2) {
    errors.push({
      field: `${prefix}.flight`,
      message: 'Flight number must be at least 2 characters',
      constraint: 'min_length',
    });
  } else if (transfer.flight.trim().length > 10) {
    errors.push({
      field: `${prefix}.flight`,
      message: 'Flight number must be 10 characters or fewer',
      constraint: 'max_length',
    });
  }

  // Date: required, ISO format, within event range
  if (!transfer.date || transfer.date.trim().length === 0) {
    errors.push({
      field: `${prefix}.date`,
      message: 'Date is required',
      constraint: 'required',
    });
  } else {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(transfer.date)) {
      errors.push({
        field: `${prefix}.date`,
        message: 'Date must be in YYYY-MM-DD format',
        constraint: 'format',
      });
    } else if (eventStartDate && eventEndDate) {
      if (transfer.date < eventStartDate || transfer.date > eventEndDate) {
        errors.push({
          field: `${prefix}.date`,
          message: `Date must be between ${eventStartDate} and ${eventEndDate}`,
          constraint: 'range',
        });
      }
    }
  }

  // Time: required, HH:MM format
  if (!transfer.time || transfer.time.trim().length === 0) {
    errors.push({
      field: `${prefix}.time`,
      message: 'Time is required',
      constraint: 'required',
    });
  } else {
    const timeRegex = /^([01]\d|2[0-3]):[0-5]\d$/;
    if (!timeRegex.test(transfer.time)) {
      errors.push({
        field: `${prefix}.time`,
        message: 'Time must be in HH:MM 24-hour format',
        constraint: 'format',
      });
    }
  }

  // Persons: required, integer 1-50
  if (transfer.persons == null || transfer.persons === 0) {
    errors.push({
      field: `${prefix}.persons`,
      message: 'Number of persons is required',
      constraint: 'required',
    });
  } else if (!Number.isInteger(transfer.persons) || transfer.persons < 1 || transfer.persons > 50) {
    errors.push({
      field: `${prefix}.persons`,
      message: 'Persons must be an integer between 1 and 50',
      constraint: 'range',
    });
  }

  return errors;
}

/**
 * Get error message for a specific field path from a list of errors.
 */
export function getFieldError(
  errors: ValidationError[],
  fieldPath: string
): string | undefined {
  const error = errors.find((e) => e.field === fieldPath);
  return error?.message;
}
