/**
 * StatusBadge Component
 *
 * Displays an order status as a colored badge.
 * Maps each OrderStatus value to an appropriate Chakra UI color scheme.
 */

import React from 'react';
import { Badge } from '@chakra-ui/react';
import { OrderStatus } from '../types/admin.types';

export interface StatusBadgeProps {
  /** The order status to display */
  status: OrderStatus;
}

const STATUS_COLOR_MAP: Record<OrderStatus, string> = {
  draft: 'gray',
  submitted: 'blue',
  locked: 'green',
  order_received: 'teal',
  payment_pending: 'yellow',
  payment_failed: 'red',
  paid: 'green',
  picked: 'purple',
  packed: 'purple',
  shipped: 'orange',
  delivered: 'teal',
  return_requested: 'pink',
  return_received: 'pink',
  completed: 'green',
};

/**
 * Formats a status string for display.
 * Replaces underscores with spaces and capitalizes the first letter.
 */
export function formatStatus(status: string): string {
  return status
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase());
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const colorScheme = STATUS_COLOR_MAP[status] || 'gray';

  return (
    <Badge colorScheme={colorScheme} fontSize="xs" textTransform="capitalize">
      {formatStatus(status)}
    </Badge>
  );
};

export default StatusBadge;
