/**
 * Member Field Definitions - Membership Information
 *
 * Fields with group: 'membership'
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const membershipFields: Record<string, FieldDefinition> = {
  status: {
    key: 'status',
    label: 'Status',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 1,
    required: true,
    enumOptions: ['Actief', 'Opgezegd', 'wachtRegio', 'Aangemeld', 'Geschorst', 'HdcnAccount', 'Club', 'Sponsor', 'Overig'],
    validation: [
      { type: 'required', message: 'Status is verplicht' }
    ],
    permissions: {
      ...createPermissionConfig('admin', 'admin', false),
      regionalRestricted: true
    },
    placeholder: 'Selecteer status',
    helpText: 'Huidige lidmaatschapsstatus',
    width: 'medium'
  },

  lidmaatschap: {
    key: 'lidmaatschap',
    label: 'Lidmaatschap',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 2,
    required: true,
    enumOptions: ['Gewoon lid', 'Gezins lid', 'Donateur', 'Gezins donateur', 'Erelid', 'Overig'],
    // Role-based enum filtering - restrict certain membership types to specific roles
    enumPermissions: {
      'Erelid': ['Members_CRUD', 'System_User_Management'], // Only full CRUD roles can see/assign Erelid
      'Overig': ['Members_CRUD', 'System_User_Management']   // Only full CRUD roles can see/assign Other
    },
    validation: [
      { type: 'required', message: 'Lidmaatschap is verplicht' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', false),
      regionalRestricted: true,
      view: [...createPermissionConfig('member', 'admin', false).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', false).edit, 'verzoek_lid']
    },
    placeholder: 'Selecteer lidmaatschapstype',
    helpText: 'Type lidmaatschap bepaalt rechten en contributie',
    width: 'medium',
    // Allow new applicants to select membership type
    conditionalEdit: {
      condition: { field: 'status', operator: 'equals', value: 'Aangemeld' },
      permissions: createPermissionConfig('member', 'self', true)
    }
  },

  regio: {
    key: 'regio',
    label: 'Regio',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 3,
    required: true,
    enumOptions: [
      'Noord-Holland',
      'Zuid-Holland',
      'Friesland',
      'Utrecht',
      'Oost',
      'Limburg',
      'Groningen/Drenthe',
      'Brabant/Zeeland',
      'Duitsland',
      'Overig'
    ],
    // Role-based enum filtering - restrict Other to specific roles
    enumPermissions: {
      'Overig': ['Members_CRUD', 'System_User_Management'] // Only full CRUD roles can see/assign Other
    },
    validation: [
      { type: 'required', message: 'Regio is verplicht' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', false),
      regionalRestricted: true,
      view: [...createPermissionConfig('member', 'admin', false).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', false).edit, 'verzoek_lid']
    },
    placeholder: 'Selecteer uw regio',
    helpText: 'H-DCN regio waar u lid van bent',
    width: 'medium',
    // Conditional edit permissions for new applicants
    conditionalEdit: {
      condition: { field: 'status', operator: 'equals', value: 'Aangemeld' },
      permissions: createPermissionConfig('member', 'self', true)
    }
  },

  lidnummer: {
    key: 'lidnummer',
    label: 'Lidnummer',
    dataType: 'number',
    inputType: 'number',
    group: 'membership',
    order: 4,
    computed: true,
    permissions: {
      ...createPermissionConfig('member', 'none', false),
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid', 'Erelid']
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Erelid' }
    ],
    helpText: 'Lidnummer van het lid'
  },

  clubblad: {
    key: 'clubblad',
    label: 'Clubblad',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 5,
    enumOptions: ['Digitaal', 'Papier', 'Geen'],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    placeholder: 'Selecteer clubblad voorkeur',
    helpText: 'Hoe wilt u het clubblad ontvangen?',
    width: 'medium',
    defaultValue: 'Digitaal'
  },

  nieuwsbrief: {
    key: 'nieuwsbrief',
    label: 'Nieuwsbrief',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 6,
    enumOptions: ['Ja', 'Nee'],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    placeholder: 'Nieuwsbrief ontvangen?',
    helpText: 'Wilt u de nieuwsbrief ontvangen?',
    width: 'small',
    defaultValue: 'Ja'
  },

  privacy: {
    key: 'privacy',
    label: 'Privacy',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 9,
    enumOptions: ['Ja', 'Nee'],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    helpText: 'Toestemming voor gebruik gegevens',
    placeholder: 'Privacy toestemming',
    width: 'small',
    defaultValue: 'Nee'
  },

  wiewatwaar: {
    key: 'wiewatwaar',
    label: 'Hoe gevonden',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 9,
    enumOptions: [
      'Eerder lid',
      'Facebook',
      'Familie',
      'Harleydag',
      'Instagram',
      'Lid H-DCN',
      'Internet',
      'Openingsrit',
      'Vrienden',
      'Website H-DCN',
      'The Young Ones',
      'Bigtwin Bike Expo'
    ],
    validation: [
      {
        type: 'required',
        message: 'Selecteer hoe u de H-DCN heeft gevonden',
        condition: { field: 'member_id', operator: 'not_exists' } // Only required for new applications
      }
    ],
    permissions: {
      ...createPermissionConfig('admin', 'admin', true),
      regionalRestricted: true
    },
    placeholder: 'Selecteer hoe u ons heeft gevonden',
    helpText: 'Hoe heeft u de H-DCN gevonden?',
    width: 'large'
  },

  ingangsdatum: {
    key: 'tijdstempel',
    label: 'Lid sinds',
    dataType: 'date',
    inputType: 'date',
    group: 'membership',
    order: 7,
    permissions: {
      ...createPermissionConfig('member', 'admin', false),
      regionalRestricted: true
    },
    displayFormat: 'dd-MM-yyyy',
    helpText: 'Datum waarop het lidmaatschap is ingegaan'
  },

  jaren_lid: {
    key: 'jaren_lid',
    label: 'Aantal jaren lid',
    dataType: 'number',
    inputType: 'number',
    group: 'membership',
    order: 8,
    permissions: createPermissionConfig('member', 'none', false),
    computed: true,
    computeFrom: 'tijdstempel',
    computeFunction: 'yearsDifference',
    helpText: 'Automatisch berekend uit Lid sinds datum',
    suffix: 'jaar'
  },
};
