/**
 * Member Field Configuration System - Modal Configurations
 *
 * Modal context definitions and helper functions for creating modal layouts.
 * Interfaces are imported from ./types (ModalFieldConfig, ModalGroupConfig, etc.)
 */

import type {
  ConditionalRule,
  FieldGroup,
  HDCNGroup,
  ModalContextConfig,
  ModalFieldConfig,
  ModalGroupConfig,
  ModalSectionConfig,
} from './types';

// ============================================================================
// MODAL CONTEXT HELPER FUNCTIONS
// ============================================================================

/**
 * Create a section configuration using field groups
 */
export function createGroupBasedSection(
  name: string,
  title: string,
  order: number,
  groups: ModalGroupConfig[],
  options?: {
    collapsible?: boolean;
    defaultExpanded?: boolean;
    showWhen?: ConditionalRule[];
    permissions?: { view: HDCNGroup[]; edit?: HDCNGroup[]; };
    additionalFields?: ModalFieldConfig[];
  }
): ModalSectionConfig {
  return {
    name,
    title,
    order,
    collapsible: options?.collapsible,
    defaultExpanded: options?.defaultExpanded,
    groups,
    fields: options?.additionalFields,
    showWhen: options?.showWhen,
    permissions: options?.permissions
  };
}

/**
 * Create a simple group configuration
 */
export function createGroupConfig(
  group: FieldGroup,
  order: number = 1,
  options?: {
    excludeFields?: string[];
    includeFields?: string[];
    fieldOverrides?: Partial<ModalFieldConfig>[];
  }
): ModalGroupConfig {
  return {
    group,
    visible: true,
    order,
    excludeFields: options?.excludeFields,
    includeFields: options?.includeFields,
    fieldOverrides: options?.fieldOverrides
  };
}

/**
 * Create a complete modal context using group-based sections
 */
export function createGroupBasedModalContext(
  name: string,
  description: string,
  sections: ModalSectionConfig[],
  permissions: { view: HDCNGroup[]; edit?: HDCNGroup[]; }
): ModalContextConfig {
  return {
    name,
    description,
    sections,
    permissions
  };
}

// ============================================================================
// MEMBER MODAL CONTEXTS
// ============================================================================

export const MEMBER_MODAL_CONTEXTS: Record<string, ModalContextConfig> = {
  // Standard member view modal
  memberView: {
    name: 'Member View',
    description: 'Complete member information modal for viewing/editing',
    sections: [
      {
        name: 'personal',
        title: 'Persoonlijke Informatie',
        order: 1,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'korte_naam', visible: true, order: 1, span: 2 },
          { fieldKey: 'initialen', visible: true, order: 2, span: 1 },
          { fieldKey: 'geboortedatum', visible: true, order: 3, span: 1 },
          { fieldKey: 'geslacht', visible: true, order: 6, span: 1 },
          { fieldKey: 'email', visible: true, order: 7, span: 2 },
          { fieldKey: 'telefoon', visible: true, order: 8, span: 1 },
          {
            fieldKey: 'minderjarigNaam',
            visible: true,
            order: 10,
            span: 3,
            conditionalVisible: [
              { field: 'geboortedatum', operator: 'age_less_than', value: 18 }
            ]
          }
        ],
        permissions: {
          view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'address',
        title: 'Adresgegevens',
        order: 2,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'straat', visible: true, order: 1, span: 2 },
          { fieldKey: 'postcode', visible: true, order: 2, span: 1 },
          { fieldKey: 'woonplaats', visible: true, order: 3, span: 2 },
          { fieldKey: 'land', visible: true, order: 4, span: 1 }
        ],
        permissions: {
          view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'membership',
        title: 'Lidmaatschap',
        order: 3,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'lidnummer', visible: true, readOnly: true, order: 1, span: 1 },
          { fieldKey: 'status', visible: true, order: 2, span: 1 },
          { fieldKey: 'lidmaatschap', visible: true, order: 3, span: 1 },
          { fieldKey: 'regio', visible: true, order: 4, span: 1 },
          { fieldKey: 'ingangsdatum', visible: true, order: 5, span: 1 },
          { fieldKey: 'jaren_lid', visible: true, readOnly: true, order: 6, span: 1 },
          { fieldKey: 'clubblad', visible: true, order: 7, span: 1 },
          { fieldKey: 'nieuwsbrief', visible: true, order: 8, span: 1 },
          { fieldKey: 'privacy', visible: true, order: 9, span: 1 },
          { fieldKey: 'wiewatwaar', visible: true, order: 10, span: 3 }
        ],
        permissions: {
          view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'motor',
        title: 'Motorgegevens',
        order: 4,
        collapsible: true,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'motormerk', visible: true, order: 1, span: 1 },
          { fieldKey: 'motortype', visible: true, order: 2, span: 2 },
          { fieldKey: 'bouwjaar', visible: true, order: 3, span: 1 },
          { fieldKey: 'kenteken', visible: true, order: 4, span: 1 }
        ],
        showWhen: [
          { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
          { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
        ],
        permissions: {
          view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'financial',
        title: 'Financiële Gegevens',
        order: 5,
        collapsible: true,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'betaalwijze', visible: true, order: 1, span: 1 },
          { fieldKey: 'bankrekeningnummer', visible: true, order: 2, span: 2 }
        ],
        permissions: {
          view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'administrative',
        title: 'Administratieve Gegevens',
        order: 6,
        collapsible: true,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'created_at', visible: true, readOnly: true, order: 4, span: 1 },
          { fieldKey: 'updated_at', visible: true, readOnly: true, order: 5, span: 1 },
          { fieldKey: 'notities', visible: true, order: 6, span: 3 }
        ],
        permissions: {
          view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      }
    ],
    permissions: {
      view: ['hdcnLeden', 'Members_Read', 'Members_CRUD', 'System_User_Management'],
      edit: ['Members_CRUD', 'System_User_Management']
    }
  },

  // Compact member view for quick reference
  memberQuickView: {
    name: 'Member Quick View',
    description: 'Simplified member modal for quick viewing',
    sections: [
      {
        name: 'essential',
        title: 'Basisgegevens',
        order: 1,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'korte_naam', visible: true, readOnly: true, order: 1, span: 2 },
          { fieldKey: 'lidnummer', visible: true, readOnly: true, order: 2, span: 1 },
          { fieldKey: 'email', visible: true, readOnly: true, order: 3, span: 2 },
          { fieldKey: 'telefoon', visible: true, readOnly: true, order: 5, span: 1 },
          { fieldKey: 'regio', visible: true, readOnly: true, order: 6, span: 1 },
          { fieldKey: 'status', visible: true, readOnly: true, order: 7, span: 1 },
          { fieldKey: 'lidmaatschap', visible: true, readOnly: true, order: 8, span: 1 }
        ],
        permissions: {
          view: ['Members_Read', 'Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      }
    ],
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'System_User_Management']
    }
  },

  // Registration form context - GROUP-BASED VERSION
  memberRegistration: {
    name: 'Member Registration',
    description: 'New member registration form using field groups',
    sections: [
      {
        name: 'membership',
        title: 'Lidmaatschap',
        order: 1,
        defaultExpanded: true,
        groups: [
          {
            group: 'membership',
            visible: true,
            order: 1,
            includeFields: ['status', 'lidmaatschap', 'regio', 'clubblad', 'nieuwsbrief', 'privacy', 'wiewatwaar'],
            fieldOverrides: [
              { fieldKey: 'wiewatwaar', span: 3 }
            ]
          }
        ],
        permissions: {
          view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
          edit: ['verzoek_lid', 'Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'personal',
        title: 'Persoonlijke Informatie',
        order: 2,
        defaultExpanded: true,
        groups: [
          {
            group: 'personal',
            visible: true,
            order: 1,
            fieldOverrides: [
              { fieldKey: 'email', span: 2, readOnly: true },
              {
                fieldKey: 'minderjarigNaam',
                span: 3,
                conditionalVisible: [
                  { field: 'geboortedatum', operator: 'age_less_than', value: 18 }
                ]
              }
            ]
          }
        ],
        permissions: {
          view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
          edit: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'address',
        title: 'Adresgegevens',
        order: 3,
        defaultExpanded: true,
        groups: [
          {
            group: 'address',
            visible: true,
            order: 1,
            fieldOverrides: [
              { fieldKey: 'straat', span: 2 },
              { fieldKey: 'woonplaats', span: 2 }
            ]
          }
        ],
        permissions: {
          view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
          edit: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'motor',
        title: 'Motorgegevens',
        order: 4,
        defaultExpanded: true,
        groups: [
          {
            group: 'motor',
            visible: true,
            order: 1,
            fieldOverrides: [
              { fieldKey: 'motortype', span: 2 }
            ]
          }
        ],
        showWhen: [
          { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
          { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
        ],
        permissions: {
          view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
          edit: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'financial',
        title: 'Betaalgegevens',
        order: 5,
        defaultExpanded: true,
        groups: [
          {
            group: 'financial',
            visible: true,
            order: 1,
            fieldOverrides: [
              { fieldKey: 'bankrekeningnummer', span: 2 }
            ]
          }
        ],
        permissions: {
          view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
          edit: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'vrijwaring',
        title: 'Vrijwaring',
        order: 6,
        defaultExpanded: true,
        fields: [],
        permissions: {
          view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
          edit: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'ondergetekende',
        title: 'Ondergetekende',
        order: 7,
        defaultExpanded: true,
        fields: [],
        permissions: {
          view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
          edit: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management']
        }
      }
    ],
    permissions: {
      view: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management'],
      edit: ['verzoek_lid', 'hdcnLeden', 'Members_CRUD', 'System_User_Management']
    }
  },

  // Multi-step membership application form - GROUP-BASED VERSION
  membershipApplication: {
    name: 'Membership Application',
    description: 'Progressive disclosure membership application form using field groups',
    sections: [
      {
        name: 'step1_personal',
        title: 'Stap 1: Wie ben je?',
        order: 1,
        defaultExpanded: true,
        groups: [
          {
            group: 'personal',
            visible: true,
            order: 1,
            fieldOverrides: [
              { fieldKey: 'minderjarigNaam', span: 3, conditionalVisible: [{ field: 'geboortedatum', operator: 'age_less_than', value: 18 }] }
            ]
          }
        ],
        permissions: {
          view: ['Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'step2_address',
        title: 'Stap 2: Waar woon je?',
        order: 2,
        defaultExpanded: false,
        groups: [
          {
            group: 'address',
            visible: true,
            order: 1
          }
        ],
        permissions: {
          view: ['Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'step3_membership',
        title: 'Stap 3: Welk lidmaatschap wil je?',
        order: 3,
        defaultExpanded: false,
        groups: [
          {
            group: 'membership',
            visible: true,
            order: 1,
            includeFields: ['lidmaatschap', 'regio', 'wiewatwaar', 'clubblad', 'nieuwsbrief', 'privacy'],
            fieldOverrides: [
              { fieldKey: 'wiewatwaar', span: 3 }
            ]
          }
        ],
        permissions: {
          view: ['Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'step4_motor',
        title: 'Stap 4: Vertel over je motor',
        order: 4,
        defaultExpanded: false,
        groups: [
          {
            group: 'motor',
            visible: true,
            order: 1,
            fieldOverrides: [
              { fieldKey: 'motortype', span: 2 },
              { fieldKey: 'kenteken', span: 2 }
            ]
          }
        ],
        showWhen: [
          { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
          { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
        ],
        permissions: {
          view: ['Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      },
      {
        name: 'step5_payment',
        title: 'Stap 5: Hoe wil je betalen?',
        order: 5,
        defaultExpanded: false,
        groups: [
          {
            group: 'financial',
            visible: true,
            order: 1,
            fieldOverrides: [
              { fieldKey: 'bankrekeningnummer', span: 2 }
            ]
          }
        ],
        permissions: {
          view: ['Members_CRUD', 'System_User_Management'],
          edit: ['Members_CRUD', 'System_User_Management']
        }
      }
    ],
    permissions: {
      view: ['Members_CRUD', 'System_User_Management'],
      edit: ['Members_CRUD', 'System_User_Management']
    }
  }
};

// ============================================================================
// EXAMPLE: SIMPLIFIED GROUP-BASED REGISTRATION FORM
// ============================================================================

/**
 * Example of how to create a registration form using the new group-based system
 * This is much more concise than listing individual fields
 */
export const SIMPLIFIED_REGISTRATION_EXAMPLE = createGroupBasedModalContext(
  'Simplified Registration',
  'Example of group-based registration form',
  [
    // Step 1: Personal info - just reference the group
    createGroupBasedSection(
      'personal_info',
      'Persoonlijke Gegevens',
      1,
      [createGroupConfig('personal', 1)],
      { defaultExpanded: true }
    ),

    // Step 2: Address + nationality
    createGroupBasedSection(
      'address_info',
      'Adresgegevens',
      2,
      [createGroupConfig('address', 1)],
      {
        defaultExpanded: false
      }
    ),

    // Step 3: Membership preferences
    createGroupBasedSection(
      'membership_info',
      'Lidmaatschap',
      3,
      [createGroupConfig('membership', 1, {
        includeFields: ['lidmaatschap', 'regio', 'clubblad', 'nieuwsbrief', 'privacy', 'wiewatwaar']
      })],
      { defaultExpanded: false }
    ),

    // Step 4: Motor (conditional)
    createGroupBasedSection(
      'motor_info',
      'Motorgegevens',
      4,
      [createGroupConfig('motor', 1)],
      {
        defaultExpanded: false,
        showWhen: [
          { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
          { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
        ]
      }
    ),

    // Step 5: Payment
    createGroupBasedSection(
      'payment_info',
      'Betaalgegevens',
      5,
      [createGroupConfig('financial', 1)],
      { defaultExpanded: false }
    )
  ],
  {
    view: ['Members_CRUD', 'System_User_Management'],
    edit: ['Members_CRUD', 'System_User_Management']
  }
);

// ============================================================================
// ULTRA-SIMPLIFIED REGISTRATION USING HELPER FUNCTIONS
// ============================================================================

/**
 * Ultra-simplified registration form using the helper functions
 * This shows how concise the configuration can be
 */
export const ULTRA_SIMPLE_REGISTRATION = createGroupBasedModalContext(
  'Ultra Simple Registration',
  'Minimal configuration using helper functions',
  [
    // Personal info with email spanning 2 columns
    createGroupBasedSection(
      'personal',
      'Persoonlijke Informatie',
      1,
      [createGroupConfig('personal', 1, {
        fieldOverrides: [
          { fieldKey: 'email', span: 2 },
          { fieldKey: 'minderjarigNaam', span: 3, conditionalVisible: [{ field: 'geboortedatum', operator: 'age_less_than', value: 18 }] }
        ]
      })],
      { defaultExpanded: true }
    ),

    // Address info with street spanning 2 columns
    createGroupBasedSection(
      'address',
      'Adresgegevens',
      2,
      [createGroupConfig('address', 1, {
        fieldOverrides: [
          { fieldKey: 'straat', span: 2 },
          { fieldKey: 'postcode', span: 1 },
          { fieldKey: 'woonplaats', span: 2 }
        ]
      })],
      { defaultExpanded: true }
    ),

    // Membership info - only specific fields
    createGroupBasedSection(
      'membership',
      'Lidmaatschap',
      3,
      [createGroupConfig('membership', 1, {
        includeFields: ['lidmaatschap', 'regio', 'clubblad', 'nieuwsbrief', 'privacy', 'wiewatwaar'],
        fieldOverrides: [{ fieldKey: 'wiewatwaar', span: 3 }]
      })],
      { defaultExpanded: true }
    ),

    // Motor info (conditional)
    createGroupBasedSection(
      'motor',
      'Motorgegevens',
      4,
      [createGroupConfig('motor', 1, {
        fieldOverrides: [{ fieldKey: 'motortype', span: 2 }]
      })],
      {
        defaultExpanded: true,
        showWhen: [
          { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
          { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
        ]
      }
    ),

    // Payment info
    createGroupBasedSection(
      'financial',
      'Betaalgegevens',
      5,
      [createGroupConfig('financial', 1, {
        fieldOverrides: [{ fieldKey: 'bankrekeningnummer', span: 2 }]
      })],
      { defaultExpanded: true }
    )
  ],
  {
    view: ['hdcnLeden', 'Members_CRUD', 'System_User_Management'],
    edit: ['hdcnLeden', 'Members_CRUD', 'System_User_Management']
  }
);
