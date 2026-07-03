import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Container, useToast, Spinner, Center, Stack, Alert, AlertIcon, AlertTitle, AlertDescription } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import ProductTable from './components/ProductTable';
import ProductCard from './components/ProductCard';
import DraftOrderModal from './components/DraftOrderModal';
import CheckoutModal from './components/CheckoutModal';
import OrdersAdmin from './components/OrdersAdmin';
import MyOrders from './components/MyOrders';
import WebshopHeader from './components/WebshopHeader';
import WebshopOrderSuccessOverlay from './components/WebshopOrderSuccessOverlay';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { productService } from './services/api';
import { FilterPanel, GenericFilter } from '../../components/filters';
import { useWebshopCart } from './hooks/useWebshopCart';
import { useWebshopUser } from './hooks/useWebshopUser';
import { usePaymentSuccess } from './hooks/usePaymentSuccess';

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

interface Product {
  product_id: string;
  id?: string;
  name?: string;
  naam?: string;
  groep?: string;
  subgroep?: string;
  price?: number;
  prijs?: number | string;
  images?: string[];
  is_parent?: boolean;
  event_id?: string | null;
  active?: boolean;
}

interface WebshopPageProps {
  user: User;
}

function WebshopPage({ user }: WebshopPageProps) {
  const { t } = useTranslation('webshop');
  const toast = useToast();

  // Cart state & handlers
  const {
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
  } = useWebshopCart();

  // User/member info
  const { userName, memberInfo, currentMemberId, loadUserInfo } = useWebshopUser(user);

  // UI state
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedGroep, setSelectedGroep] = useState<string>('');
  const [selectedSubgroep, setSelectedSubgroep] = useState<string>('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isProductCardOpen, setIsProductCardOpen] = useState<boolean>(false);
  const [isDraftOrderModalOpen, setIsDraftOrderModalOpen] = useState<boolean>(false);
  const [isCheckoutModalOpen, setIsCheckoutModalOpen] = useState<boolean>(false);
  const [showOrdersAdmin, setShowOrdersAdmin] = useState<boolean>(false);
  const [showMyOrders, setShowMyOrders] = useState<boolean>(false);
  const [showOrderSuccess, setShowOrderSuccess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  // Payment success handler
  const handlePaymentSuccess = usePaymentSuccess({
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
  });

  const loadProducts = useCallback(async () => {
    try {
      const webshopProducts = await productService.getWebshopProducts();
      setProducts(webshopProducts);
    } catch (error) {
      const mockProducts: Product[] = [
        {
          product_id: 'mock-1',
          naam: 'H-DCN T-Shirt',
          groep: 'Kleding',
          subgroep: 'T-shirts',
          prijs: 25.00,
          images: [],
          is_parent: true,
          event_id: null,
          active: true,
        },
        {
          product_id: 'mock-2',
          naam: 'H-DCN Hoodie',
          groep: 'Kleding',
          subgroep: 'Hoodies',
          prijs: 45.00,
          images: [],
          is_parent: true,
          event_id: null,
          active: true,
        },
        {
          product_id: 'mock-3',
          naam: 'H-DCN Pet',
          groep: 'Accessoires',
          subgroep: 'Hoofddeksels',
          prijs: 18.00,
          images: [],
          is_parent: true,
          event_id: null,
          active: true,
        }
      ];
      setProducts(mockProducts);
      toast({
        title: t('demo.title'),
        description: t('demo.description'),
        status: 'warning',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }, [toast, t]);

  const { groepOptions, subgroepOptions } = useMemo(() => {
    const groups = new Set<string>();
    const subgroups = new Set<string>();
    products.forEach(p => {
      if (p.groep) groups.add(p.groep);
      if (p.subgroep && (!selectedGroep || p.groep === selectedGroep)) {
        subgroups.add(p.subgroep);
      }
    });
    return {
      groepOptions: Array.from(groups).sort().map(g => ({ value: g, label: g })),
      subgroepOptions: Array.from(subgroups).sort().map(s => ({ value: s, label: s })),
    };
  }, [products, selectedGroep]);

  const filteredProducts = useMemo(() => {
    let filtered = products;
    if (selectedGroep) {
      filtered = filtered.filter(p => p.groep === selectedGroep);
    }
    if (selectedSubgroep) {
      filtered = filtered.filter(p => p.subgroep === selectedSubgroep);
    }
    filtered = filtered.filter(p => p.active !== false);
    return filtered;
  }, [products, selectedGroep, selectedSubgroep]);

  useEffect(() => {
    loadProducts();
    initializeCart();
    loadUserInfo();

    // Detect Mollie payment return: URL has ?payment=complete&order_id=...
    // This means the payment flow is done (not necessarily successful).
    // Fetch the order to check actual payment_status.
    const urlParams = new URLSearchParams(window.location.search);
    const paymentComplete = urlParams.get('payment');
    const returnOrderId = urlParams.get('order_id');

    if (paymentComplete === 'complete' && returnOrderId) {
      // Clean up URL params immediately
      const url = new URL(window.location.href);
      url.searchParams.delete('payment');
      url.searchParams.delete('order_id');
      window.history.replaceState({}, '', url.toString());

      // Store order_id for the success overlay PDF download button
      const existingOrder = localStorage.getItem('latest_order');
      if (!existingOrder) {
        localStorage.setItem('latest_order', JSON.stringify({
          orderId: returnOrderId,
          timestamp: new Date().toISOString(),
          items: [],
          subtotal_amount: '0.00',
          total_amount: '0.00',
        }));
      } else {
        // Ensure orderId is set correctly on existing data
        try {
          const parsed = JSON.parse(existingOrder);
          if (!parsed.orderId || parsed.orderId.startsWith('ORDER_')) {
            parsed.orderId = returnOrderId;
            localStorage.setItem('latest_order', JSON.stringify(parsed));
          }
        } catch { /* ignore parse errors */ }
      }

      // Show order success overlay (payment confirmation with PDF download)
      setShowOrderSuccess(true);
    }
  }, [loadProducts, initializeCart, loadUserInfo]);

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  return (
    <FunctionGuard
      user={user}
      functionName="webshop"
      action="read"
      requiredRoles={['hdcnLeden']}
      fallback={
        <Box minH="100vh" bg="gray.100" display="flex" alignItems="center" justifyContent="center">
          <Alert status="warning" maxW="md">
            <AlertIcon />
            <Box>
              <AlertTitle>{t('access.no_access_title')}</AlertTitle>
              <AlertDescription>
                {t('access.no_access_desc')}
              </AlertDescription>
            </Box>
          </Alert>
        </Box>
      }
    >
      <Box minH="100vh">
        <WebshopHeader
          user={user}
          cartItemCount={cartItems.length}
          showOrdersAdmin={showOrdersAdmin}
          showMyOrders={showMyOrders}
          onToggleOrdersAdmin={() => { setShowOrdersAdmin(!showOrdersAdmin); setShowMyOrders(false); }}
          onToggleMyOrders={() => { setShowMyOrders(!showMyOrders); setShowOrdersAdmin(false); }}
          onOpenCart={() => setIsDraftOrderModalOpen(true)}
        />

        <Container maxW="container.xl" py={6}>
          {showMyOrders ? (
            <MyOrders />
          ) : showOrdersAdmin ? (
            <FunctionGuard
              user={user}
              functionName="orders"
              action="read"
              requiredRoles={['Products_CRUD', 'System_User_Management']}
              fallback={
                <Alert status="warning">
                  <AlertIcon />
                  <Box>
                    <AlertTitle>{t('orders.no_access_title')}</AlertTitle>
                    <AlertDescription>
                      {t('orders.no_access_desc')}
                    </AlertDescription>
                  </Box>
                </Alert>
              }
            >
              <OrdersAdmin />
            </FunctionGuard>
          ) : (
            <Stack direction={{ base: 'column', lg: 'row' }} spacing={6}>
              <Box w={{ base: 'full', lg: '300px' }}>
                <FilterPanel
                  hasActiveFilters={!!selectedGroep || !!selectedSubgroep}
                  onReset={() => { setSelectedGroep(''); setSelectedSubgroep(''); }}
                >
                  <GenericFilter
                    label={t('filter.group', 'Groep')}
                    value={selectedGroep}
                    options={groepOptions}
                    onChange={(v) => { setSelectedGroep(v); setSelectedSubgroep(''); }}
                    placeholder={t('filter.all_groups', 'Alle groepen')}
                  />
                  {subgroepOptions.length > 0 && (
                    <GenericFilter
                      label={t('filter.subgroup', 'Subgroep')}
                      value={selectedSubgroep}
                      options={subgroepOptions}
                      onChange={setSelectedSubgroep}
                      placeholder={t('filter.all_subgroups', 'Alle subgroepen')}
                    />
                  )}
                </FilterPanel>
              </Box>

              <Box flex={1}>
                <ProductTable
                  products={filteredProducts}
                  onProductSelect={(product: Product) => {
                    setSelectedProduct(product);
                    setIsProductCardOpen(true);
                  }}
                />
              </Box>
            </Stack>
          )}
        </Container>

        {selectedProduct && (
          <ProductCard
            product={selectedProduct}
            isOpen={isProductCardOpen}
            onClose={() => setIsProductCardOpen(false)}
            onAddToCart={handleAddToCart}
          />
        )}

        <DraftOrderModal
          isOpen={isDraftOrderModalOpen}
          onClose={() => setIsDraftOrderModalOpen(false)}
          items={cartItems}
          orderId={cartId}
          orderVersion={orderVersion}
          onRemoveItem={handleRemoveFromCart}
          onUpdateQuantity={handleUpdateQuantity}
          onCheckout={() => {
            if (cartItems.length === 0) {
              toast({
                title: t('cart.empty'),
                description: t('cart.empty_hint'),
                status: 'warning',
                duration: 3000,
              });
              return;
            }
            setIsDraftOrderModalOpen(false);
            setIsCheckoutModalOpen(true);
          }}
          onSaveOrder={handleSaveCart}
          onClearOrder={handleClearCart}
          onVersionConflict={() => {
            toast({
              title: t('cart.version_conflict', { defaultValue: 'Versieconflict' }),
              description: t('cart.version_conflict_desc', { defaultValue: 'Je bestelling is gewijzigd. Ververs de pagina.' }),
              status: 'warning',
              duration: 5000,
            });
          }}
        />

        <CheckoutModal
          isOpen={isCheckoutModalOpen}
          onClose={() => setIsCheckoutModalOpen(false)}
          cartItems={cartItems}
          userEmail={user?.attributes?.email || memberInfo?.email || ''}
          memberInfo={memberInfo}
          orderId={cartId || undefined}
          onPaymentSuccess={handlePaymentSuccess}
        />

        {showOrderSuccess && (
          <WebshopOrderSuccessOverlay onClose={() => setShowOrderSuccess(false)} />
        )}
      </Box>
    </FunctionGuard>
  );
}

export default WebshopPage;
