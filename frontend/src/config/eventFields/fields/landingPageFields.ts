/**
 * Event Field Definitions - Landing Page Fields
 *
 * Fields with group: 'landing_page'
 * The landing_page map is stored as a single DynamoDB attribute on the event record.
 * These field definitions document the structure of that map.
 *
 * DynamoDB storage: event.landing_page = { enabled, slug, hero_image_url, tagline, registration_label, logos, sections }
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const landingPageFields: Record<string, FieldDefinition> = {
  landing_page: {
    key: 'landing_page',
    label: 'Landing Page',
    dataType: 'map',
    inputType: 'json',
    group: 'landing_page',
    order: 1,
    defaultValue: {
      enabled: false,
      slug: '',
      hero_image_url: '',
      tagline: '',
      registration_label: 'Register Now',
      logos: [],
      sections: [],
    },
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Volledige landing page configuratie als map. Bevat: enabled, slug, hero_image_url, tagline, registration_label, logos[], sections[].',
    width: 'full',
  },

  // ---- Sub-field documentation (not stored separately, part of landing_page map) ----

  'landing_page.enabled': {
    key: 'landing_page.enabled',
    label: 'Landing Page Actief',
    dataType: 'boolean',
    inputType: 'toggle',
    group: 'landing_page',
    order: 2,
    defaultValue: false,
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Bepaalt of de landing page zichtbaar is voor bezoekers.',
    width: 'small',
  },

  'landing_page.slug': {
    key: 'landing_page.slug',
    label: 'Landing Page Slug',
    dataType: 'string',
    inputType: 'text',
    group: 'landing_page',
    order: 3,
    validation: [
      { type: 'pattern', value: '^[a-z0-9]+(?:-[a-z0-9]+)*$', message: 'Slug mag alleen lowercase letters, cijfers en hyphens bevatten' },
      { type: 'max_length', value: 100, message: 'Slug mag maximaal 100 karakters bevatten' },
    ],
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'bijv. presmeet-2026',
    helpText: 'Unieke URL slug voor de landing page. Moet uniek zijn over alle events.',
    width: 'medium',
  },

  'landing_page.hero_image_url': {
    key: 'landing_page.hero_image_url',
    label: 'Hero Afbeelding',
    dataType: 'string',
    inputType: 'text',
    group: 'landing_page',
    order: 4,
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'https://...',
    helpText: 'URL naar de hero/banner afbeelding bovenaan de landing page.',
    width: 'large',
  },

  'landing_page.tagline': {
    key: 'landing_page.tagline',
    label: 'Tagline',
    dataType: 'string',
    inputType: 'text',
    group: 'landing_page',
    order: 5,
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Korte wervende tekst',
    helpText: 'Korte tekst onder de hero image.',
    width: 'large',
  },

  'landing_page.registration_label': {
    key: 'landing_page.registration_label',
    label: 'Registratie Knoptekst',
    dataType: 'string',
    inputType: 'text',
    group: 'landing_page',
    order: 6,
    defaultValue: 'Register Now',
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Register Now',
    helpText: 'Tekst op de registratieknop.',
    width: 'medium',
  },

  'landing_page.logos': {
    key: 'landing_page.logos',
    label: 'Logo\'s',
    dataType: 'list',
    inputType: 'json',
    group: 'landing_page',
    order: 7,
    defaultValue: [],
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Array van logo objecten: [{ url, alt, link? }]. Getoond op de landing page.',
    width: 'full',
  },

  'landing_page.sections': {
    key: 'landing_page.sections',
    label: 'Secties',
    dataType: 'list',
    inputType: 'json',
    group: 'landing_page',
    order: 8,
    defaultValue: [],
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Array van content secties: [{ title, body, image_url? }]. Getoond onder de hero.',
    width: 'full',
  },
};
