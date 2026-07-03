import React, { useEffect, useState } from 'react';
import { Box, Button, Text, VStack, Spinner } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import OrderConfirmation from './OrderConfirmation';
import { orderService } from '../services/api';

interface OrderItem {
  name?: string;
  variant_attributes?: Record<string, string>;
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

interface ShippingAddress {
  name?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
}

interface DeliveryOption {
  label: string;
}

interface OrderData {
  orderId: string;
  timestamp: string;
  customer_info?: CustomerInfo;
  shipping_address?: ShippingAddress;
  delivery_option?: DeliveryOption;
  delivery_cost?: string;
  items: OrderItem[];
  subtotal_amount: string;
  total_amount: string;
}

interface OrderSuccessProps {
  onClose: () => void;
}

const OrderSuccess: React.FC<OrderSuccessProps> = ({ onClose }) => {
  const [orderData, setOrderData] = useState<OrderData | null>(null);
  const [loading, setLoading] = useState(true);
  const { t } = useTranslation('webshop');

  useEffect(() => {
    const loadOrder = async () => {
      try {
        const latestOrder = localStorage.getItem('latest_order');
        if (!latestOrder) {
          setLoading(false);
          return;
        }

        const parsedOrder = JSON.parse(latestOrder);
        const orderId = parsedOrder.orderId || parsedOrder.order_id;

        // If localStorage has complete data (items present), use it directly
        if (parsedOrder.items && parsedOrder.items.length > 0) {
          setOrderData(parsedOrder);
          setLoading(false);
          return;
        }

        // Otherwise, fetch the order from the backend for complete data
        if (orderId) {
          try {
            const response = await orderService.getOrder(orderId);
            const order = response.data || response;
            if (order && order.order_id) {
              setOrderData({
                orderId: order.order_id,
                timestamp: order.submitted_at || order.created_at || '',
                customer_info: {
                  name: order.customer_name || '',
                  email: order.customer_email || order.user_email || '',
                  phone: order.customer_phone || '',
                  straat: order.shipping_address?.straat || '',
                  postcode: order.shipping_address?.postcode || '',
                  woonplaats: order.shipping_address?.woonplaats || '',
                },
                shipping_address: order.shipping_address || undefined,
                delivery_option: order.delivery_option
                  ? (typeof order.delivery_option === 'string'
                    ? { label: order.delivery_option }
                    : order.delivery_option)
                  : undefined,
                delivery_cost: order.delivery_cost ? String(order.delivery_cost) : undefined,
                items: (order.items || []).map((item: any) => ({
                  name: item.name || item.naam || '',
                  variant_attributes: item.variant_attributes,
                  quantity: item.quantity || 1,
                  price: item.unit_price || item.price || 0,
                })),
                subtotal_amount: String(order.subtotal_amount || '0.00'),
                total_amount: String(order.total_amount || '0.00'),
              });
              setLoading(false);
              return;
            }
          } catch (err) {
            console.warn('Could not fetch order from backend:', err);
          }
        }

        // Final fallback: use whatever localStorage has
        setOrderData(parsedOrder);
      } catch (err) {
        console.error('Error loading order data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadOrder();
  }, []);

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.400">{t('orders.loading', { defaultValue: 'Bestelling laden...' })}</Text>
      </Box>
    );
  }

  if (!orderData) {
    return (
      <Box p={6} textAlign="center">
        <Text>{t('orders.no_data', { defaultValue: 'Geen ordergegevens gevonden.' })}</Text>
        <Button onClick={onClose} mt={4}>{t('buttons.close', { ns: 'common', defaultValue: 'Sluiten' })}</Button>
      </Box>
    );
  }

  return (
    <VStack spacing={4} p={6}>
      <Text fontSize="xl" fontWeight="bold" color="green.500">
        {t('orders.success', { defaultValue: 'Bestelling succesvol geplaatst!' })}
      </Text>
      <Text>{t('orders.order_number', { defaultValue: 'Ordernummer' })}: {orderData.orderId}</Text>
      
      <Box border="1px solid #ddd" p={4}>
        <OrderConfirmation orderData={orderData} />
      </Box>
      
      <Button onClick={onClose} colorScheme="blue">
        {t('orders.back_to_webshop', { defaultValue: 'Terug naar webshop' })}
      </Button>
    </VStack>
  );
};

export default OrderSuccess;