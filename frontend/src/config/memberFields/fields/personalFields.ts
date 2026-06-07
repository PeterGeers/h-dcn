/**
 * Member Field Definitions - Personal Information
 *
 * Fields with group: 'personal'
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const personalFields: Record<string, FieldDefinition> = {
  voornaam: {
    key: 'voornaam',
    label: 'Voornaam',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 1,
    required: true,
    validation: [
      { type: 'required', message: 'Voornaam is verplicht' },
      { type: 'min_length', value: 1, message: 'Voornaam moet minimaal 1 karakter bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      view: [...createPermissionConfig('member', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', true).edit, 'verzoek_lid']
    },
    placeholder: 'Voer uw voornaam in',
    helpText: 'Uw officiële voornaam',
    width: 'medium'
  },

  achternaam: {
    key: 'achternaam',
    label: 'Achternaam',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 2,
    required: true,
    validation: [
      { type: 'required', message: 'Achternaam is verplicht' },
      { type: 'min_length', value: 1, message: 'Achternaam moet minimaal 1 karakter bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      view: [...createPermissionConfig('member', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', true).edit, 'verzoek_lid']
    },
    placeholder: 'Voer uw achternaam in',
    helpText: 'Uw officiële achternaam',
    width: 'medium'
  },

  initialen: {
    key: 'initialen',
    label: 'Initialen',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 3,
    validation: [
      { type: 'max_length', value: 10, message: 'Initialen mogen maximaal 10 karakters bevatten' },
      { type: 'pattern', value: '^[A-Z]+(\\.[A-Z]+)*\\.?$', message: 'Initialen moeten hoofdletters zijn, gescheiden door punten (bijv. J.P.)' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      view: [...createPermissionConfig('member', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', true).edit, 'verzoek_lid']
    },
    placeholder: 'Bijv. J.P.',
    helpText: 'Uw initialen met punten',
    width: 'small'
  },

  tussenvoegsel: {
    key: 'tussenvoegsel',
    label: 'Tussenvoegsel',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 4,
    validation: [
      { type: 'max_length', value: 20, message: 'Tussenvoegsel mag maximaal 20 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      view: [...createPermissionConfig('member', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', true).edit, 'verzoek_lid']
    },
    placeholder: 'Bijv. van, de, van der',
    helpText: 'Tussenvoegsel in uw naam',
    width: 'small'
  },

  korte_naam: {
    key: 'korte_naam',
    label: 'Korte naam',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 5,
    computed: true,
    computeFrom: ['voornaam', 'tussenvoegsel', 'achternaam'],
    computeFunction: 'concatenateName',
    permissions: createPermissionConfig('member', 'none', false),
    helpText: 'Automatisch samengestelde naam',
    width: 'large'
  },

  geboortedatum: {
    key: 'geboortedatum',
    label: 'Geboortedatum',
    dataType: 'date',
    inputType: 'date',
    group: 'personal',
    order: 5,
    validation: [
      { type: 'required', message: 'Geboortedatum is verplicht' }
    ],
    permissions: {
      ...createPermissionConfig('admin', 'admin', true),
      regionalRestricted: true,
      view: [...createPermissionConfig('admin', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('admin', 'admin', true).edit, 'verzoek_lid']
    },
    displayFormat: 'dd-MM-yyyy',
    placeholder: 'dd-mm-jjjj',
    helpText: 'Uw geboortedatum voor leeftijdsverificatie',
    width: 'medium'
  },

  leeftijd: {
    key: 'leeftijd',
    label: 'Leeftijd',
    dataType: 'number',
    inputType: 'number',
    group: 'personal',
    order: 6,
    computed: true,
    computeFrom: 'geboortedatum',
    computeFunction: 'calculateAge',
    permissions: {
      ...createPermissionConfig('admin', 'none', false),
      regionalRestricted: true
    },
    helpText: 'Automatisch berekende leeftijd',
    suffix: 'jaar',
    width: 'small'
  },

  verjaardag: {
    key: 'verjaardag',
    label: 'Verjaardag',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 7,
    computed: true,
    computeFrom: 'geboortedatum',
    computeFunction: 'extractBirthday',
    permissions: {
      ...createPermissionConfig('admin', 'none', false),
      regionalRestricted: true
    },
    helpText: 'Dag en maand van verjaardag (bijv. September 26)',
    width: 'small'
  },

  geslacht: {
    key: 'geslacht',
    label: 'Geslacht',
    dataType: 'enum',
    inputType: 'select',
    group: 'personal',
    order: 6,
    enumOptions: ['M', 'V', 'X', 'N'],
    validation: [
      { type: 'required', message: 'Geslacht is verplicht' }
    ],
    permissions: {
      ...createPermissionConfig('admin', 'admin', true),
      regionalRestricted: true,
      view: [...createPermissionConfig('admin', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('admin', 'admin', true).edit, 'verzoek_lid']
    },
    placeholder: 'Selecteer geslacht',
    helpText: 'M = Man, V = Vrouw, X = Onbepaald, N = Niet opgegeven',
    width: 'small'
  },

  email: {
    key: 'email',
    label: 'Email',
    dataType: 'string',
    inputType: 'email',
    group: 'personal',
    order: 7,
    required: true,
    validation: [
      { type: 'required', message: 'Email is verplicht' },
      { type: 'email', message: 'Voer een geldig emailadres in' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      view: [...createPermissionConfig('member', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', true).edit, 'verzoek_lid']
    },
    placeholder: 'naam@voorbeeld.nl',
    helpText: 'Uw primaire emailadres (gekoppeld aan uw account, niet wijzigbaar)',
    width: 'large'
  },

  telefoon: {
    key: 'telefoon',
    label: 'Telefoon',
    dataType: 'string',
    inputType: 'tel',
    group: 'personal',
    order: 8,
    validation: [
      { type: 'phone', message: 'Voer een geldig telefoonnummer in' },
      { type: 'min_length', value: 10, message: 'Telefoonnummer moet minimaal 10 cijfers bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true,
      view: [...createPermissionConfig('member', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('member', 'admin', true).edit, 'verzoek_lid']
    },
    placeholder: '06-12345678 of +31612345678',
    helpText: 'Uw telefoonnummer voor contact',
    width: 'medium'
  },

  minderjarigNaam: {
    key: 'minderjarigNaam',
    label: 'Ouder/Verzorger',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 10,
    validation: [
      {
        type: 'required',
        message: 'Naam ouder/verzorger is verplicht voor minderjarige leden',
        condition: { field: 'geboortedatum', operator: 'age_less_than', value: 18 }
      },
      { type: 'min_length', value: 2, message: 'Naam moet minimaal 2 karakters bevatten' },
      { type: 'max_length', value: 100, message: 'Naam mag maximaal 100 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('admin', 'admin', true),
      regionalRestricted: true,
      view: [...createPermissionConfig('admin', 'admin', true).view, 'verzoek_lid'],
      edit: [...createPermissionConfig('admin', 'admin', true).edit, 'verzoek_lid']
    },
    showWhen: [
      { field: 'geboortedatum', operator: 'age_less_than', value: 18 }
    ],
    placeholder: 'Naam van ouder of verzorger',
    helpText: 'Verplicht voor leden onder de 18 jaar',
    width: 'large'
  },
};
