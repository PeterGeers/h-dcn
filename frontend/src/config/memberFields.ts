/**
 * Member Field Configuration System - Base Field Registry
 * 
 * This file defines all possible member fields with comprehensive metadata
 * for use across different contexts (table, view, edit, forms).
 */

export type HDCNGroup = 'hdcnLeden' | 'System_CRUD_All' | 'Members_Read_All' | 'Members_CRUD_All' | 'Members_Status_Approve' | 'System_User_Management' | 'National_Chairman' | 'National_Secretary' | 'Communication_Read_All' | 'Communication_CRUD_All' | 'Club_Magazine_Editorial' | 'Event_Organizer';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export type DataType = 'string' | 'date' | 'number' | 'boolean' | 'enum';
export type InputType = 'text' | 'email' | 'date' | 'select' | 'textarea' | 'number' | 'tel' | 'url' | 'iban';
export type FieldGroup = 'personal' | 'address' | 'membership' | 'motor' | 'financial' | 'administrative';

export interface ConditionalRule {
  field: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'exists' | 'not_exists' | 'age_less_than';
  value?: any;
}

export interface ValidationRule {
  type: 'required' | 'email' | 'phone' | 'postal_code' | 'iban' | 'min_length' | 'max_length' | 'pattern' | 'custom';
  value?: any;
  message?: string;
  condition?: ConditionalRule;
}

export interface PermissionConfig {
  view: HDCNGroup[];
  edit: HDCNGroup[];
  selfService?: boolean; // Can members edit their own data
  regionalRestricted?: boolean; // Restricted to regional access
  membershipTypeRestricted?: string[]; // Only for specific membership types
}

export interface FieldDefinition {
  key: string;
  label: string;
  dataType: DataType;
  inputType: InputType;
  group: FieldGroup;
  order: number; // Display order within group
  required?: boolean | ConditionalRule;
  validation?: ValidationRule[];
  permissions?: PermissionConfig;
  
  // UI Properties
  placeholder?: string;
  helpText?: string;
  width?: 'small' | 'medium' | 'large' | 'full';
  
  // Data Properties
  enumOptions?: string[]; // For select/enum fields
  defaultValue?: any;
  
  // Conditional Logic
  showWhen?: ConditionalRule[];
  hideWhen?: ConditionalRule[];
  conditionalEdit?: {
    condition: ConditionalRule;
    permissions: PermissionConfig;
  };
  
  // Display Properties
  displayFormat?: string; // For dates, numbers, etc.
  prefix?: string; // € for currency
  suffix?: string; // % for percentages
  
  // Computed Fields
  computed?: boolean;
  computeFrom?: string;
  computeFunction?: string;
}

// ============================================================================
// FIELD REGISTRY
// ============================================================================

export const MEMBER_FIELDS: Record<string, FieldDefinition> = {
  // ========================================
  // PERSONAL INFORMATION
  // ========================================
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'National_Chairman', 'National_Secretary'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'National_Chairman', 'National_Secretary'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true
    },
    placeholder: 'Bijv. van, de, van der',
    helpText: 'Tussenvoegsel in uw naam',
    width: 'small'
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
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'National_Secretary'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    displayFormat: 'dd-MM-yyyy',
    placeholder: 'dd-mm-jjjj',
    helpText: 'Uw geboortedatum voor leeftijdsverificatie',
    width: 'medium'
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
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'Communication_Read_All'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true
    },
    placeholder: 'naam@voorbeeld.nl',
    helpText: 'Uw primaire emailadres voor communicatie',
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    placeholder: '06-12345678 of +31612345678',
    helpText: 'Uw telefoonnummer voor contact',
    width: 'medium'
  },

  nationaliteit: {
    key: 'nationaliteit',
    label: 'Nationaliteit',
    dataType: 'string',
    inputType: 'text',
    group: 'personal',
    order: 9,
    validation: [
      { type: 'min_length', value: 2, message: 'Nationaliteit moet minimaal 2 karakters bevatten' },
      { type: 'max_length', value: 50, message: 'Nationaliteit mag maximaal 50 karakters bevatten' }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    defaultValue: 'Nederlandse',
    placeholder: 'Bijv. Nederlandse, Duitse, Belgische',
    helpText: 'Uw nationaliteit',
    width: 'medium'
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    helpText: 'Toestemming voor gebruik gegevens',
    placeholder: 'Privacy toestemming',
    width: 'small',
    defaultValue: 'Nee'
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
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    showWhen: [
      { field: 'geboortedatum', operator: 'age_less_than', value: 18 }
    ],
    placeholder: 'Naam van ouder of verzorger',
    helpText: 'Verplicht voor leden onder de 18 jaar',
    width: 'large'
  },

  // ========================================
  // ADDRESS INFORMATION
  // ========================================
  straat: {
    key: 'straat',
    label: 'Straat',
    dataType: 'string',
    inputType: 'text',
    group: 'address',
    order: 1,
    validation: [
      { type: 'min_length', value: 3, message: 'Straat moet minimaal 3 karakters bevatten' },
      { type: 'max_length', value: 100, message: 'Straat mag maximaal 100 karakters bevatten' }
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    placeholder: 'Straatnaam en huisnummer',
    helpText: 'Uw volledige adres (straat + huisnummer)',
    width: 'large'
  },

postcode: {
  key: 'postcode',
  label: 'Postcode',
  dataType: 'string',
  inputType: 'text',
  group: 'address',
  order: 2,
  validation: [
    // Dutch postcode validation (when land = 'Nederland')
    { 
      type: 'pattern', 
      value: '^[1-9][0-9]{3}\\s?[A-Z]{2}$', 
      message: 'Nederlandse postcode moet format 1234AB hebben',
      condition: { field: 'land', operator: 'equals', value: 'Nederland' }
    },
    // International postcode validation (when land ≠ 'Nederland')
    { 
      type: 'min_length', 
      value: 3, 
      message: 'Postcode moet minimaal 3 karakters bevatten',
      condition: { field: 'land', operator: 'not_equals', value: 'Nederland' }
    },
    { 
      type: 'max_length', 
      value: 15, 
      message: 'Postcode mag maximaal 15 karakters bevatten',
      condition: { field: 'land', operator: 'not_equals', value: 'Nederland' }
    }
  ],
  permissions: {
    view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
    edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
    selfService: true,
    regionalRestricted: true
  },
  placeholder: '1234AB of internationaal formaat',
  helpText: 'Uw postcode',
  width: 'small'
},

  woonplaats: {
    key: 'woonplaats',
    label: 'Woonplaats',
    dataType: 'string',
    inputType: 'text',
    group: 'address',
    order: 3,
    validation: [
      { type: 'min_length', value: 2, message: 'Woonplaats moet minimaal 2 karakters bevatten' },
      { type: 'max_length', value: 50, message: 'Woonplaats mag maximaal 50 karakters bevatten' }
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    placeholder: 'Plaatsnaam',
    helpText: 'Uw woonplaats',
    width: 'medium'
  },

  land: {
    key: 'land',
    label: 'Land',
    dataType: 'string',
    inputType: 'text',
    group: 'address',
    order: 4,
    validation: [
      { type: 'min_length', value: 2, message: 'Land moet minimaal 2 karakters bevatten' },
      { type: 'max_length', value: 50, message: 'Land mag maximaal 50 karakters bevatten' }
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    defaultValue: 'Nederland',
    placeholder: 'Bijv. Nederland, België, Duitsland',
    helpText: 'Het land waar u woont',
    width: 'medium'
  },

  // ========================================
  // MEMBERSHIP INFORMATION
  // ========================================
  status: {
    key: 'status',
    label: 'Status',
    dataType: 'enum',
    inputType: 'select',
    group: 'membership',
    order: 1,
    required: true,
    enumOptions: ['Actief', 'Opgezegd', 'wachtRegio', 'Aangemeld', 'Geschorst','Overig'],
    validation: [
      { type: 'required', message: 'Status is verplicht' }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'Members_Status_Approve', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'Members_Status_Approve'],
      selfService: false,
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
    enumOptions: ['Gewoon lid', 'Gezins lid', 'Donateur', 'Gezins donateur','Erelid','Club','Sponsor', 'HDCNaccount'],
    validation: [
      { type: 'required', message: 'Lidmaatschap is verplicht' }
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: false,
      regionalRestricted: true
    },
    placeholder: 'Selecteer lidmaatschapstype',
    helpText: 'Type lidmaatschap bepaalt rechten en contributie',
    width: 'medium',
    // Allow new applicants to select membership type
    conditionalEdit: {
      condition: { field: 'status', operator: 'equals', value: 'Aangemeld' },
      permissions: {
        view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
        edit: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
        selfService: true // Allow self-service for new applicants
      }
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
      'Noord-Brabant',
      'Zeeland'
    ],
    validation: [
      { type: 'required', message: 'Regio is verplicht' }
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All'],
      selfService: false,
      regionalRestricted: true
    },
    placeholder: 'Selecteer uw regio',
    helpText: 'H-DCN regio waar u lid van bent',
    width: 'medium',
    // Conditional edit permissions for new applicants
    conditionalEdit: {
      condition: { field: 'status', operator: 'equals', value: 'Aangemeld' },
      permissions: {
        view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
        edit: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All'], // New applicants can select their region
        selfService: true // Allow self-service for new applicants
      }
    }
  },

  lidnummer: {
    key: 'lidnummer',
    label: 'Lidnummer',
    dataType: 'number',
    inputType: 'number',
    group: 'membership',
    order: 4,
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: [], // Cannot be edited - automatically calculated
      selfService: false,
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid', 'Erelid']
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Erelid' }
    ],
    computed: true,
    computeFunction: 'nextLidnummer',
    helpText: 'Automatisch toegewezen lidnummer (hoogste bestaande nummer + 1)'
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'Club_Magazine_Editorial'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management', 'Club_Magazine_Editorial'],
      selfService: true,
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
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'Communication_Read_All'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management', 'Communication_CRUD_All'],
      selfService: true,
      regionalRestricted: true
    },
    placeholder: 'Nieuwsbrief ontvangen?',
    helpText: 'Wilt u de nieuwsbrief ontvangen?',
    width: 'small',
    defaultValue: 'Ja'
  },


  wiewatwaar: {
    key: 'wiewatwaar',
    label: 'Hoe gevonden',
    dataType: 'string',
    inputType: 'text',
    group: 'membership',
    order: 9,
    validation: [
      { type: 'max_length', value: 200, message: 'Beschrijving mag maximaal 200 karakters bevatten' }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      regionalRestricted: true
    },
    helpText: 'Hoe heeft u de H-DCN gevonden?'
  },

  notities: {
    key: 'notities',
    label: 'Notities',
    dataType: 'string',
    inputType: 'textarea',
    group: 'administrative',
    order: 7,
    validation: [
      { type: 'max_length', value: 1000, message: 'Notities mogen maximaal 1000 karakters bevatten' }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_CRUD_All', 'System_CRUD_All'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_CRUD_All'],
      selfService: false
    },
    helpText: 'Interne notities voor administratieve doeleinden'
  },

  ingangsdatum: {
    key: 'tijdstempel',
    label: 'Lid sinds',
    dataType: 'date',
    inputType: 'date',
    group: 'membership',
    order: 7,
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All'],
      selfService: false,
      regionalRestricted: true
    },
    displayFormat: 'dd-MM-yyyy',
    helpText: 'Datum waarop het lidmaatschap is ingegaan'
  },

  aanmeldingsjaar: {
    key: 'aanmeldingsjaar',
    label: 'Aanmeldingsjaar',
    dataType: 'number',
    inputType: 'number',
    group: 'administrative',
    order: 1,
    permissions: {
      view: ['System_CRUD_All', 'Members_CRUD_All', 'System_CRUD_All'],
      edit: [], // Cannot be edited - computed field
      selfService: false
    },
    computed: true,
    computeFrom: 'ingangsdatum',
    computeFunction: 'year',
    helpText: 'Automatisch berekend uit Lid sinds datum'
  },

  jaren_lid: {
    key: 'jaren_lid',
    label: 'Aantal jaren lid',
    dataType: 'number',
    inputType: 'number',
    group: 'membership',
    order: 8,
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: [], // Cannot be edited - computed field
      selfService: false
    },
    computed: true,
    computeFrom: 'ingangsdatum',
    computeFunction: 'yearsDifference',
    helpText: 'Automatisch berekend uit Lid sinds datum',
    suffix: 'jaar'
  },

  datum_ondertekening: {
    key: 'datum_ondertekening',
    label: 'Datum ondertekening',
    dataType: 'date',
    inputType: 'date',
    group: 'administrative',
    order: 4,
    permissions: {
      view: ['System_CRUD_All', 'Members_CRUD_All', 'System_CRUD_All'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_CRUD_All'],
      selfService: false
    },
    displayFormat: 'dd-MM-yyyy'
  },

  created_at: {
    key: 'created_at',
    label: 'Record aangemaakt',
    dataType: 'date',
    inputType: 'date',
    group: 'administrative',
    order: 5,
    permissions: {
      view: ['System_CRUD_All', 'System_CRUD_All'],
      edit: [], // Display only - cannot be edited
      selfService: false
    },
    displayFormat: 'dd-MM-yyyy HH:mm:ss',
    helpText: 'Technische datum wanneer record is aangemaakt'
  },

  updated_at: {
    key: 'updated_at',
    label: 'Laatst bijgewerkt',
    dataType: 'date',
    inputType: 'date',
    group: 'administrative',
    order: 6,
    permissions: {
      view: ['System_CRUD_All', 'System_CRUD_All'],
      edit: [], // Display only - cannot be edited
      selfService: false
    },
    displayFormat: 'dd-MM-yyyy HH:mm:ss',
    helpText: 'Technische datum wanneer record laatst is bijgewerkt'
  },

  // ========================================
  // MOTOR INFORMATION
  // ========================================
  motormerk: {
    key: 'motormerk',
    label: 'Motormerk',
    dataType: 'enum',
    inputType: 'select',
    group: 'motor',
    order: 1,
    enumOptions: [
      'Harley-Davidson',
      'Indian',
      'Buell',
      'Eigenbouw'
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: 'Selecteer motormerk',
    helpText: 'Merk van uw motor (alleen voor gewone leden)',
    width: 'medium'
  },

  motortype: {
    key: 'motortype',
    label: 'Motortype',
    dataType: 'string',
    inputType: 'text',
    group: 'motor',
    order: 2,
    validation: [
      { type: 'max_length', value: 50, message: 'Motortype mag maximaal 50 karakters bevatten' }
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: 'Bijv. Sportster, Street Glide',
    helpText: 'Type/model van uw motor',
    width: 'medium'
  },

  bouwjaar: {
    key: 'bouwjaar',
    label: 'Bouwjaar',
    dataType: 'number',
    inputType: 'number',
    group: 'motor',
    order: 3,
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    validation: [
      { type: 'min_length', value: 1900, message: 'Bouwjaar moet na 1900 zijn' },
      { type: 'max_length', value: new Date().getFullYear() + 1, message: `Bouwjaar mag niet in de toekomst liggen` }
    ],
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: 'Bijv. 2015',
    helpText: 'Bouwjaar van uw motor',
    width: 'small'
  },

  kenteken: {
    key: 'kenteken',
    label: 'Kenteken',
    dataType: 'string',
    inputType: 'text',
    group: 'motor',
    order: 4,
    validation: [
      { type: 'max_length', value: 15, message: 'Kenteken mag maximaal 15 karakters bevatten' }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'],
      selfService: true,
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: '12-ABC-3 of internationaal formaat',
    helpText: 'Kenteken van uw motor',
    width: 'medium'
  },

  // ========================================
  // FINANCIAL INFORMATION
  // ========================================
  // Change IBAN back to bankrekeningnummer to match API
  bankrekeningnummer: {
    key: 'bankrekeningnummer',
    label: 'IBAN',
    dataType: 'string',
    inputType: 'iban',
    group: 'financial',
    order: 1,
    validation: [
      { 
        type: 'required', 
        message: 'IBAN is verplicht voor dit lidmaatschapstype',
        condition: { field: 'lidmaatschap', operator: 'contains', value: ['Gewoon lid', 'Gezins lid', 'Donateur', 'Gezins donateur', 'Sponsor'] }
      },
      { type: 'iban', message: 'Voer een geldig IBAN nummer in' },
      { type: 'min_length', value: 15, message: 'IBAN moet minimaal 15 karakters bevatten' },
      { type: 'max_length', value: 34, message: 'IBAN mag maximaal 34 karakters bevatten' }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_CRUD_All'],
      edit: ['System_CRUD_All',  'Members_CRUD_All'],
      selfService: true,
      regionalRestricted: true
    },
    placeholder: 'NL12ABCD0123456789 of internationaal IBAN',
    helpText: 'Internationaal bankrekeningnummer voor incasso doeleinden'
  },


  betaalwijze: {
    key: 'betaalwijze',
    label: 'Betaalwijze',
    dataType: 'enum',
    inputType: 'select',
    group: 'financial',
    order: 2,
    enumOptions: ['Incasso', 'Overmaking'],
    validation: [
      { type: 'required', message: 'Betaalwijze is verplicht' }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_CRUD_All'],
      edit: ['System_CRUD_All', 'Members_CRUD_All'],
      selfService: true,
      regionalRestricted: true
    },
    placeholder: 'Selecteer betaalwijze',
    helpText: 'Hoe wilt u uw contributie betalen?',
    width: 'medium'
  },


};

// ============================================================================
// CONTEXT-SPECIFIC CONFIGURATIONS
// ============================================================================

export interface TableColumnConfig {
  fieldKey: string;
  visible: boolean;
  order: number;
  width?: number | string; // pixels or percentage
  sortable?: boolean;
  filterable?: boolean;
  filterType?: 'text' | 'select' | 'date' | 'number' | 'boolean';
  sticky?: boolean; // for sticky columns
  align?: 'left' | 'center' | 'right';
}

export interface TableContextConfig {
  name: string;
  description: string;
  columns: TableColumnConfig[];
  defaultSort?: {
    field: string;
    direction: 'asc' | 'desc';
  };
  pageSize?: number;
  exportable?: boolean;
  regionalRestricted?: boolean; // Filter data to user's region only
  permissions: {
    view: HDCNGroup[];
    export?: HDCNGroup[];
  };
}

// ============================================================================
// MEMBER TABLE CONFIGURATIONS
// ============================================================================

export const MEMBER_TABLE_CONTEXTS: Record<string, TableContextConfig> = {
  // Default member overview table
  memberOverview: {
    name: 'Member Overview',
    description: 'Standard member table for general administration',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 80, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'voornaam', visible: true, order: 2, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'tussenvoegsel', visible: true, order: 3, width: 80, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'achternaam', visible: true, order: 4, width: 140, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'geboortedatum', visible: true, order: 5, width: 110, sortable: true, filterable: true, filterType: 'date' },
      { fieldKey: 'email', visible: true, order: 6, width: 200, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'telefoon', visible: false, order: 7, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'straat', visible: true, order: 8, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'postcode', visible: true, order: 9, width: 80, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'woonplaats', visible: true, order: 10, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'land', visible: false, order: 11, width: 100, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 12, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'status', visible: true, order: 13, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'lidmaatschap', visible: true, order: 14, width: 130, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'ingangsdatum', visible: true, order: 15, width: 110, sortable: true, filterable: true, filterType: 'date' },
      { fieldKey: 'jaren_lid', visible: true, order: 16, width: 80, sortable: true, filterable: true, filterType: 'number', align: 'center' }
    ],
    defaultSort: { field: 'achternaam', direction: 'asc' },
    pageSize: 50,
    exportable: true,
    regionalRestricted: true, // Apply regional filtering for Members_Read_All users
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      export: ['System_CRUD_All','Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
    }
  },

  // Compact table for quick lookups
  memberCompact: {
    name: 'Member Compact',
    description: 'Minimal member table for quick reference',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 80, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'voornaam', visible: true, order: 2, width: 100, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'achternaam', visible: true, order: 3, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'email', visible: true, order: 4, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 5, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'status', visible: true, order: 6, width: 90, sortable: true, filterable: true, filterType: 'select' }
    ],
    defaultSort: { field: 'achternaam', direction: 'asc' },
    pageSize: 100,
    exportable: false,
    regionalRestricted: true, // Apply regional filtering for Members_Read_All users
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
    }
  },

  // Motor-focused view for events/rides
  motorView: {
    name: 'Motor Members',
    description: 'Member table focused on motor information',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 80, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'voornaam', visible: true, order: 2, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'achternaam', visible: true, order: 3, width: 140, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 4, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'motormerk', visible: true, order: 5, width: 130, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'motortype', visible: true, order: 6, width: 150, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'bouwjaar', visible: true, order: 7, width: 90, sortable: true, filterable: true, filterType: 'number', align: 'center' },
      { fieldKey: 'kenteken', visible: true, order: 8, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'telefoon', visible: true, order: 9, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'email', visible: false, order: 10, width: 200, sortable: true, filterable: true, filterType: 'text' }
    ],
    defaultSort: { field: 'motormerk', direction: 'asc' },
    pageSize: 50,
    exportable: true,
    regionalRestricted: true, // Apply regional filtering for Members_Read_All users
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'Event_Organizer'],
      export: ['System_CRUD_All', 'Members_CRUD_All', 'Event_Organizer']
    }
  },

  // Communication-focused view
  communicationView: {
    name: 'Communication List',
    description: 'Member table for communication and marketing',
    columns: [
      { fieldKey: 'voornaam', visible: true, order: 1, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'achternaam', visible: true, order: 2, width: 140, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'email', visible: true, order: 3, width: 220, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'straat', visible: true, order: 4, width: 180, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'postcode', visible: true, order: 5, width: 80, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'woonplaats', visible: true, order: 6, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'land', visible: false, order: 7, width: 100, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'regio', visible: true, order: 8, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'clubblad', visible: true, order: 9, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'nieuwsbrief', visible: true, order: 10, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'privacy', visible: true, order: 11, width: 80, sortable: true, filterable: true, filterType: 'select', align: 'center' },
      { fieldKey: 'status', visible: true, order: 12, width: 100, sortable: true, filterable: true, filterType: 'select' }
    ],
    defaultSort: { field: 'achternaam', direction: 'asc' },
    pageSize: 100,
    exportable: true,
    regionalRestricted: true, // Apply regional filtering for Members_Read_All users
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Communication_Read_All', 'Communication_CRUD_All'],
      export: ['System_CRUD_All', 'Communication_CRUD_All', 'Communication_Read_All']
    }
  },

  // Financial overview
  financialView: {
    name: 'Financial Overview',
    description: 'Member table for financial administration',
    columns: [
      { fieldKey: 'lidnummer', visible: true, order: 1, width: 80, sortable: true, filterable: true, filterType: 'number', sticky: true },
      { fieldKey: 'voornaam', visible: true, order: 2, width: 120, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'achternaam', visible: true, order: 3, width: 140, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'lidmaatschap', visible: true, order: 4, width: 130, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'betaalwijze', visible: true, order: 5, width: 110, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'bankrekeningnummer', visible: true, order: 6, width: 200, sortable: true, filterable: true, filterType: 'text' },
      { fieldKey: 'status', visible: true, order: 7, width: 100, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'regio', visible: true, order: 8, width: 120, sortable: true, filterable: true, filterType: 'select' },
      { fieldKey: 'ingangsdatum', visible: true, order: 9, width: 110, sortable: true, filterable: true, filterType: 'date' },
      { fieldKey: 'jaren_lid', visible: true, order: 10, width: 80, sortable: true, filterable: true, filterType: 'number', align: 'center' }
    ],
    defaultSort: { field: 'achternaam', direction: 'asc' },
    pageSize: 50,
    exportable: true,
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All'],
      export:['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All']
    }
  }
};

// ============================================================================
// MEMBER VIEW MODAL CONFIGURATIONS
// ============================================================================

export interface ModalFieldConfig {
  fieldKey: string;
  visible: boolean;
  readOnly?: boolean;
  order: number;
  span?: 1 | 2 | 3; // Grid span (1=33%, 2=66%, 3=100%)
  conditionalVisible?: ConditionalRule[];
}

export interface ModalSectionConfig {
  name: string;
  title: string;
  order: number;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  fields: ModalFieldConfig[];
  showWhen?: ConditionalRule[];
  permissions?: {
    view: HDCNGroup[];
    edit?: HDCNGroup[];
  };
}

export interface ModalContextConfig {
  name: string;
  description: string;
  sections: ModalSectionConfig[];
  permissions: {
    view: HDCNGroup[];
    edit?: HDCNGroup[];
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
          { fieldKey: 'voornaam', visible: true, order: 1, span: 1 },
          { fieldKey: 'tussenvoegsel', visible: true, order: 2, span: 1 },
          { fieldKey: 'achternaam', visible: true, order: 3, span: 1 },
          { fieldKey: 'initialen', visible: true, order: 4, span: 1 },
          { fieldKey: 'geboortedatum', visible: true, order: 5, span: 1 },
          { fieldKey: 'geslacht', visible: true, order: 6, span: 1 },
          { fieldKey: 'nationaliteit', visible: true, order: 7, span: 2 },
          { fieldKey: 'email', visible: true, order: 8, span: 2 },
          { fieldKey: 'telefoon', visible: true, order: 9, span: 1 },
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
          view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
          edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
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
          view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
          edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
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
          view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
          edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
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
          view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
          edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
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
          view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
          edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
        }
      },
      {
        name: 'administrative',
        title: 'Administratieve Gegevens',
        order: 6,
        collapsible: true,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'tijdstempel', visible: true, readOnly: true, order: 1, span: 1 },
          { fieldKey: 'aanmeldingsjaar', visible: true, readOnly: true, order: 2, span: 1 },
          { fieldKey: 'datum_ondertekening', visible: true, order: 3, span: 1 },
          { fieldKey: 'created_at', visible: true, readOnly: true, order: 4, span: 1 },
          { fieldKey: 'updated_at', visible: true, readOnly: true, order: 5, span: 1 },
          { fieldKey: 'notities', visible: true, order: 6, span: 3 }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
          edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
        }
      }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
      edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
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
          { fieldKey: 'voornaam', visible: true, readOnly: true, order: 1, span: 1 },
          { fieldKey: 'achternaam', visible: true, readOnly: true, order: 2, span: 1 },
          { fieldKey: 'lidnummer', visible: true, readOnly: true, order: 3, span: 1 },
          { fieldKey: 'email', visible: true, readOnly: true, order: 4, span: 2 },
          { fieldKey: 'telefoon', visible: true, readOnly: true, order: 5, span: 1 },
          { fieldKey: 'regio', visible: true, readOnly: true, order: 6, span: 1 },
          { fieldKey: 'status', visible: true, readOnly: true, order: 7, span: 1 },
          { fieldKey: 'lidmaatschap', visible: true, readOnly: true, order: 8, span: 1 }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management'],
          edit: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
        }
      }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management']
    }
  },

  // Registration form context
  memberRegistration: {
    name: 'Member Registration',
    description: 'New member registration form',
    sections: [
      {
        name: 'personal',
        title: 'Persoonlijke Informatie',
        order: 1,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'voornaam', visible: true, order: 1, span: 1 },
          { fieldKey: 'tussenvoegsel', visible: true, order: 2, span: 1 },
          { fieldKey: 'achternaam', visible: true, order: 3, span: 1 },
          { fieldKey: 'geboortedatum', visible: true, order: 4, span: 1 },
          { fieldKey: 'geslacht', visible: true, order: 5, span: 1 },
          { fieldKey: 'email', visible: true, order: 6, span: 2 },
          { fieldKey: 'telefoon', visible: true, order: 7, span: 1 },
          { 
            fieldKey: 'minderjarigNaam', 
            visible: true, 
            order: 8, 
            span: 3,
            conditionalVisible: [
              { field: 'geboortedatum', operator: 'age_less_than', value: 18 }
            ]
          }
        ],
        permissions: {
          view: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All'],
          edit: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All']
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
          view: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All'],
          edit: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'membership',
        title: 'Lidmaatschap',
        order: 3,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'lidmaatschap', visible: true, order: 1, span: 1 },
          { fieldKey: 'regio', visible: true, order: 2, span: 1 },
          { fieldKey: 'ingangsdatum', visible: true, order: 5, span: 1 },
          { fieldKey: 'jaren_lid', visible: true, readOnly: true, order: 6, span: 1 },
          { fieldKey: 'clubblad', visible: true, order: 3, span: 1 },
          { fieldKey: 'nieuwsbrief', visible: true, order: 4, span: 1 },
          { fieldKey: 'privacy', visible: true, order: 5, span: 1 },
          { fieldKey: 'wiewatwaar', visible: true, order: 6, span: 3 }
        ],
        permissions: {
          view: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All'],
          edit: ['System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'motor',
        title: 'Motorgegevens',
        order: 4,
        defaultExpanded: true,
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
          view: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All'],
          edit: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'financial',
        title: 'Betaalgegevens',
        order: 5,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'betaalwijze', visible: true, order: 1, span: 1 },
          { fieldKey: 'bankrekeningnummer', visible: true, order: 2, span: 2 }
        ],
        permissions: {
          view: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All'],
          edit: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All']
        }
      }
    ],
    permissions: {
      view: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All'],
      edit: ['hdcnLeden', 'System_CRUD_All', 'Members_CRUD_All']
    }
  },

  // Multi-step membership application form
  membershipApplication: {
    name: 'Membership Application',
    description: 'Progressive disclosure membership application form',
    sections: [
      {
        name: 'step1_personal',
        title: 'Stap 1: Wie ben je?',
        order: 1,
        defaultExpanded: true,
        fields: [
          { fieldKey: 'voornaam', visible: true, order: 1, span: 1 },
          { fieldKey: 'tussenvoegsel', visible: true, order: 2, span: 1 },
          { fieldKey: 'achternaam', visible: true, order: 3, span: 1 },
          { fieldKey: 'geboortedatum', visible: true, order: 4, span: 1 },
          { fieldKey: 'geslacht', visible: true, order: 5, span: 1 },
          { fieldKey: 'email', visible: true, order: 6, span: 2 },
          { fieldKey: 'telefoon', visible: true, order: 7, span: 1 },
          { 
            fieldKey: 'minderjarigNaam', 
            visible: true, 
            order: 8, 
            span: 3,
            conditionalVisible: [
              { field: 'geboortedatum', operator: 'age_less_than', value: 18 }
            ]
          }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_CRUD_All'],
          edit: ['System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'step2_address',
        title: 'Stap 2: Waar woon je?',
        order: 2,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'straat', visible: true, order: 1, span: 2 },
          { fieldKey: 'postcode', visible: true, order: 2, span: 1 },
          { fieldKey: 'woonplaats', visible: true, order: 3, span: 2 },
          { fieldKey: 'land', visible: true, order: 4, span: 1 },
          { fieldKey: 'nationaliteit', visible: true, order: 5, span: 1 }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_CRUD_All'],
          edit: ['System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'step3_membership',
        title: 'Stap 3: Welk lidmaatschap wil je?',
        order: 3,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'lidmaatschap', visible: true, order: 1, span: 2 },
          { fieldKey: 'regio', visible: true, order: 2, span: 1 },
          { fieldKey: 'wiewatwaar', visible: true, order: 3, span: 3 }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_CRUD_All'],
          edit: ['System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'step4_motor',
        title: 'Stap 4: Vertel over je motor',
        order: 4,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'motormerk', visible: true, order: 1, span: 1 },
          { fieldKey: 'motortype', visible: true, order: 2, span: 2 },
          { fieldKey: 'bouwjaar', visible: true, order: 3, span: 1 },
          { fieldKey: 'kenteken', visible: true, order: 4, span: 2 }
        ],
        showWhen: [
          { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
          { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_CRUD_All'],
          edit: ['System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'step5_preferences',
        title: 'Stap 5: Communicatie voorkeuren',
        order: 5,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'clubblad', visible: true, order: 1, span: 1 },
          { fieldKey: 'nieuwsbrief', visible: true, order: 2, span: 1 },
          { fieldKey: 'privacy', visible: true, order: 3, span: 2 }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_CRUD_All'],
          edit: ['System_CRUD_All', 'Members_CRUD_All']
        }
      },
      {
        name: 'step6_payment',
        title: 'Stap 6: Hoe wil je betalen?',
        order: 6,
        defaultExpanded: false,
        fields: [
          { fieldKey: 'betaalwijze', visible: true, order: 1, span: 1 },
          { fieldKey: 'bankrekeningnummer', visible: true, order: 2, span: 2 }
        ],
        permissions: {
          view: ['System_CRUD_All', 'Members_CRUD_All'],
          edit: ['System_CRUD_All', 'Members_CRUD_All']
        }
      }
    ],
    permissions: {
      view: ['System_CRUD_All', 'Members_CRUD_All'],
      edit: ['System_CRUD_All', 'Members_CRUD_All']
    }
  }
};

// ============================================================================
// UTILITY FUNCTIONS FOR MODAL CONTEXTS
// ============================================================================

/**
 * Get modal configuration by context name
 */
export function getModalContext(contextName: string): ModalContextConfig | undefined {
  return MEMBER_MODAL_CONTEXTS[contextName];
}

/**
 * Get visible sections for a modal context, sorted by order
 */
export function getVisibleSections(contextName: string, userRole: HDCNGroup): ModalSectionConfig[] {
  const context = MEMBER_MODAL_CONTEXTS[contextName];
  if (!context) return [];
  
  return context.sections
    .filter(section => section.permissions?.view.includes(userRole))
    .sort((a, b) => a.order - b.order);
}

/**
 * Get visible fields for a section, sorted by order
 */
export function getVisibleFields(section: ModalSectionConfig): ModalFieldConfig[] {
  return section.fields
    .filter(field => field.visible)
    .sort((a, b) => a.order - b.order);
}

/**
 * Check if user can edit a modal context
 */
export function canEditModalContext(contextName: string, userRole: HDCNGroup): boolean {
  const context = MEMBER_MODAL_CONTEXTS[contextName];
  if (!context || !context.permissions.edit) return false;
  
  return context.permissions.edit.includes(userRole);
}

// ============================================================================
// UTILITY FUNCTIONS FOR TABLE CONTEXTS
// ============================================================================

/**
 * Get table configuration by context name
 */
export function getTableContext(contextName: string): TableContextConfig | undefined {
  return MEMBER_TABLE_CONTEXTS[contextName];
}

/**
 * Get visible columns for a table context, sorted by order
 */
export function getVisibleColumns(contextName: string): TableColumnConfig[] {
  const context = MEMBER_TABLE_CONTEXTS[contextName];
  if (!context) return [];
  
  return context.columns
    .filter(col => col.visible)
    .sort((a, b) => a.order - b.order);
}

/**
 * Get filterable columns for a table context
 */
export function getFilterableColumns(contextName: string): TableColumnConfig[] {
  const context = MEMBER_TABLE_CONTEXTS[contextName];
  if (!context) return [];
  
  return context.columns.filter(col => col.visible && col.filterable);
}

/**
 * Check if user has permission to view table context
 */
export function canViewTableContext(contextName: string, userRole: HDCNGroup): boolean {
  const context = MEMBER_TABLE_CONTEXTS[contextName];
  if (!context) return false;
  
  return context.permissions.view.includes(userRole);
}

/**
 * Get all available table contexts for a user role
 */
export function getAvailableTableContexts(userRole: HDCNGroup): TableContextConfig[] {
  return Object.values(MEMBER_TABLE_CONTEXTS)
    .filter(context => context.permissions.view.includes(userRole));
}

/**
 * Get all fields for a specific group
 */
export function getFieldsByGroup(group: FieldGroup): FieldDefinition[] {
  return Object.values(MEMBER_FIELDS)
    .filter(field => field.group === group)
    .sort((a, b) => a.order - b.order);
}

/**
 * Get field definition by key
 */
export function getFieldDefinition(key: string): FieldDefinition | undefined {
  return MEMBER_FIELDS[key];
}

/**
 * Get all field keys
 */
export function getAllFieldKeys(): string[] {
  return Object.keys(MEMBER_FIELDS);
}

/**
 * Get fields by permission level
 */
export function getFieldsByPermission(permissionLevel: HDCNGroup, action: 'view' | 'edit'): FieldDefinition[] {
  return Object.values(MEMBER_FIELDS).filter(field => 
    field.permissions?.[action]?.includes(permissionLevel)
  );
}

/**
 * Get field groups in display order
 */
export function getFieldGroups(): FieldGroup[] {
  return ['personal', 'address', 'membership', 'motor', 'financial', 'administrative'];
}
