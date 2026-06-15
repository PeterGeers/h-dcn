import { useEffect, useState, useRef } from 'react';
import { scanProducts, updateProduct, deleteProduct, insertProduct, softDeleteProduct, hardDeleteProduct } from './api/productApi';
import ProductTable from './components/ProductTable';
import ProductCard from './components/ProductCard';
import ProductFilter from './components/ProductFilter';
import { Product } from '../../types';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { getUserRoles } from '../../utils/functionPermissions';
import { useTranslation } from 'react-i18next';

import {
  Button, Box, HStack, Stack, Alert, AlertIcon, AlertTitle, AlertDescription,
  Text, VStack, Heading, Switch, FormControl, FormLabel, IconButton, Tooltip,
  useDisclosure, useToast,
  AlertDialog, AlertDialogBody, AlertDialogFooter, AlertDialogHeader,
  AlertDialogContent, AlertDialogOverlay,
} from '@chakra-ui/react';
import { DeleteIcon, NotAllowedIcon, CheckIcon } from '@chakra-ui/icons';

interface FilterOption {
  type: 'group' | 'subgroup';
  value: string;
  group?: string;
}

interface User {
  attributes?: {
    given_name?: string;
    family_name?: string;
    email?: string;
  };
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
    };
  };
}

interface ProductManagementPageProps {
  user: User;
  /** Event filter: "" = all, "webshop" = event_id is null, "<uuid>" = specific event */
  eventFilter?: string;
}

export default function ProductManagementPage({ user, eventFilter }: ProductManagementPageProps) {
  // Use eventFilter to determine which products to display
  const activeFilter = eventFilter ?? '';
  const [products, setProducts] = useState<Product[]>([]);
  const [selected, setSelected] = useState<Product | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const { t } = useTranslation('products');
  const toast = useToast();

  // Alert dialog state for deactivation
  const {
    isOpen: isDeactivateOpen,
    onOpen: onDeactivateOpen,
    onClose: onDeactivateClose,
  } = useDisclosure();

  // Alert dialog state for hard-delete
  const {
    isOpen: isHardDeleteOpen,
    onOpen: onHardDeleteOpen,
    onClose: onHardDeleteClose,
  } = useDisclosure();

  const [actionProduct, setActionProduct] = useState<Product | null>(null);
  const [hasPendingOrders, setHasPendingOrders] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Enhanced role-based access checks for products
  const userRoles = getUserRoles(user);
  const hasProductsFullAccess = userRoles.some(role => 
    role === 'Products_CRUD' ||
    role === 'Webmaster' ||
    role === 'Webshop_Management'
  );

  const hasProductsReadAccess = userRoles.some(role => 
    role === 'Products_Read' ||
    role === 'Products_CRUD' ||
    role === 'Webmaster' ||
    role === 'Webshop_Management' ||
    role === 'hdcnLeden' ||
    role === 'National_Chairman' ||
    role === 'National_Secretary' ||
    role === 'Tour_Commissioner' ||
    role === 'Club_Magazine_Editorial'
  );

  const hasProductsFinancialAccess = userRoles.some(role => 
    role === 'Products_CRUD' ||
    role === 'Products_Read_Financial' ||
    role === 'Webmaster' ||
    role === 'Webshop_Management' ||
    role === 'National_Treasurer' ||
    role.includes('Regional_Treasurer_')
  );

  useEffect(() => {
    scanProducts()
      .then(res => {
        setProducts(res.data || []);
      })
      .catch((error: any) => {
        alert('Fout bij laden producten: ' + (error.response?.data?.error || error.message));
        setProducts([]);
      });
  }, []);

  const handleSave = (data: Product) => {
    // Remove fields that should be managed by the backend
    const { updated_at, created_at, opties, ...cleanData } = data as any;
    
    // Send both Dutch and English field names so the backend writes both.
    // This ensures products with either legacy (prijs/naam) or new (price/name) 
    // field naming in DynamoDB get updated correctly.
    const priceStr = cleanData.prijs ? cleanData.prijs.toString() : (cleanData.price ? cleanData.price.toString() : undefined);
    const nameStr = cleanData.naam || cleanData.name || undefined;
    
    const processedData = {
      ...cleanData,
      prijs: priceStr,
      price: priceStr,
      naam: nameStr,
      name: nameStr,
    };
    
    // Use product_id (unified key) if available, fallback to id
    const productId = data.product_id || data.id;
    if (productId) {
      updateProduct(productId, processedData)
        .then(() => {
          refresh();
          alert('Product opgeslagen ✓');
        })
        .catch((error: any) => {
          alert('Fout bij opslaan product: ' + (error.response?.data?.error || error.message));
        });
    } else {
      insertProduct(processedData)
        .then(() => refresh())
        .catch((error: any) => {
          alert('Fout bij aanmaken product: ' + (error.response?.data?.error || error.message));
        });
    }
  };

  const handleDelete = (id: string) => {
    deleteProduct(id).then(() => refresh());
  };

  const refresh = () => {
    scanProducts().then(res => setProducts(res.data));
    setSelected(null);
  };

  // --- Soft-delete (deactivate) ---
  const handleDeactivateClick = (product: Product) => {
    setActionProduct(product);
    // Check if product may have pending orders (we show a generic warning;
    // a full check would require an API call, but for UX we show based on status)
    setHasPendingOrders(false); // Default - can be enhanced with API check
    onDeactivateOpen();
  };

  const handleDeactivateConfirm = async () => {
    if (!actionProduct) return;
    const productId = actionProduct.product_id || actionProduct.id || '';
    const result = await softDeleteProduct(productId);
    if (result.success) {
      toast({
        title: t('management.deactivate'),
        description: result.data?.message || `Product ${productId} deactivated`,
        status: 'success',
        duration: 3000,
      });
      refresh();
    } else {
      toast({
        title: 'Error',
        description: result.error || 'Failed to deactivate product',
        status: 'error',
        duration: 5000,
      });
    }
    onDeactivateClose();
    setActionProduct(null);
  };

  // --- Reactivate (set active=true) ---
  const handleActivate = async (product: Product) => {
    const productId = product.product_id || product.id || '';
    const result = await updateProduct(productId, { active: true } as any);
    if (result.success) {
      toast({
        title: t('management.activate'),
        status: 'success',
        duration: 3000,
      });
      refresh();
    } else {
      toast({
        title: 'Error',
        description: result.error || 'Failed to activate product',
        status: 'error',
        duration: 5000,
      });
    }
  };

  // --- Hard-delete ---
  const handleHardDeleteClick = (product: Product) => {
    setActionProduct(product);
    onHardDeleteOpen();
  };

  const handleHardDeleteConfirm = async () => {
    if (!actionProduct) return;
    const productId = actionProduct.product_id || actionProduct.id || '';
    const result = await hardDeleteProduct(productId);
    if (result.success) {
      toast({
        title: t('management.hard_delete'),
        description: result.data?.message || `Product ${productId} permanently deleted`,
        status: 'success',
        duration: 3000,
      });
      refresh();
    } else {
      // Check for ProductHasOrderHistory error
      const errorMsg = result.data?.error || result.error || '';
      if (errorMsg.includes('order history') || errorMsg.includes('ProductHasOrderHistory')) {
        toast({
          title: 'Error',
          description: t('management.hard_delete_error_has_orders'),
          status: 'error',
          duration: 5000,
        });
      } else {
        toast({
          title: 'Error',
          description: errorMsg || 'Failed to delete product',
          status: 'error',
          duration: 5000,
        });
      }
    }
    onHardDeleteClose();
    setActionProduct(null);
  };

  const [selectedFilter, setSelectedFilter] = useState<FilterOption | null>(null);
  const filteredProducts = products.filter((p: Product) => {
    // Apply active/inactive filter (default: show only active)
    if (!showInactive && p.active === false) return false;

    // Apply event_id filter based on the active event filter
    if (activeFilter === 'webshop') {
      // Show only products where event_id is null (generic webshop products)
      if ((p as any).event_id != null) return false;
    } else if (activeFilter && activeFilter !== '') {
      // Show only products linked to a specific event_id
      if ((p as any).event_id !== activeFilter) return false;
    }
    // When activeFilter is "" (Alle), show all products — no event_id filtering

    // Apply group/subgroup filter
    if (!selectedFilter) return true;
    if (selectedFilter.type === 'group') {
      return p.groep === selectedFilter.value;
    }
    if (selectedFilter.type === 'subgroup') {
      return p.groep === selectedFilter.group && p.subgroep === selectedFilter.value;
    }
    return true;
  });

  return (
    <>
      <Box p={6} bg="black" minH="100vh">
        <VStack spacing={6} align="stretch">
          <Heading color="orange.400">{t('management.title')}</Heading>

      {/* Active/Inactive filter toggle */}
      <FormControl display="flex" alignItems="center">
        <FormLabel htmlFor="show-inactive-toggle" mb="0" color="gray.300" fontSize="sm">
          {t('management.show_inactive')}
        </FormLabel>
        <Switch
          id="show-inactive-toggle"
          colorScheme="orange"
          isChecked={showInactive}
          onChange={(e) => setShowInactive(e.target.checked)}
        />
      </FormControl>
      
      {/* Check if user has read access to products */}
      <FunctionGuard 
        user={user} 
        functionName="products" 
        action="read"
        requiredRoles={['Products_Read', 'Products_CRUD', 'Webshop_Management', 'System_User_Management', 'hdcnLeden']}
        fallback={
          <Alert status="warning" mt={4}>
            <AlertIcon />
            <Box>
              <AlertTitle>Geen toegang!</AlertTitle>
              <AlertDescription>
                U heeft geen toegang tot de productbeheer module. Neem contact op met de beheerder als u denkt dat dit een fout is.
                <br /><br />
                <strong>Vereiste rollen:</strong> Products_Read, Products_CRUD, Webshop_Management, System_User_Management, of hdcnLeden (voor catalogus)
              </AlertDescription>
            </Box>
          </Alert>
        }
      >
        {/* Enhanced functionality for different admin roles */}
        {(hasProductsFinancialAccess && !hasProductsFullAccess) && (
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="yellow.400" mb={4}>
            <Text color="yellow.400" fontWeight="bold" mb={3}>
              💰 Product Financiën & Rapportage
            </Text>
            <HStack spacing={4} wrap="wrap">
              <Button
                size="sm"
                colorScheme="yellow"
                onClick={() => {
                  // Financial product overview
                  const financialOverview = products.map(p => ({
                    naam: p.naam || p.name,
                    prijs: p.prijs || p.price,
                    categorie: p.groep
                  }));
                  console.log('💰 Financieel overzicht:', financialOverview);
                }}
              >
                💰 Financieel Overzicht
              </Button>
              <Button
                size="sm"
                colorScheme="orange"
                onClick={() => {
                  // Price analysis
                  console.log('📊 Prijsanalyse functionaliteit');
                }}
              >
                📊 Prijsanalyse
              </Button>
            </HStack>
          </Box>
        )}

        {(hasProductsReadAccess && !hasProductsFullAccess && !hasProductsFinancialAccess) && (
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="blue.400" mb={4}>
            <Text color="blue.400" fontWeight="bold" mb={3}>
              👀 Product Catalogus (Alleen Lezen)
            </Text>
            <HStack spacing={4} wrap="wrap">
              <Button
                size="sm"
                colorScheme="blue"
                onClick={() => {
                  // Product catalog view
                  const catalogView = products.map(p => ({
                    naam: p.naam || p.name,
                    categorie: p.groep,
                    beschikbaar: true
                  }));
                  console.log('📋 Catalogus overzicht:', catalogView);
                }}
              >
                📋 Catalogus Overzicht
              </Button>
              <Button
                size="sm"
                colorScheme="teal"
                onClick={() => {
                  // Product search functionality
                  console.log('🔍 Product zoek functionaliteit');
                }}
              >
                🔍 Product Zoeken
              </Button>
            </HStack>
          </Box>
        )}

        <Stack direction={{ base: 'column', lg: 'row' }} align="start" spacing={6}>
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
              onSelect={setSelected}
              showStatusColumn={hasProductsFullAccess}
              renderActions={hasProductsFullAccess ? (product: Product) => (
                <HStack spacing={1}>
                  {product.active !== false ? (
                    <Tooltip label={t('management.deactivate')}>
                      <IconButton
                        aria-label={t('management.deactivate')}
                        icon={<NotAllowedIcon />}
                        size="xs"
                        colorScheme="yellow"
                        variant="ghost"
                        onClick={() => handleDeactivateClick(product)}
                      />
                    </Tooltip>
                  ) : (
                    <Tooltip label={t('management.activate')}>
                      <IconButton
                        aria-label={t('management.activate')}
                        icon={<CheckIcon />}
                        size="xs"
                        colorScheme="green"
                        variant="ghost"
                        onClick={() => handleActivate(product)}
                      />
                    </Tooltip>
                  )}
                  <Tooltip label={t('management.hard_delete')}>
                    <IconButton
                      aria-label={t('management.hard_delete')}
                      icon={<DeleteIcon />}
                      size="xs"
                      colorScheme="red"
                      variant="ghost"
                      onClick={() => handleHardDeleteClick(product)}
                    />
                  </Tooltip>
                </HStack>
              ) : undefined}
            />
          </Box>
        </Stack>
        
        {/* Product editing modal - only show if user has write access */}
        {selected && (
          <FunctionGuard 
            user={user} 
            functionName="products" 
            action="write"
            requiredRoles={['Products_CRUD', 'Webshop_Management', 'System_User_Management']}
            fallback={
              <ProductCard
                key={selected.id}
                product={selected}
                products={products}
                filteredProducts={filteredProducts}
                onSave={() => {}} // Disabled save function
                onDelete={() => {}} // Disabled delete function
                onNew={() => {}} // Disabled new function
                onClose={() => setSelected(null)}
                onNavigate={setSelected}
                readOnly={true} // Add read-only mode
              />
            }
          >
            <ProductCard
              key={selected.id}
              product={selected}
              products={products}
              filteredProducts={filteredProducts}
              onSave={handleSave}
              onDelete={handleDelete}
              onNew={() => setSelected({ product_id: '', id: '', name: '', naam: '', price: 0, category: '', groep: '', subgroep: '' })}
              onClose={() => setSelected(null)}
              onNavigate={setSelected}
              readOnly={false}
            />
          </FunctionGuard>
        )}
      </FunctionGuard>
        </VStack>
      </Box>

      {/* Deactivate Confirmation Dialog */}
      <AlertDialog
        isOpen={isDeactivateOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeactivateClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {t('management.deactivate_confirm_title')}
            </AlertDialogHeader>

            <AlertDialogBody>
              {t('management.deactivate_confirm_body')}
              {hasPendingOrders && (
                <Alert status="warning" mt={3} borderRadius="md">
                  <AlertIcon />
                  {t('management.deactivate_pending_orders_warning')}
                </Alert>
              )}
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeactivateClose}>
                {t('management.cancel')}
              </Button>
              <Button colorScheme="yellow" onClick={handleDeactivateConfirm} ml={3}>
                {t('management.confirm')}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Hard-Delete Confirmation Dialog */}
      <AlertDialog
        isOpen={isHardDeleteOpen}
        leastDestructiveRef={cancelRef}
        onClose={onHardDeleteClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {t('management.hard_delete_confirm_title')}
            </AlertDialogHeader>

            <AlertDialogBody>
              {t('management.hard_delete_confirm_body')}
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onHardDeleteClose}>
                {t('management.cancel')}
              </Button>
              <Button colorScheme="red" onClick={handleHardDeleteConfirm} ml={3}>
                {t('management.confirm')}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
}
