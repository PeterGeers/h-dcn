/**
 * Order transformer utility — converts between person-centric form state
 * and the flat order items array used by the backend.
 *
 * The person-centric form groups items by person (name + role + products),
 * while the backend stores a flat items array where each item has a product_id
 * and item_fields_data containing the person's name/role.
 *
 * Validates: Requirements 11.5, 11.6, 11.7
 */

import { OrderItem, Product } from '../types/eventBooking.types';

// --- Person-centric form state types ---

export interface PersonProduct {
  product_id: string;
  variant_id: string | null;
  fields: Record<string, any>;
}

export interface PersonFormEntry {
  name: string;
  role: string;
  products: PersonProduct[];
}

export interface PersonFormState {
  persons: PersonFormEntry[];
}

// --- Transformation: Form State → Order Items ---

/**
 * Transform person-centric form state into a flat order items array.
 *
 * Each person may have multiple products. Each product becomes a separate
 * OrderItem with the person's name and role stored in item_fields_data
 * alongside any product-specific fields.
 *
 * @param formState - The person-centric form state from the booking wizard
 * @param products - Available product definitions (used to look up unit_price)
 * @returns Flat array of OrderItem objects ready to send to the backend
 */
export function formStateToOrderItems(
  formState: PersonFormState,
  products: Product[]
): OrderItem[] {
  const productMap = new Map(products.map((p) => [p.product_id, p]));
  const items: OrderItem[] = [];

  for (const person of formState.persons) {
    for (const personProduct of person.products) {
      const productDef = productMap.get(personProduct.product_id);
      const unitPrice = productDef?.price ?? 0;

      const itemFieldsData: Record<string, any> = {
        name: person.name,
        role: person.role,
        ...personProduct.fields,
      };

      items.push({
        product_id: personProduct.product_id,
        variant_id: personProduct.variant_id,
        item_fields_data: itemFieldsData,
        unit_price: unitPrice,
        line_total: unitPrice,
      });
    }
  }

  return items;
}

// --- Transformation: Order Items → Form State ---

/**
 * Transform a flat order items array back into person-centric form state.
 *
 * Groups items by the person's name (from item_fields_data.name).
 * Multiple items with the same name are grouped under a single person entry.
 * The role is taken from the first item encountered for that person.
 *
 * @param items - Flat array of OrderItem objects from the backend
 * @returns Person-centric form state for the booking wizard
 */
export function orderItemsToFormState(items: OrderItem[]): PersonFormState {
  const personMap = new Map<string, PersonFormEntry>();

  for (const item of items) {
    const name = (item.item_fields_data.name as string) || '';
    const role = (item.item_fields_data.role as string) || '';

    // Extract product-specific fields (everything except name and role)
    const { name: _name, role: _role, ...productFields } = item.item_fields_data;

    const personProduct: PersonProduct = {
      product_id: item.product_id,
      variant_id: item.variant_id,
      fields: productFields,
    };

    if (personMap.has(name)) {
      personMap.get(name)!.products.push(personProduct);
    } else {
      personMap.set(name, {
        name,
        role,
        products: [personProduct],
      });
    }
  }

  return {
    persons: Array.from(personMap.values()),
  };
}
