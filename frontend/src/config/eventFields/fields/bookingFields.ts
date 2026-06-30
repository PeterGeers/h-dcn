/**
 * Event Field Definitions - Booking Fields
 *
 * Fields with group: 'booking'
 * These fields support the closed community booking module:
 * password gate, invitee registry, and claims.
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const bookingFields: Record<string, FieldDefinition> = {
  event_password: {
    key: 'event_password',
    label: 'Event Wachtwoord',
    dataType: 'string',
    inputType: 'password',
    group: 'booking',
    order: 1,
    permissions: createPermissionConfig('system', 'admin', { writeOnly: true }),
    helpText: 'Bcrypt-hashed wachtwoord voor de password gate. Wordt nooit in plaintext geretourneerd via API.',
    width: 'medium',
  },

  registry_config: {
    key: 'registry_config',
    label: 'Registry Configuratie',
    dataType: 'map',
    inputType: 'json',
    group: 'booking',
    order: 2,
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Configuratie voor het invitee registry: s3_path, row_label, claim_mode, max_delegates_per_row, allow_logo_upload.',
    width: 'full',
  },

  registry_claims: {
    key: 'registry_claims',
    label: 'Registry Claims',
    dataType: 'map',
    inputType: 'json',
    group: 'booking',
    order: 3,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Runtime claim state: map van row_id → { member_id, email, name, claimed_at }. Beheerd door het onboard-endpoint.',
    width: 'full',
  },
};
