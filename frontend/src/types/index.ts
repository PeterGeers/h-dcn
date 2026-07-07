// Core H-DCN Types
export interface Member {
  id: string;
  member_id?: string;
  name: string;
  email: string;
  region: string;
  regio?: string;
  membershipType: string;
  membership_type?: string;
  lidmaatschap?: string;
  voornaam?: string;
  achternaam?: string;
  lidnummer?: string | number;
  status?: string;
  created_at?: string;
  updated_at?: string;
  initialen?: string;
  tussenvoegsel?: string;
  geboortedatum?: string;
  geslacht?: string;
  telefoon?: string;
  phone?: string;
  mobiel?: string;
  werktelefoon?: string;
  bsn?: string;
  nationaliteit?: string;
  straat?: string;
  huisnummer?: string;
  postcode?: string;
  woonplaats?: string;
  land?: string;
  postadres?: string;
  postpostcode?: string;
  postwoonplaats?: string;
  postland?: string;
  clubblad?: string;
  nieuwsbrief?: string;
  ingangsdatum?: string;
  einddatum?: string;
  opzegtermijn?: string;
  motormerk?: string;
  motortype?: string;
  motormodel?: string;
  motorkleur?: string;
  bouwjaar?: string;
  kenteken?: string;
  cilinderinhoud?: string;
  vermogen?: string;
  bankrekeningnummer?: string;
  iban?: string;
  bic?: string;
  contributie?: string;
  betaalwijze?: string;
  incasso?: string;
  beroep?: string;
  werkgever?: string;
  hobbys?: string;
  wiewatwaar?: string;
  minderjarigNaam?: string;
  notities?: string;
  opmerkingen?: string;
  privacy?: string;
  toestemmingfoto?: string;
  address?: string;
  // Additional timestamp and membership fields
  tijdstempel?: string;
  datum_ondertekening?: string;
  datumOndertekening?: string;
  ingangsdatum_lidmaatschap?: string;
  ingangsdatumLidmaatschap?: string;
  aanmeldingsdatum?: string;
  aanmeldingsDatum?: string;
  
  // ============================================================================
  // CALCULATED/COMPUTED FIELDS
  // ============================================================================
  // These fields are automatically calculated by computeCalculatedFields()
  // and should be present on Member objects that have been processed
  
  /** Full name computed from voornaam + tussenvoegsel + achternaam */
  korte_naam?: string;
  
  /** Age in years computed from geboortedatum */
  leeftijd?: number | null;
  
  /** Birthday in format "month day" computed from geboortedatum */
  verjaardag?: string;
  
  /** Years of membership computed from ingangsdatum/tijdstempel */
  jaren_lid?: number | null;
  
  /** Registration year computed from ingangsdatum/tijdstempel */
  aanmeldingsjaar?: number | null;
}

export interface Product {
  product_id: string;
  id?: string; // alias used for React keys and legacy article codes
  naam?: string;
  prijs?: string | number;
  artikelcode?: string;
  groep?: string;
  subgroep?: string;
  images?: string[];
  is_parent?: boolean;
  active?: boolean;
  order_item_fields?: any[];
  purchase_rules?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  // Variant-specific fields
  parent_id?: string;
  variant_attributes?: Record<string, string>;
  stock?: number;
  sold_count?: number;
  allow_oversell?: boolean;
}

export interface Event {
  event_id?: string;
  // New schema (Field Registry)
  name?: string;
  event_type?: string;
  event_category?: string;
  participation?: string;
  linked_regio?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  location?: string;
  slug?: string;
  poster_url?: string;
  description?: string;
  registration_open?: string;
  registration_close?: string;
  payment_deadline?: string;
  product_ids?: string[];
  constraints?: Array<{ key: string; max: number; counting_rule: string }>;
  participants?: string | number;
  cost?: string | number;
  revenue?: string | number;
  notes?: string;
  landing_page?: {
    enabled: boolean;
    slug: string;
    hero_image_url: string;
    tagline: string;
    registration_label: string;
    logos: Array<{ name: string; logo_url: string }>;
    sections: Array<{ type: string; title: string; content?: string; items?: Array<{ name: string; logo_url: string }> }>;
  };
  registry_config?: {
    s3_path?: string;
    row_label?: string;
    claim_mode?: 'first_come_first_served' | 'email_restricted';
    max_delegates_per_row?: number;
    allow_logo_upload?: boolean;
  };
  // Metadata
  created_at?: string;
  created_by?: string;
  updated_at?: string;
}

export interface ApiResponse<T> {
  statusCode: number;
  body: T;
}

// Import HDCNGroup from user.ts to avoid duplication
export type { HDCNGroup } from './user';

// Cognito User Groups - UPDATED TO NEW STRUCTURE
export type UserGroup = 'hdcnLeden' | `Regio_${string}` | `Members_${string}` | `Events_${string}` | `Products_${string}` | `Communication_${string}` | `System_${string}` | 'Webshop_Management' | 'verzoek_lid';