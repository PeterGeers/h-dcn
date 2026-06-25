/**
 * Product Field Definitions
 *
 * Canonical field registry for the Producten DynamoDB table.
 * Field keys match DynamoDB attribute names exactly (Dutch convention).
 *
 * Decisions:
 * - docs/decisions/dutch-field-names.md
 * - docs/decisions/webshop-as-event.md
 * - docs/decisions/bidirectional-variant-sync.md
 */

import type { ProductFieldDefinition } from './types';

// ============================================================================
// PARENT PRODUCT FIELDS
// ============================================================================

export const parentFields: Record<string, ProductFieldDefinition> = {
  product_id: {
    key: 'product_id',
    label: 'Product ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'identity',
    order: 1,
    required: true,
    recordType: 'both',
    editable: false,
    helpText: 'UUID primary key — auto-generated',
  },

  naam: {
    key: 'naam',
    label: 'Productnaam',
    dataType: 'string',
    inputType: 'text',
    group: 'identity',
    order: 2,
    required: true,
    recordType: 'both',
    placeholder: 'Bijv. H-DCN T-Shirt',
    helpText: 'De naam zoals getoond aan klanten',
  },

  artikelcode: {
    key: 'artikelcode',
    label: 'Artikelcode',
    dataType: 'string',
    inputType: 'text',
    group: 'identity',
    order: 3,
    required: false,
    recordType: 'parent',
    placeholder: 'Bijv. G5, TD-60',
    helpText: 'Korte productcode voor facturen en referentie. Mag leeg zijn.',
  },

  prijs: {
    key: 'prijs',
    label: 'Prijs',
    dataType: 'string',
    inputType: 'number',
    group: 'pricing',
    order: 1,
    required: true,
    recordType: 'both',
    placeholder: '0.00',
    helpText: 'Prijs in euro, opgeslagen als string (bijv. "3.50")',
  },

  groep: {
    key: 'groep',
    label: 'Groep',
    dataType: 'string',
    inputType: 'select',
    group: 'categorization',
    order: 1,
    required: false,
    recordType: 'parent',
    placeholder: 'Selecteer groep',
    helpText: 'Productcategorie (bijv. Heren, Dames, Diversen)',
  },

  subgroep: {
    key: 'subgroep',
    label: 'Subgroep',
    dataType: 'string',
    inputType: 'select',
    group: 'categorization',
    order: 2,
    required: false,
    recordType: 'parent',
    placeholder: 'Selecteer subgroep',
    helpText: 'Subcategorie (bijv. T-Shirts, Pins)',
  },

  images: {
    key: 'images',
    label: 'Afbeeldingen',
    dataType: 'list',
    inputType: 'image-upload',
    group: 'media',
    order: 1,
    required: false,
    recordType: 'parent',
    helpText: 'Productafbeeldingen (URLs naar S3)',
    defaultValue: [],
  },

  active: {
    key: 'active',
    label: 'Actief',
    dataType: 'boolean',
    inputType: 'checkbox',
    group: 'metadata',
    order: 1,
    required: false,
    recordType: 'both',
    helpText: 'Inactieve producten worden niet getoond',
    defaultValue: true,
  },

  is_parent: {
    key: 'is_parent',
    label: 'Is hoofdproduct',
    dataType: 'boolean',
    inputType: 'hidden',
    group: 'variants',
    order: 1,
    required: false,
    recordType: 'both',
    editable: false,
    helpText: 'true = hoofdproduct, false = variant',
  },

  event_ids: {
    key: 'event_ids',
    label: 'Evenementen',
    dataType: 'list',
    inputType: 'multiselect',
    group: 'categorization',
    order: 3,
    required: false,
    recordType: 'parent',
    helpText: 'In welke evenementen/winkels dit product zichtbaar is (incl. evt-webshop)',
    defaultValue: [],
  },



  order_item_fields: {
    key: 'order_item_fields',
    label: 'Bestelvelden',
    dataType: 'list',
    inputType: 'json-editor',
    group: 'ordering',
    order: 1,
    required: false,
    recordType: 'parent',
    helpText: 'Extra velden die de klant per besteld item invult (bijv. naam, tentgrootte)',
  },

  purchase_rules: {
    key: 'purchase_rules',
    label: 'Aankoopregels',
    dataType: 'map',
    inputType: 'json-editor',
    group: 'ordering',
    order: 2,
    required: false,
    recordType: 'parent',
    helpText: 'Beperkingen: max_per_order (max per bestelling), min_per_order (min per bestelling), max_per_event (totaal cap), order_mode (persistent/event)',
  },

  created_at: {
    key: 'created_at',
    label: 'Aangemaakt op',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 2,
    required: false,
    recordType: 'both',
    editable: false,
  },

  updated_at: {
    key: 'updated_at',
    label: 'Bijgewerkt op',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 3,
    required: false,
    recordType: 'both',
    editable: false,
  },
};

// ============================================================================
// VARIANT-SPECIFIC FIELDS
// ============================================================================

export const variantFields: Record<string, ProductFieldDefinition> = {
  parent_id: {
    key: 'parent_id',
    label: 'Hoofdproduct ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'variants',
    order: 3,
    required: true,
    recordType: 'variant',
    editable: false,
    helpText: 'UUID van het hoofdproduct waar deze variant bij hoort',
  },

  variant_attributes: {
    key: 'variant_attributes',
    label: 'Variant waarden',
    dataType: 'map',
    inputType: 'json-editor',
    group: 'variants',
    order: 4,
    required: true,
    recordType: 'variant',
    helpText: 'De as-waarden van deze variant, bijv. {"Maat": "M", "Gender": "Male"}',
  },

  stock: {
    key: 'stock',
    label: 'Voorraad',
    dataType: 'number',
    inputType: 'number',
    group: 'variants',
    order: 5,
    required: false,
    recordType: 'variant',
    placeholder: '0',
    helpText: 'Huidige voorraad',
    defaultValue: 0,
  },

  sold_count: {
    key: 'sold_count',
    label: 'Verkocht',
    dataType: 'number',
    inputType: 'number',
    group: 'variants',
    order: 6,
    required: false,
    recordType: 'variant',
    editable: false,
    helpText: 'Totaal verkochte eenheden',
    defaultValue: 0,
  },

  allow_oversell: {
    key: 'allow_oversell',
    label: 'Oversell toestaan',
    dataType: 'boolean',
    inputType: 'checkbox',
    group: 'variants',
    order: 7,
    required: false,
    recordType: 'variant',
    helpText: 'Verkoop toestaan wanneer voorraad 0 is',
    defaultValue: true,
  },
};
