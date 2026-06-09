/**
 * TypeScript type definitions for the PresMeet module.
 *
 * PresMeet is the FH-DCE Presidents' Meeting booking system.
 * These types model the product-type-driven cart/order/payment pipeline.
 */

// --- Enums / Union Types ---

export type ProductType = "meeting_ticket" | "party_ticket" | "tshirt" | "airport_transfer";

export type OrderStatus = "draft" | "submitted" | "locked";

export type PaymentStatus = "unpaid" | "partial" | "paid";

export type Gender = "male" | "female";

export type TshirtSize = "S" | "M" | "L" | "XL" | "XXL" | "3XL" | "4XL";

export type TransferDirection = "pickup" | "dropoff";

export type Airport = "AMS" | "RTM" | "EIN";

export type PersonType = "delegate" | "guest";

export type PaymentProvider = "mollie" | "manual";

export type MolliePaymentStatus = "pending" | "paid" | "failed" | "cancelled" | "expired";

// --- Core Data Models ---

export interface CartItem {
  item_id: string;
  product_type: ProductType;
  attributes: Record<string, any>;
  unit_price: number;
}

export interface PresMeetBooking {
  order_id: string;
  club_id: string;
  event_id: string;
  source: "presmeet";
  status: OrderStatus;
  payment_status: PaymentStatus;
  items: CartItem[];
  total_amount: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
}

// --- Configuration ---

export interface AttributeSchema {
  type: "string" | "integer";
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

// --- Payments ---

export interface PaymentSession {
  payment_id: string;
  checkout_url: string;
  amount: number;
  status: MolliePaymentStatus;
}

export interface ManualPayment {
  order_id: string;
  amount: number;
  date: string;
  description: string;
}

export interface PaymentRecord {
  payment_id: string;
  order_id: string;
  club_id: string;
  amount: number;
  status: MolliePaymentStatus;
  provider: PaymentProvider;
  mollie_payment_id?: string;
  description?: string;
  created_at: string;
  created_by: string;
}

// --- Reports ---

export type ReportType = "overview" | "orders" | "export_submitted" | "export_all" | "metadata";

export interface ReportMetadata {
  generated_at: string;
  generated_by: string;
  total_orders: number;
  total_items: number;
  generation_duration_ms: number;
}

export interface ReportOverview {
  generated_at: string;
  generated_by: string;
  summary: {
    total_orders: number;
    by_status: Record<OrderStatus, number>;
    by_product_type: Record<ProductType, Record<OrderStatus, number>>;
  };
  payments: {
    total_charged: number;
    total_paid: number;
    total_outstanding: number;
  };
}

export interface ReportOrderEntry {
  order_id: string;
  club_id: string;
  club_name: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  total_amount: number;
  total_paid: number;
  outstanding: number;
  item_counts: Record<ProductType, number>;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
}

export interface ReportOrders {
  generated_at: string;
  orders: ReportOrderEntry[];
}

export type ReportData = ReportOverview | ReportOrders | ReportMetadata;

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

export interface AssignClubResponse {
  message: string;
  club_id: string;
  member_id: string;
}
