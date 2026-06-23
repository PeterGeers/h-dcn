import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Container, useToast, Spinner, Center, Flex, Button, HStack, Stack, Alert, AlertIcon, AlertTitle, AlertDescription } from '@chakra-ui/react';
import { ArrowBackIcon, ViewIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ProductTable from './components/ProductTable';
import ProductCard from './components/ProductCard';
import DraftOrderModal from './components/DraftOrderModal';
import CheckoutModal from './components/CheckoutModal';
import OrdersAdmin from './components/OrdersAdmin';
import OrderSuccess from './components/OrderSuccess';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { productService, memberService, orderService } from './services/api';
import { ApiService } from '../../services/apiService';
import { formatPrice } from '../../utils/formatPrice';
import { FilterPanel, GenericFilter } from '../../components/filters';

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

interface CartItem {
  product_id: string;
  variant_id: string;
  variant_attributes?: Record<string, string>;
  name?: string;
  price?: number;
  quantity: number;
}

interface MemberInfo {
  member_id?: string;
  voornaam?: string;
  achternaam?: string;
  name?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
  email?: string;
  phone?: string;
}

interface PaymentData {
  paymentMethodId: string;
  amount: number;
  shippingAddress?: any;
  deliveryOption?: {
    cost?: string;
  };
}

interface WebshopPageProps {
  user: User;
}

function WebshopPage({ user }: WebshopPageProps) {
  const navigate = useNavigate();
  const { t } = useTranslation('webshop');
  const { t: tCommon } = useTranslation('common');
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedGroep, setSelectedGroep] = useState<string>('');
  const [selectedSubgroep, setSelectedSubgroep] = useState<string>('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isProductCardOpen, setIsProductCardOpen] = useState<boolean>(false);
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [cartId, setCartId] = useState<string | null>(null);
  const [orderVersion, setOrderVersion] = useState<number>(1);
  const [isDraftOrderModalOpen, setIsDraftOrderModalOpen] = useState<boolean>(false);
  const [isCheckoutModalOpen, setIsCheckoutModalOpen] = useState<boolean>(false);
  const [showOrdersAdmin, setShowOrdersAdmin] = useState<boolean>(false);
  const [showOrderSuccess, setShowOrderSuccess] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [userName, setUserName] = useState<string>('Gebruiker');
  const [memberInfo, setMemberInfo] = useState<MemberInfo | null>(null);
  const [currentMemberId, setCurrentMemberId] = useState<string | null>(null);
  const toast = useToast();

  const initializeCart = useCallback(async () => {
    try {
      const savedOrderId = localStorage.getItem('hdcn_cart_id');
      
      if (savedOrderId) {
        setCartId(savedOrderId);
        return;
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

  const loadProducts = useCallback(async () => {
    try {
      const response = await productService.scanProducts();
      const allProducts: Product[] = response.data || [];
      // Filter to show only products linked to the webshop event
      const webshopProducts = allProducts.filter(
        (p: any) => {
          const eventIds = p.event_ids || [];
          return eventIds.includes('evt-webshop');
        }
      );
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
    // Only show active products
    filtered = filtered.filter(p => p.active !== false);
    return filtered;
  }, [products, selectedGroep, selectedSubgroep]);

  const loadUserInfo = useCallback(async () => {
    try {
      if (user) {
        console.log('=== COGNITO USER DEBUG ===');
        console.log('Full user object:', user);
        console.log('User attributes:', user.attributes);
        console.log('All custom attributes:');
        Object.keys(user.attributes || {}).forEach(key => {
          if (key.startsWith('custom:')) {
            console.log(`  ${key}: ${user.attributes![key]}`);
          }
        });
        
        const email = user.attributes?.email || user.username;
        const memberId = user.attributes?.['custom:member_id'];
        
        console.log('Email:', email);
        console.log('Member ID from custom:member_id:', memberId);
        
        setUserName(email || 'Gebruiker');
        
        // Always try to get member by email first
        try {
          const response = await ApiService.get("/members/me");
          if (response.success && response.data) {
            const memberByEmail = response.data;
            
            if (memberByEmail) {
              console.log('Member found by email:', memberByEmail);
              
              const memberData: MemberInfo = {
                member_id: memberByEmail.member_id,
                voornaam: memberByEmail.voornaam,
                achternaam: memberByEmail.achternaam,
                name: memberByEmail.name,
                straat: memberByEmail.straat,
                postcode: memberByEmail.postcode,
                woonplaats: memberByEmail.woonplaats,
                email: memberByEmail.email,
                phone: memberByEmail.phone || memberByEmail.telefoon
              };
              
              console.log('Setting member data:', memberData);
              setMemberInfo(memberData);
              setUserName(memberData.name || 'Gebruiker');
              setCurrentMemberId(memberByEmail.member_id);
              return;
            }
          }
        } catch (emailError) {
          console.error('Failed to load member by email:', emailError);
        }
        
        if (memberId) {
          console.log('Member ID from Cognito:', memberId);
          setCurrentMemberId(memberId);
          try {
            const response = await memberService.getMember(memberId);
            console.log('Member service response:', response);
            const member = response.data;
            console.log('Member data from database:', member);
            
            const memberData: MemberInfo = {
              member_id: memberId,
              voornaam: member.voornaam || user.attributes?.given_name || '',
              achternaam: member.achternaam || user.attributes?.family_name || '',
              name: member.name || `${member.voornaam || ''} ${member.achternaam || ''}`.trim(),
              straat: member.straat || '',
              postcode: member.postcode || '',
              woonplaats: member.woonplaats || '',
              email: member.email || user.attributes?.email || '',
              phone: member.phone || user.attributes?.phone_number || ''
            };
            
            console.log('Processed member data:', memberData);
            setMemberInfo(memberData);
            setUserName(memberData.name || memberData.voornaam || email || 'Gebruiker');
          } catch (memberError) {
            console.error('Failed to load member data by ID:', memberError);
            
            const fallbackMember: MemberInfo = {
              member_id: memberId,
              voornaam: user.attributes?.given_name || '',
              achternaam: user.attributes?.family_name || '',
              name: `${user.attributes?.given_name || ''} ${user.attributes?.family_name || ''}`.trim(),
              straat: '',
              postcode: '',
              woonplaats: '',
              email: user.attributes?.email || '',
              phone: user.attributes?.phone_number || ''
            };
            setMemberInfo(fallbackMember);
            setUserName(fallbackMember.name || email || 'Gebruiker');
          }
        } else {
          console.log('No member_id found in Cognito attributes');
        }
      }
    } catch (error) {
      setUserName('Gast');
    }
  }, [user]);

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
      
      setIsDraftOrderModalOpen(false);
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

  useEffect(() => {
    loadProducts();
    initializeCart();
    loadUserInfo();
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
        <Flex justify="space-between" align="center" p={4} bg="black" color="orange.400">
          <Button onClick={() => navigate('/')} variant="ghost" color="orange.300" leftIcon={<ArrowBackIcon />}>
            {tCommon('nav.back_to_dashboard')}
          </Button>
          <Box fontSize="xl" fontWeight="bold">{t('title')}</Box>
          <HStack>
            {/* Orders admin button - only show for users with appropriate permissions */}
            <FunctionGuard 
              user={user} 
              functionName="orders" 
              action="read"
              requiredRoles={['Products_CRUD', 'System_User_Management']}
              fallback={null}
            >
              <Button
                onClick={() => setShowOrdersAdmin(!showOrdersAdmin)}
                colorScheme="orange"
                variant="ghost"
                size="sm"
              >
                Orders
              </Button>
            </FunctionGuard>
            <Button
              onClick={() => setIsDraftOrderModalOpen(true)}
              colorScheme="orange"
              variant="outline"
              leftIcon={<ViewIcon />}
            >
              {t('cart.item_count', { count: cartItems.length })}
            </Button>
          </HStack>
        </Flex>
        
        <Container maxW="container.xl" py={6}>
          {showOrdersAdmin ? (
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
          orderId={cartId || undefined}
          onPaymentSuccess={async (paymentData: PaymentData) => {
            try {
              const totalAmount = cartItems.reduce((sum, item) => sum + (Number(item.price || 0) * item.quantity), 0);
              
              const orderId = `ORDER_${Date.now()}`;
              console.log('Creating order with memberInfo:', memberInfo);
              console.log('Current member ID:', currentMemberId);
              
              const orderData = {
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
                console.log('Order API response:', JSON.stringify(response));
                // Use the backend-generated order_id (UUID) for PDF download
                if (response.success && response.data?.order_id) {
                  orderData.orderId = response.data.order_id;
                  console.log('Order created with backend ID:', response.data.order_id);
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
          }}
        />

        {showOrderSuccess && (
          <Box
            position="fixed"
            top={0}
            left={0}
            right={0}
            bottom={0}
            bg="blackAlpha.600"
            display="flex"
            alignItems="center"
            justifyContent="center"
            zIndex={1000}
          >
            <Box
              bg="white"
              borderRadius="md"
              maxW="800px"
              maxH="90vh"
              overflow="auto"
              boxShadow="xl"
            >
              <OrderSuccess onClose={() => setShowOrderSuccess(false)} />
            </Box>
          </Box>
        )}
      </Box>
    </FunctionGuard>
  );
}

export default WebshopPage;