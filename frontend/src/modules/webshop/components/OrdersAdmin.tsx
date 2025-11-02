import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  useToast,
  Collapse,
  useDisclosure,
  HStack,
  Divider
} from '@chakra-ui/react';

interface OrderItem {
  name?: string;
  naam?: string;
  selectedOption?: string;
  quantity: number;
  price?: number;
}

interface CustomerInfo {
  name?: string;
  voornaam?: string;
  achternaam?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
  email?: string;
  phone?: string;
}

interface DeliveryOption {
  label: string;
}

interface Order {
  orderId: string;
  timestamp: string;
  total_amount: string;
  item_count: number;
  delivery_option?: DeliveryOption;
  customer_info?: CustomerInfo;
  customer_id?: string;
  payment_method_id?: string;
  delivery_cost?: string;
  subtotal_amount?: string;
  items: OrderItem[];
}

interface OrderItemComponentProps {
  order: Order;
}

const OrdersAdmin: React.FC = () => {
  const [localOrders, setLocalOrders] = useState<Order[]>([]);
  const toast = useToast();

  const loadLocalOrders = useCallback(() => {
    try {
      const ordersData = localStorage.getItem('hdcn_orders') || '[]';
      const orders = JSON.parse(ordersData);
      if (Array.isArray(orders)) {
        setLocalOrders(orders);
      } else {
        console.warn('Invalid orders data format, resetting to empty array');
        localStorage.removeItem('hdcn_orders');
        setLocalOrders([]);
      }
    } catch (error) {
      console.error('Failed to parse local orders:', error);
      localStorage.removeItem('hdcn_orders');
      setLocalOrders([]);
      toast({
        title: 'Lokale orders data beschadigd',
        description: 'Orders data is gereset.',
        status: 'warning',
        duration: 3000,
      });
    }
  }, [toast]);

  useEffect(() => {
    loadLocalOrders();
  }, [loadLocalOrders]);

  const clearLocalOrders = (): void => {
    localStorage.removeItem('hdcn_orders');
    setLocalOrders([]);
    toast({
      title: 'Lokale orders gewist',
      status: 'info',
      duration: 2000,
    });
  };

  return (
    <Box p={6} bg="white" borderRadius="md" color="black">
      <VStack spacing={4} align="stretch">
        <Text fontSize="xl" fontWeight="bold">Lokaal Opgeslagen Orders</Text>
        
        <Button onClick={clearLocalOrders} colorScheme="red" size="sm" alignSelf="flex-start">
          Wis Lokale Orders
        </Button>

        {localOrders.length === 0 ? (
          <Text>Geen lokale orders gevonden</Text>
        ) : (
          <VStack spacing={4} align="stretch">
            {localOrders.map((order, index) => (
              <OrderItemComponent key={index} order={order} />
            ))}
          </VStack>
        )}
      </VStack>
    </Box>
  );
};

const OrderItemComponent: React.FC<OrderItemComponentProps> = ({ order }) => {
  const { isOpen, onToggle } = useDisclosure();

  return (
    <Box borderWidth={1} borderRadius="md" p={4} bg="gray.50">
      <HStack justify="space-between" cursor="pointer" onClick={onToggle}>
        <VStack align="start" spacing={1}>
          <Text fontWeight="bold">{order.orderId}</Text>
          <Text fontSize="sm" color="gray.600">
            {new Date(order.timestamp).toLocaleString()}
          </Text>
        </VStack>
        <VStack align="end" spacing={1}>
          <Text fontWeight="bold">€{order.total_amount}</Text>
          <HStack>
            <Badge colorScheme="orange">Lokaal</Badge>
            <Text fontSize="sm">{order.item_count} items</Text>
          </HStack>
          {order.delivery_option && (
            <Text fontSize="xs" color="gray.600">{order.delivery_option.label}</Text>
          )}
        </VStack>
        <Text>{isOpen ? '▼' : '▶'}</Text>
      </HStack>
      
      <Collapse in={isOpen}>
        <Box mt={4}>
          <Divider mb={3} />
          
          <VStack align="stretch" spacing={3}>
            <Box>
              <Text fontWeight="bold" mb={2}>Besteller:</Text>
              {order.customer_info ? (
                <VStack align="start" spacing={1}>
                  <Text fontWeight="bold">{order.customer_info.name || `${order.customer_info.voornaam} ${order.customer_info.achternaam}`}</Text>
                  <Text>{order.customer_info.straat}</Text>
                  <Text>{order.customer_info.postcode} {order.customer_info.woonplaats}</Text>
                  {order.customer_info.email && <Text fontSize="sm">{order.customer_info.email}</Text>}
                  {order.customer_info.phone && <Text fontSize="sm">{order.customer_info.phone}</Text>}
                  <Text fontSize="sm" color="gray.600">ID: {order.customer_id}</Text>
                  <Text fontSize="sm" color="gray.600">Betaling: {order.payment_method_id}</Text>
                </VStack>
              ) : (
                <VStack align="start" spacing={1}>
                  <Text>Klant ID: {order.customer_id}</Text>
                  <Text>Betaling: {order.payment_method_id}</Text>
                </VStack>
              )}
            </Box>
            
            {order.delivery_option && (
              <Box>
                <Text fontWeight="bold" mb={2}>Levering:</Text>
                <VStack align="start" spacing={1}>
                  <Text>{order.delivery_option.label}</Text>
                  <Text>Kosten: €{order.delivery_cost}</Text>
                </VStack>
              </Box>
            )}
            
            <Box>
              <Text fontWeight="bold" mb={2}>Totalen:</Text>
              <VStack align="start" spacing={1}>
                <Text>Subtotaal: €{order.subtotal_amount || order.total_amount}</Text>
                {order.delivery_cost && <Text>Verzending: €{order.delivery_cost}</Text>}
                <Text fontWeight="bold">Totaal: €{order.total_amount}</Text>
              </VStack>
            </Box>
            
            <Box>
              <Text fontWeight="bold" mb={2}>Producten:</Text>
              <Table size="sm" variant="simple">
                <Thead>
                  <Tr>
                    <Th>Product</Th>
                    <Th>Optie</Th>
                    <Th>Aantal</Th>
                    <Th>Prijs</Th>
                    <Th>Totaal</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {order.items.map((item, idx) => (
                    <Tr key={idx}>
                      <Td>{item.name || item.naam}</Td>
                      <Td>{item.selectedOption || '-'}</Td>
                      <Td>{item.quantity}</Td>
                      <Td>€{Number(item.price || 0).toFixed(2)}</Td>
                      <Td>€{(item.quantity * Number(item.price || 0)).toFixed(2)}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </VStack>
        </Box>
      </Collapse>
    </Box>
  );
};

export default OrdersAdmin;