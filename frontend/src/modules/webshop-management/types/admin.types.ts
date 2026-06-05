/**
 * TypeScript interfaces for the Admin Webshop Management module.
 *
 * These types map to the /admin/* API endpoints defined in the design doc.
 */

// --- Order Status ---

export type OrderStatus =
  | 'draft'
  | 'submitted'
  | 'locked'
  | 'order_received'
  | 'payment_pending'
  | 'payment_failed'
  | 'paid'
  | 'picked'
  | 'packed'
  | 'shipped'
  | 'delivered'
  | 'return_requested'
  | 'return_received'
  | 'completed';

// --- Product & Variant Interfaces ---

export interface AdminProduct {
  product_id: string;
  tenant: string;
  name: string;
  description?: string;
  price: number;
  active: boolean;
  product_type?: string;
  max_per_club?: number | null;
  min_per_club?: number | null;
  required_attributes?: object | null;
  is_parent: boolean;
  variants: AdminVariant[];
}

export interface AdminVariant {
  product_id: string;
  parent_id: string;
  variant_attributes: Record<string, string>;
  price?: number | null;
  stock: number;
  sold_count: number;
  allow_oversell: boolean;
  active: boolean;
}

// --- Order Interfaces ---

export interface OrderLineItem {
  product_id: string;
  variant_id: string;
  product_type?: string;
  name: string;
  quantity: number;
  unit_price: number;
  attributes?: Record<string, string>;
}

export interface StatusHistoryEntry {
  from_status: OrderStatus;
  to_status: OrderStatus;
  timestamp: string;
  triggered_by: string;
}

export interface PaymentRecord {
  payment_id: string;
  order_id: string;
  amount: number;
  date: string;
  description?: string;
  recorded_by: string;
  created_at: string;
}

export interface AdminOrder {
  order_id: string;
  tenant: string;
  customer_name: string;
  club_name?: string;
  status: OrderStatus;
  payment_status: 'paid' | 'partial' | 'unpaid';
  total_amount: number;
  amount_paid: number;
  outstanding: number;
  created_at: string;
  submitted_at?: string;
  items: OrderLineItem[];
  status_history: StatusHistoryEntry[];
  payments: PaymentRecord[];
}

export interface AdminOrdersResponse {
  orders: AdminOrder[];
  total_count: number;
}

// --- Stock Movement Interfaces ---

export interface StockMovement {
  movement_id: string;
  variant_id: string;
  tenant: string;
  type: 'inbound' | 'sale';
  quantity: number;
  purchase_price_per_unit?: number | null;
  total_cost?: number | null;
  supplier_name?: string | null;
  recorded_by: string;
  reference?: string | null;
  order_id?: string | null;
  created_at: string;
}

export interface StockMovementsResponse {
  movements: StockMovement[];
  total_count: number;
}

// --- Request Interfaces ---

export interface UpdateOrderStatusRequest {
  target_status: OrderStatus;
}

export interface RecordPaymentRequest {
  order_id: string;
  amount: number;
  date: string;
  description?: string;
}

export interface AddStockRequest {
  quantity: number;
  purchase_price_per_unit: number;
  supplier_name: string;
  reference?: string;
}

export interface CreateProductRequest {
  tenant: string;
  name: string;
  description?: string;
  price: number;
  product_type?: string;
  max_per_club?: number | null;
  min_per_club?: number | null;
  required_attributes?: object | null;
}

export interface CreateVariantRequest {
  variant_attributes: Record<string, string>;
  price?: number | null;
  stock?: number;
  allow_oversell?: boolean;
}

export interface UpdateVariantRequest {
  stock?: number;
  allow_oversell?: boolean;
  price?: number | null;
  active?: boolean;
}

// --- Report Interfaces ---

export interface ReportResponse {
  generated_at: string;
  summary: {
    total_orders: number;
    total_revenue: number;
    total_paid: number;
    total_outstanding: number;
    by_product_type?: Record<string, Record<OrderStatus, number>>;
    by_product?: {
      product_name: string;
      items_sold: number;
      revenue: number;
    }[];
    purchase_cost?: {
      total_inbound_cost: number;
      by_variant?: {
        variant_id: string;
        product_name: string;
        weighted_avg_cost: number;
        selling_price: number;
        gross_margin: number;
      }[];
    };
  };
}
