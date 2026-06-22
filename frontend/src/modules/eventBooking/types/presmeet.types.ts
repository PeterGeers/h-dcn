/**
 * PresMeet-specific domain types.
 *
 * These types model the FH-DCE Presidents' Meeting product-type-driven
 * cart/order/payment pipeline. They are retained here because the
 * eventBooking utilities (cartBuilder, validation, pdfGenerator) still
 * operate on these structures.
 *
 * TODO: Once the booking pipeline is fully genericised, these types can
 * be removed in favour of the generic eventBooking.types.ts definitions.
 */

// --- Enums / Union Types ---

export type ProductType = 'meeting_ticket' | 'party_ticket' | 'tshirt' | 'airport_transfer';

export type OrderStatus = 'draft' | 'submitted' | 'locked';

export type PaymentStatus = 'unpaid' | 'partial' | 'paid';

export type Gender = 'male' | 'female';

export type TshirtSize = 'S' | 'M' | 'L' | 'XL' | 'XXL' | '3XL' | '4XL';

export type TransferDirection = 'pickup' | 'dropoff';

export type Airport = 'AMS' | 'RTM' | 'EIN';

export type PersonType = 'delegate' | 'guest';

// --- Core Data Models ---

export interface CartItem {
  item_id: string;
  product_type: ProductType;
  attributes: Record<string, any>;
  unit_price: number;
}

// --- Configuration ---

export interface AttributeSchema {
  type: 'string' | 'integer';
  required: boolean;
  enum?: string[];
  min_length?: number;
  max_length?: number;
  minimum?: number;
  maximum?: number;
}

export interface ProductTypeConfig {
  product_type: ProductType;
  max_per_club: number;
  min_per_club: number;
  unit_price: number;
  required_attributes: Record<string, AttributeSchema>;
}

export interface PresMeetConfig {
  product_types: ProductTypeConfig[];
  event: {
    event_id: string;
    start_date: string;
    end_date: string;
  };
}

// --- Validation ---

export interface ValidationError {
  item_id?: string;
  field: string;
  message: string;
  constraint: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

// --- Booking Form Data ---

export interface DelegateFormData {
  name: string;
  role: string;
  attend_party: boolean;
  tshirt?: {
    gender: Gender;
    size: TshirtSize;
  };
}

export interface GuestFormData {
  name: string;
  tshirt?: {
    gender: Gender;
    size: TshirtSize;
  };
}

export interface TransferFormData {
  direction: TransferDirection;
  airport: Airport;
  flight: string;
  date: string;
  time: string;
  persons: number;
}

export interface BookingFormData {
  delegates: DelegateFormData[];
  guests: GuestFormData[];
  transfers: TransferFormData[];
}

// --- Club Registry (Onboarding) ---

export interface ClubRegistryEntry {
  club_id: string;
  club_name: string;
  logo_url: string | null;
  assigned_member_id: string | null;
  assigned_contact: string | null;
  assigned_at: string | null;
}

export interface ClubRegistry {
  version: string;
  updated_at: string;
  clubs: ClubRegistryEntry[];
}
