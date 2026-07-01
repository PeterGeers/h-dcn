import { useState, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { orderService } from '../services/api';

export interface CartItem {
  product_id: string;
  variant_id: string;
  variant_attributes?: Record<string, string>;
  name?: string;
  price?: number;
  quantity: number;
}

interface UseWebshopCartReturn {
  cartItems: CartItem[];
  setCartItems: React.Dispatch<React.SetStateAction<CartItem[]>>;
  cartId: string | null;
  setCartId: React.Dispatch<React.SetStateAction<string | null>>;
  orderVersion: number;
  setOrderVersion: React.Dispatch<React.SetStateAction<number>>;
  initializeCart: () => Promise<void>;
  handleAddToCart: (cartItem: CartItem) => Promise<void>;
  handleUpdateQuantity: (product_id: string, newQuantity: number) => Promise<void>;
  handleRemoveFromCart: (product_id: string) => Promise<void>;
  handleSaveCart: () => Promise<void>;
  handleClearCart: () => Promise<void>;
  updateCartOnServer: (newItems: CartItem[]) => Promise<void>;
}

export function useWebshopCart(): UseWebshopCartReturn {
  const { t } = useTranslation('webshop');
  const toast = useToast();

  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [cartId, setCartId] = useState<string | null>(null);
  const [orderVersion, setOrderVersion] = useState<number>(1);

  const initializeCart = useCallback(async () => {
    try {
      const savedOrderId = localStorage.getItem('hdcn_cart_id');

      if (savedOrderId) {
        // Validate the stored order still exists and is in draft status
        const orderResponse = await orderService.getOrder(savedOrderId);

        if (orderResponse.success && orderResponse.data) {
          const existingOrder = orderResponse.data;
          if (existingOrder.status === 'draft') {
            setCartId(savedOrderId);
            setOrderVersion(existingOrder.version || 1);
            // Restore cart items from the order
            if (existingOrder.items && existingOrder.items.length > 0) {
              setCartItems(existingOrder.items.map((item: any) => ({
                product_id: item.product_id,
                variant_id: item.variant_id || '',
                variant_attributes: item.variant_attributes,
                name: item.name || item.product_name || '',
                price: Number(item.unit_price || 0),
                quantity: item.quantity || 1,
              })));
            }
            return;
          }
        }

        // Order not found or no longer draft — clear stale reference
        localStorage.removeItem('hdcn_cart_id');
      }

      const response = await orderService.createDraft({ event_id: null });
      const newOrderId = response.data?.order_id;
      const version = response.data?.version || 1;

      if (newOrderId) {
        setCartId(newOrderId);
        setOrderVersion(version);
        localStorage.setItem('hdcn_cart_id', newOrderId);
      }
    } catch (error) {
      setCartId(null);
      toast({
        title: t('errors.service_unavailable_title'),
        description: t('errors.service_unavailable_desc'),
        status: 'error',
        duration: 5000,
      });
    }
  }, [toast, t]);

  const updateCartOnServer = async (newItems: CartItem[]) => {
    if (cartId) {
      try {
        const itemsData = newItems.map(item => ({
          product_id: item.product_id,
          variant_id: item.variant_id,
          variant_attributes: item.variant_attributes,
          quantity: item.quantity,
          unit_price: Number(item.price || 0),
        }));

        const response = await orderService.updateItems(cartId, { version: orderVersion, items: itemsData });
        if (response.data?.version) {
          setOrderVersion(response.data.version);
        }
      } catch (error: any) {
        if (error?.response?.status === 409) {
          toast({
            title: t('cart.version_conflict', { defaultValue: 'Versieconflict' }),
            description: t('cart.version_conflict_desc', { defaultValue: 'Je bestelling is door een andere sessie gewijzigd. Ververs de pagina.' }),
            status: 'warning',
            duration: 5000,
          });
        } else {
          console.error('Failed to sync order with server:', error);
        }
      }
    }
  };

  const handleAddToCart = async (cartItem: CartItem) => {
    try {
      let newItems: CartItem[];

      const existingItemIndex = cartItems.findIndex(item =>
        item.product_id === cartItem.product_id &&
        item.variant_id === cartItem.variant_id
      );

      if (existingItemIndex >= 0) {
        newItems = cartItems.map((item, index) =>
          index === existingItemIndex
            ? { ...item, quantity: item.quantity + cartItem.quantity }
            : item
        );
      } else {
        newItems = [...cartItems, cartItem];
      }

      setCartItems(newItems);
      await updateCartOnServer(newItems);

      toast({
        title: t('product.added'),
        status: 'success',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: t('product.add_error'),
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleUpdateQuantity = async (product_id: string, newQuantity: number) => {
    try {
      if (newQuantity <= 0) {
        const newItems = cartItems.filter(item => item.product_id !== product_id);
        setCartItems(newItems);
        await updateCartOnServer(newItems);
        return;
      }

      const newItems = cartItems.map(item =>
        item.product_id === product_id
          ? { ...item, quantity: newQuantity }
          : item
      );

      setCartItems(newItems);
      await updateCartOnServer(newItems);
    } catch (error) {
      toast({
        title: t('product.quantity_error'),
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleRemoveFromCart = async (product_id: string) => {
    try {
      const newItems = cartItems.filter(item => item.product_id !== product_id);
      setCartItems(newItems);
      await updateCartOnServer(newItems);

      toast({
        title: t('product.removed'),
        status: 'info',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: t('product.remove_error'),
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleSaveCart = async () => {
    if (cartItems.length === 0) {
      toast({
        title: t('cart.empty'),
        description: t('cart.save_hint'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    try {
      await updateCartOnServer(cartItems);

      toast({
        title: t('cart.saved'),
        description: t('cart.saved_desc', { count: cartItems.length }),
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: t('errors.cart_save_error'),
        description: t('errors.cart_save_error_desc'),
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleClearCart = async () => {
    try {
      if (cartId) {
        localStorage.removeItem('hdcn_cart_id');
      }
      setCartItems([]);
      setCartId(null);
      setOrderVersion(1);

      await initializeCart();

      toast({
        title: t('cart.cleared'),
        status: 'info',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: t('errors.cart_clear_error'),
        status: 'error',
        duration: 3000,
      });
    }
  };

  return {
    cartItems,
    setCartItems,
    cartId,
    setCartId,
    orderVersion,
    setOrderVersion,
    initializeCart,
    handleAddToCart,
    handleUpdateQuantity,
    handleRemoveFromCart,
    handleSaveCart,
    handleClearCart,
    updateCartOnServer,
  };
}
