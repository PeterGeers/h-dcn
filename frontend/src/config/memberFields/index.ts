/**
 * Member Field Configuration System - Barrel Export
 *
 * Re-exports all symbols from sub-modules for backward compatibility.
 * Existing imports (`from '../config/memberFields'`) continue working unchanged.
 */

import type { FieldDefinition, EmailNotificationConfig } from './types';
import {
  personalFields,
  addressFields,
  membershipFields,
  motorFields,
  financialFields,
  administrativeFields,
} from './fields';

// ============================================================================
// ASSEMBLED FIELD REGISTRY
// ============================================================================

/**
 * Complete field registry assembled from group-specific partials.
 */
export const MEMBER_FIELDS: Record<string, FieldDefinition> = {
  ...personalFields,
  ...addressFields,
  ...membershipFields,
  ...motorFields,
  ...financialFields,
  ...administrativeFields,
};

// ============================================================================
// EMAIL CONFIGURATION
// ============================================================================

export const MEMBERSHIP_EMAIL_CONFIG: EmailNotificationConfig = {
  enabled: true,
  templates: {
    applicantConfirmation: 'membership-application-confirmation',
    adminNotification: 'membership-application-admin-notification'
  },
  recipients: {
    admin: ['ledenadministratie@h-dcn.nl'],
    cc: [],
    bcc: []
  },
  triggers: {
    onSubmission: true,
    onStatusChange: true,
    onApproval: true,
    onRejection: false
  }
};

// ============================================================================
// RE-EXPORTS FROM SUB-MODULES
// ============================================================================

// Types (all interfaces and type aliases)
export * from './types';

// Permissions (createPermissionConfig, ViewLevel, EditLevel)
export * from './permissions';

// Table configuration (MEMBER_TABLE_CONTEXTS, table utility functions)
export * from './tableConfig';

// Modal configuration (MEMBER_MODAL_CONTEXTS, modal builder functions, example configs)
export * from './modalConfig';

// Helper functions (getModalContext, getVisibleSections, getFieldsByGroup, etc.)
export * from './helpers';

// Field partials (for direct access when needed)
export {
  personalFields,
  addressFields,
  membershipFields,
  motorFields,
  financialFields,
  administrativeFields,
} from './fields';
