import React, { useState, useEffect, useCallback } from 'react';
import { Box, Container, useToast, Spinner, Center, Flex, Button, HStack, Stack } from '@chakra-ui/react';
import { ArrowBackIcon, ViewIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import ProductFilter from './components/ProductFilter';
import ProductTable from './components/ProductTable';
import ProductCard from './components/ProductCard';
import CartModal from './components/CartModal';
import CheckoutModal from './components/CheckoutModal';
import OrdersAdmin from './components/OrdersAdmin';
import OrderSuccess from './components/OrderSuccess';
import { productService, cartService, memberService, orderService } from './services/api';

function WebshopPage({ user }) {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [selectedFilter, setSelectedFilter] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isProductCardOpen, setIsProductCardOpen] = useState(false);
  const [cartItems, setCartItems] = useState([]);
  const [cartId, setCartId] = useState(null);
  const [isCartModalOpen, setIsCartModalOpen] = useState(false);
  const [isCheckoutModalOpen, setIsCheckoutModalOpen] = useState(false);
  const [showOrdersAdmin, setShowOrdersAdmin] = useState(false);
  const [showOrderSuccess, setShowOrderSuccess] = useState(false);

  const [loading, setLoading] = useState(true);
  const [userName, setUserName] = useState('Gebruiker');
  const [memberInfo, setMemberInfo] = useState(null);
  const [currentMemberId, setCurrentMemberId] = useState(null);
  const toast = useToast();



  const initializeCart = useCallback(async () => {
    try {
      const savedCartId = localStorage.getItem('hdcn_cart_id');
      
      if (savedCartId) {
        try {
          const cartResponse = await cartService.getCart(savedCartId);
          if (cartResponse.data && cartResponse.data.items) {
            setCartId(savedCartId);
            setCartItems(cartResponse.data.items || []);
            
            toast({
              title: 'Winkelwagen hersteld',
              description: `${cartResponse.data.items.length} items teruggevonden`,
              status: 'info',
              duration: 3000,
            });
            return;
          }
        } catch (error) {
          localStorage.removeItem('hdcn_cart_id');
        }
      }
      
      const response = await cartService.createCart({ customer_id: 'current-user' });
      const newCartId = response.data?.cartId || response.data?.cart_id || response.cartId || response.cart_id;
      
      if (newCartId) {
        setCartId(newCartId);
        localStorage.setItem('hdcn_cart_id', newCartId);
      }
    } catch (error) {
      setCartId(null);
      toast({
        title: 'Winkelwagen service niet beschikbaar',
        description: 'De winkelwagen functionaliteit is momenteel niet beschikbaar.',
        status: 'error',
        duration: 5000,
      });
    }
  }, [toast]);

  const loadProducts = useCallback(async () => {
    try {
      const response = await productService.scanProducts();
      setProducts(response.data);
    } catch (error) {
      const mockProducts = [
        {
          id: '1',
          naam: 'H-DCN T-Shirt',
          groep: 'Kleding',
          subgroep: 'T-shirts',
          prijs: 25.00,
          beschrijving: 'Officieel H-DCN T-shirt',
          images: [],
          opties: 'S,M,L,XL'
        },
        {
          id: '2',
          naam: 'H-DCN Hoodie',
          groep: 'Kleding',
          subgroep: 'Hoodies',
          prijs: 45.00,
          beschrijving: 'Warme H-DCN hoodie',
          images: [],
          opties: 'S,M,L,XL'
        },
        {
          id: '3',
          naam: 'H-DCN Pet',
          groep: 'Accessoires',
          subgroep: 'Hoofddeksels',
          prijs: 18.00,
          beschrijving: 'H-DCN baseball cap',
          images: [],
          opties: 'One Size'
        }
      ];
      setProducts(mockProducts);
      toast({
        title: 'Demo modus',
        description: 'Gebruikt mock data omdat API niet beschikbaar is',
        status: 'warning',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const filterProducts = useCallback(() => {
    let filtered = products;
    
    if (selectedFilter) {
      if (selectedFilter.type === 'group') {
        filtered = filtered.filter(p => p.groep === selectedFilter.value);
      } else if (selectedFilter.type === 'subgroup') {
        filtered = filtered.filter(p => p.groep === selectedFilter.group && p.subgroep === selectedFilter.value);
      }
    }
    
    setFilteredProducts(filtered);
  }, [products, selectedFilter]);

  const loadUserInfo = useCallback(async () => {
    try {
      if (user) {
        console.log('=== COGNITO USER DEBUG ===');
        console.log('Full user object:', user);
        console.log('User attributes:', user.attributes);
        console.log('All custom attributes:');
        Object.keys(user.attributes || {}).forEach(key => {
          if (key.startsWith('custom:')) {
            console.log(`  ${key}: ${user.attributes[key]}`);
          }
        });
        
        const email = user.attributes?.email || user.username;
        const memberId = user.attributes?.['custom:member_id'];
        
        console.log('Email:', email);
        console.log('Member ID from custom:member_id:', memberId);
        
        setUserName(email);
        
        // Always try to get member by email first
        try {
          const allMembersResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL}/members`);
          if (allMembersResponse.ok) {
            const allMembers = await allMembersResponse.json();
            const memberByEmail = allMembers.find(m => m.email === email);
            
            if (memberByEmail) {
              console.log('Member found by email:', memberByEmail);
              
              const memberData = {
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
              setUserName(memberData.name);
              setCurrentMemberId(memberByEmail.member_id);
              return; // Exit early if found
            }
          }
        } catch (emailError) {
          console.error('Failed to load member by email:', emailError);
        }
        
        if (memberId) {
          console.log('Member ID from Cognito:', memberId);
          setCurrentMemberId(memberId);
          try {
            // First try to get member by ID
            const response = await memberService.getMember(memberId);
            console.log('Member service response:', response);
            const member = response.data;
            console.log('Member data from database:', member);
            
            // Use actual member data from database
            const memberData = {
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
            setUserName(memberData.name || memberData.voornaam || email);
          } catch (memberError) {
            console.error('Failed to load member data by ID:', memberError);
            
            // Try to get all members and find by email
            try {
              const allMembersResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL}/members`);
              if (allMembersResponse.ok) {
                const allMembers = await allMembersResponse.json();
                const memberByEmail = allMembers.find(m => m.email === email);
                
                if (memberByEmail) {
                  console.log('Member found by email:', memberByEmail);
                  
                  const memberData = {
                    member_id: memberByEmail.member_id,
                    voornaam: memberByEmail.voornaam || user.attributes?.given_name || '',
                    achternaam: memberByEmail.achternaam || user.attributes?.family_name || '',
                    name: memberByEmail.name || `${memberByEmail.voornaam || ''} ${memberByEmail.achternaam || ''}`.trim(),
                    straat: memberByEmail.straat || '',
                    postcode: memberByEmail.postcode || '',
                    woonplaats: memberByEmail.woonplaats || '',
                    email: memberByEmail.email || user.attributes?.email || '',
                    phone: memberByEmail.phone || memberByEmail.telefoon || user.attributes?.phone_number || ''
                  };
                  
                  setMemberInfo(memberData);
                  setUserName(memberData.name || memberData.voornaam || email);
                  setCurrentMemberId(memberByEmail.member_id);
                  return;
                }
              }
            } catch (emailError) {
              console.error('Failed to load member data by email:', emailError);
            }
            
            // Final fallback to Cognito attributes
            const fallbackMember = {
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
            setUserName(fallbackMember.name || email);
          }
        } else {
          console.log('No member_id found in Cognito attributes');
        }
      }
    } catch (error) {
      setUserName('Gast');
    }
  }, [user]);

  const updateCartOnServer = async (newItems) => {
    if (cartId) {
      try {
        const totalAmount = newItems.reduce((sum, item) => sum + (Number(item.price || 0) * item.quantity), 0);
        const itemCount = newItems.reduce((sum, item) => sum + item.quantity, 0);
        
        const cartData = {
          items: newItems,
          total_amount: totalAmount.toFixed(2),
          item_count: itemCount
        };
        
        await cartService.updateCartItems(cartId, cartData);
      } catch (error) {
        console.error('Failed to sync cart with server:', error);
      }
    }
  };

  const handleAddToCart = async (cartItem) => {
    try {
      let newItems;
      
      const existingItemIndex = cartItems.findIndex(item => 
        item.product_id === cartItem.product_id && 
        item.selectedOption === cartItem.selectedOption
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
        title: 'Product toegevoegd',
        status: 'success',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: 'Fout bij toevoegen aan winkelwagen',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleUpdateQuantity = async (product_id, newQuantity) => {
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
        title: 'Fout bij wijzigen aantal',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleRemoveFromCart = async (product_id) => {
    try {
      const newItems = cartItems.filter(item => item.product_id !== product_id);
      setCartItems(newItems);
      await updateCartOnServer(newItems);
      
      toast({
        title: 'Product verwijderd',
        status: 'info',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: 'Fout bij verwijderen uit winkelwagen',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleSaveCart = async () => {
    if (cartItems.length === 0) {
      toast({
        title: 'Winkelwagen is leeg',
        description: 'Voeg eerst producten toe om te bewaren.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    try {
      await updateCartOnServer(cartItems);
      
      toast({
        title: 'Winkelwagen bewaard',
        description: `${cartItems.length} items bewaard voor later`,
        status: 'success',
        duration: 3000,
      });
      
      setIsCartModalOpen(false);
    } catch (error) {
      toast({
        title: 'Fout bij bewaren winkelwagen',
        description: 'Probeer het later opnieuw.',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleClearCart = async () => {
    try {
      if (cartId) {
        await cartService.clearCart(cartId);
        localStorage.removeItem('hdcn_cart_id');
      }
      setCartItems([]);
      setCartId(null);
      
      await initializeCart();
      
      toast({
        title: 'Winkelwagen geleegd',
        status: 'info',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: 'Fout bij legen winkelwagen',
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

  useEffect(() => {
    filterProducts();
  }, [filterProducts]);

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  return (
    <Box minH="100vh">
      <Flex justify="space-between" align="center" p={4} bg="black" color="orange.400">
        <Button onClick={() => navigate('/')} variant="ghost" color="orange.300" leftIcon={<ArrowBackIcon />}>
          Terug naar Dashboard
        </Button>
        <Box fontSize="xl" fontWeight="bold">H-DCN Webshop</Box>
        <HStack>
          <Button
            onClick={() => setShowOrdersAdmin(!showOrdersAdmin)}
            colorScheme="orange"
            variant="ghost"
            size="sm"
          >
            Orders
          </Button>
          <Button
            onClick={() => setIsCartModalOpen(true)}
            colorScheme="orange"
            variant="outline"
            leftIcon={<ViewIcon />}
          >
            Winkelwagen ({cartItems.length})
          </Button>
        </HStack>
      </Flex>
      
      <Container maxW="container.xl" py={6}>
        {showOrdersAdmin ? (
          <OrdersAdmin />
        ) : (
          <Stack direction={{ base: 'column', lg: 'row' }} spacing={6}>
            <Box w={{ base: 'full', lg: '300px' }}>
              <ProductFilter
                products={products}
                selectedFilter={selectedFilter}
                onFilterChange={setSelectedFilter}
              />
            </Box>
            
            <Box flex={1}>
              <ProductTable
                products={filteredProducts}
                onProductSelect={(product) => {
                  setSelectedProduct(product);
                  setIsProductCardOpen(true);
                }}
              />
            </Box>
          </Stack>
        )}
      </Container>

      {/* Product Detail Modal */}
      {selectedProduct && (
        <ProductCard
          product={selectedProduct}
          isOpen={isProductCardOpen}
          onClose={() => setIsProductCardOpen(false)}
          onAddToCart={handleAddToCart}
        />
      )}

      <CartModal
        isOpen={isCartModalOpen}
        onClose={() => setIsCartModalOpen(false)}
        cartItems={cartItems}
        onRemoveItem={handleRemoveFromCart}
        onUpdateQuantity={handleUpdateQuantity}
        onCheckout={() => {
          if (cartItems.length === 0) {
            toast({
              title: 'Winkelwagen is leeg',
              description: 'Voeg eerst producten toe aan uw winkelwagen.',
              status: 'warning',
              duration: 3000,
            });
            return;
          }
          setIsCartModalOpen(false);
          setIsCheckoutModalOpen(true);
        }}
        onSaveCart={handleSaveCart}
        onClearCart={handleClearCart}
      />

      <CheckoutModal
        isOpen={isCheckoutModalOpen}
        onClose={() => setIsCheckoutModalOpen(false)}
        cartItems={cartItems}
        userEmail={user?.attributes?.email || memberInfo?.email || ''}
        onPaymentSuccess={async (paymentData) => {
          try {
            // Calculate totals
            const totalAmount = cartItems.reduce((sum, item) => sum + (Number(item.price || 0) * item.quantity), 0);
            
            const orderId = `ORDER_${Date.now()}`;
            console.log('Creating order with memberInfo:', memberInfo);
            console.log('Current member ID:', currentMemberId);
            
            const orderData = {
              order_id: currentMemberId || memberInfo?.member_id,
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
              delivery_cost: paymentData.deliveryOption ? parseFloat(paymentData.deliveryOption.cost || 0).toFixed(2) : '0.00',
              delivery_option: paymentData.deliveryOption || null,
              items: cartItems.map(item => ({
                name: item.name || item.naam,
                price: Number(item.price || 0).toFixed(2),
                product_id: item.product_id || item.id,
                quantity: item.quantity,
                selectedOption: item.selectedOption || ''
              })),
              item_count: cartItems.reduce((sum, item) => sum + item.quantity, 0),
              orderId: orderId,
              payment_method_id: paymentData.paymentMethodId,
              subtotal_amount: totalAmount.toFixed(2),
              timestamp: new Date().toISOString(),
              total_amount: paymentData.amount.toFixed(2)
            };
            
            // Save order to backend
            try {
              await orderService.createOrder(orderData);
              console.log('Order saved successfully:', orderId);
            console.log('Order data with member info:', orderData);
            } catch (error) {
              console.error('Backend order failed:', error);
              // Fallback to local storage
              const localOrders = JSON.parse(localStorage.getItem('hdcn_orders') || '[]');
              localOrders.push(orderData);
              localStorage.setItem('hdcn_orders', JSON.stringify(localOrders));
            }
            
            // Store order data for OrderConfirmation component
            localStorage.setItem('latest_order', JSON.stringify(orderData));
            
            // Clear cart completely
            setCartItems([]);
            localStorage.removeItem('hdcn_cart_items');
            
            // Clear backend cart
            if (cartId) {
              try {
                await cartService.clearCart(cartId);
                localStorage.removeItem('hdcn_cart_id');
                setCartId(null);
                // Initialize new cart
                await initializeCart();
              } catch (error) {
                console.error('Failed to clear backend cart:', error);
              }
            }
            
            toast({
              title: 'Betaling succesvol!',
              description: `Bestelling ${orderId} van €${paymentData.amount.toFixed(2)} verwerkt`,
              status: 'success',
              duration: 5000,
            });
            
            // Show order success modal
            setIsCheckoutModalOpen(false);
            setShowOrderSuccess(true);
          } catch (error) {
            toast({
              title: 'Fout bij verwerken bestelling',
              description: 'Er is een probleem opgetreden.',
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
  );
}

export default WebshopPage;