import { useCallback } from 'react';
import { useToast } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { orderService } from '../services/api';
import { formatPrice } from '../../../utils/formatPrice';
import { CartItem } from './useWebshopCart';
import { MemberInfo } from './useWebshopUser';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
    family_name?: string;
    phone_number?: string;
    'custom:member_id'?: string;
  };
  username?: string;
}

interface PaymentData {
  paymentMethodId: string;
  amount: number;
  shippingAddress?: any;
  deliveryOption?: {
    cost?: string;
  };
}

interface UsePaymentSuccessOptions {
  user: User;
  cartItems: CartItem[];
  cartId: string | null;
  memberInfo: MemberInfo | null;
  currentMemberId: string | null;
  userName: string;
  setCartItems: React.Dispatch<React.SetStateAction<CartItem[]>>;
  setCartId: React.Dispatch<React.SetStateAction<string | null>>;
  setOrderVersion: React.Dispatch<React.SetStateAction<number>>;
  setIsCheckoutModalOpen: (open: boolean) => void;
  setShowOrderSuccess: (show: boolean) => void;
  initializeCart: () => Promise<void>;
}

export function usePaymentSuccess({
  user,
  cartItems,
  cartId,
  memberInfo,
  currentMemberId,
  userName,
  setCartItems,
  setCartId,
  setOrderVersion,
  setIsCheckoutModalOpen,
  setShowOrderSuccess,
  initializeCart,
}: UsePaymentSuccessOptions) {
  const { t } = useTranslation('webshop');
  const toast = useToast();

  const handlePaymentSuccess = useCallback(async (paymentData: PaymentData) => {
    try {
      const totalAmount = cartItems.reduce((sum, item) => sum + (Number(item.price || 0) * item.quantity), 0);

      const orderId = `ORDER_${Date.now()}`;

      const orderData: any = {
        order_id: cartId,
        customer_id: currentMemberId || memberInfo?.member_id,
        customer_info: memberInfo || {
          member_id: currentMemberId,
          name: userName,
          email: user?.attributes?.email || '',
          phone: user?.attributes?.phone_number || ''
        },
        shipping_address: paymentData.shippingAddress || memberInfo || {
          name: userName,
          email: user?.attributes?.email || ''
        },
        delivery_cost: paymentData.deliveryOption ? parseFloat(paymentData.deliveryOption.cost || '0').toFixed(2) : '0.00',
        delivery_option: paymentData.deliveryOption || null,
        items: cartItems.map(item => ({
          name: item.name,
          price: formatPrice(item.price),
          product_id: item.product_id,
          variant_id: item.variant_id,
          quantity: item.quantity,
          variant_attributes: item.variant_attributes || {}
        })),
        item_count: cartItems.reduce((sum, item) => sum + item.quantity, 0),
        orderId: orderId,
        payment_method_id: paymentData.paymentMethodId,
        subtotal_amount: totalAmount.toFixed(2),
        timestamp: new Date().toISOString(),
        total_amount: paymentData.amount.toFixed(2)
      };

      try {
        const response = await orderService.createDraft(orderData);
        if (response.success && response.data?.order_id) {
          orderData.orderId = response.data.order_id;
        } else {
          console.error('Order creation failed:', response.error);
        }
      } catch (error) {
        console.error('Backend order failed:', error);
        const localOrders = JSON.parse(localStorage.getItem('hdcn_orders') || '[]');
        localOrders.push(orderData);
        localStorage.setItem('hdcn_orders', JSON.stringify(localOrders));
      }

      localStorage.setItem('latest_order', JSON.stringify(orderData));

      setCartItems([]);
      localStorage.removeItem('hdcn_cart_items');

      if (cartId) {
        try {
          localStorage.removeItem('hdcn_cart_id');
          setCartId(null);
          setOrderVersion(1);
          await initializeCart();
        } catch (error) {
          console.error('Failed to reset draft order state:', error);
        }
      }

      toast({
        title: t('checkout.payment_success'),
        description: t('checkout.payment_success_desc', { order_id: orderId, amount: paymentData.amount.toFixed(2) }),
        status: 'success',
        duration: 5000,
      });

      setIsCheckoutModalOpen(false);
      setShowOrderSuccess(true);
    } catch (error) {
      toast({
        title: t('checkout.payment_error'),
        description: t('checkout.payment_error_desc'),
        status: 'error',
        duration: 5000,
      });
    }
  }, [cartItems, cartId, memberInfo, currentMemberId, userName, user, setCartItems, setCartId, setOrderVersion, setIsCheckoutModalOpen, setShowOrderSuccess, initializeCart, toast, t]);

  return handlePaymentSuccess;
}
