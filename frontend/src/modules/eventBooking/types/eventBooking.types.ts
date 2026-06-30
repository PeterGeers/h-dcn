/**
 * TypeScript type definitions for Event Booking v3.
 *
 * Models the order-only flow with event-linked architecture,
 * optimistic locking, and Mollie payment integration.
 */

// --- Status Types ---

export type OrderStatus = 'draft' | 'submitted' | 'locked';

export type PaymentStatus = 'unpaid' | 'partial' | 'paid';

export type EventStatus = 'draft' | 'published' | 'open' | 'closed' | 'archived';

export type CountingRule = 'count_items_by_product' | 'count_distinct_rows' | 'sum_field';

export type PaymentProvider = 'mollie' | 'manual';

export type MolliePaymentStatus = 'pending' | 'paid' | 'failed' | 'cancelled' | 'expired';

export type FieldType = 'text' | 'select' | 'number' | 'date';

// --- Order Models ---

export interface OrderItem {
  product_id: string;
  variant_id: string | null;
  variant_attributes?: Record<string, string>;
  item_fields_data: Record<string, any>;
  unit_price: number;
  line_total: number;
}

export interface Delegate {
  primary: string;
  secondary: string | null;
  primary_member_id?: string;
  secondary_member_id?: string;
  pending_secondary_email?: string | null;
}

export interface StatusHistoryEntry {
  from: OrderStatus;
  to: OrderStatus;
  at: string;
  by: string;
  source: 'delegate' | 'admin' | 'system' | 'manual';
}

export interface Order {
  order_id: string;
  source_id: string;
  member_id: string;
  registry_row_id?: string;
  registry_row_label?: string;
  registry_row_logo_url?: string;
  event_id?: string;
  event_type?: string;
  status: OrderStatus;
  payment_status?: PaymentStatus;
  total_amount?: number;
  total_paid?: number;
  items: OrderItem[];
  delegates?: Delegate;
  version: number;
  status_history?: StatusHistoryEntry[];
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  created_by?: string;
  user_email?: string;
}

// --- Event Models ---

export interface Constraint {
  key: string;
  label: string;
  max: number;
  counting_rule: CountingRule;
  product_id?: string;
}

export interface RegistryConfig {
  s3_path: string;
  row_label: string;
  claim_mode?: 'first_come_first_served' | 'email_restricted';
  max_delegates_per_row?: number;
  allow_logo_upload?: boolean;
}

export interface Event {
  event_id: string;
  event_type: string;
  name: string;
  location: string;
  status: EventStatus;
  start_date: string;
  end_date: string;
  registration_open: string;
  registration_close: string;
  payment_deadline: string;
  product_ids: string[];
  constraints: Constraint[];
  created_at: string;
  created_by: string;
  registry_config?: RegistryConfig;
}

// --- Product Models ---

export interface OrderItemField {
  id: string;
  label: string;
  type: FieldType;
  required: boolean;
  options?: string[];
  min?: number;
  max?: number;
}

export interface VariantAxis {
  name: string;
  values: string[];
}

export interface PurchaseRules {
  min_per_order?: number;
  max_per_order?: number;
  max_per_event?: number;
  order_mode?: 'persistent';
}

export interface ProductVariant {
  variant_id: string;
  variant_attributes: Record<string, string>;
  price?: number;
  stock?: number;
  active?: boolean;
}

export interface Product {
  product_id: string;
  naam: string;
  event_type: string;
  prijs: number;
  order_item_fields: OrderItemField[];
  /** @deprecated No longer stored in DB — variants are fetched separately via useProductVariants */
  variant_schema?: VariantAxis[] | null;
  /** @deprecated Use useProductVariants hook instead */
  variants?: ProductVariant[];
  purchase_rules: PurchaseRules;
  /** Product images (S3 URLs) */
  images?: string[];
  /** Whether this is a parent product (has variants) */
  is_parent?: boolean;
}

// --- Payment Models ---

export interface PaymentRecord {
  payment_id: string;
  order_id: string;
  registry_row_id: string;
  amount: number;
  status: MolliePaymentStatus;
  provider: PaymentProvider;
  method: string;
  mollie_payment_id?: string;
  created_at: string;
}

// --- API Request/Response Types ---

export interface SaveOrderRequest {
  items: OrderItem[];
  version: number;
}

export interface SubmitOrderResponse {
  order: Order;
}

export interface PaymentInitiationResponse {
  payment_id: string;
  checkout_url: string;
  amount: number;
  status: MolliePaymentStatus;
}

export interface ValidationError {
  item_index: number;
  person_index: number | null;
  product_id: string | null;
  field: string;
  message: string;
  remaining?: number;
}

export interface SubmitValidationErrorResponse {
  errors: ValidationError[];
}

// --- Report Types ---

export type ReportType =
  | 'attendees'
  | 'party'
  | 'tshirts'
  | 'pickups'
  | 'dropoffs'
  | 'financial'
  | 'overview';

export type ReportFormat = 'json' | 'csv';

export interface ReportParams {
  event_id: string;
  type: ReportType;
  status?: OrderStatus | 'all';
  payment_status?: PaymentStatus | 'all';
  format?: ReportFormat;
}

export interface ReportMetadata {
  event_name: string;
  event_location: string;
  event_dates: { start: string; end: string };
  generated_at: string;
}

export interface ReportResponse {
  metadata: ReportMetadata;
  data: Record<string, any>[];
}

// --- Error Types ---

export interface VersionConflictError {
  type: 'VERSION_CONFLICT';
  message: string;
  current_version: number;
}

export interface AuthorizationError {
  type: 'AUTHORIZATION_ERROR';
  message: string;
  status: 403;
}

export type EventBookingApiError = VersionConflictError | AuthorizationError;
