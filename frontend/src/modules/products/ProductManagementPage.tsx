import { useEffect, useState, useRef, useMemo } from 'react';
import { scanProducts, updateProduct, deleteProduct, insertProduct, softDeleteProduct, hardDeleteProduct } from './api/productApi';
import ProductTable from './components/ProductTable';
import type { ProductColumnFilters } from './components/ProductTable';
import ProductCard from './components/ProductCard';
import { Product } from '../../types';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { getUserRoles } from '../../utils/functionPermissions';
import { useTranslation } from 'react-i18next';
import { isDeactivated } from '../../utils/productHelpers';
import { FilterPanel, GenericFilter } from '../../components/filters';
import { useFilterableTable } from '../../hooks/useFilterableTable';
import { ApiService } from '../../services/apiService';

import {
  Button, Box, HStack, Stack, Alert, AlertIcon, AlertTitle, AlertDescription,
  Text, VStack, Heading, Switch, FormControl, FormLabel,
  useDisclosure, useToast,
  AlertDialog, AlertDialogBody, AlertDialogFooter, AlertDialogHeader,
  AlertDialogContent, AlertDialogOverlay,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';

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

  // Event-product mapping: events have product_ids[], build reverse lookup
  const [eventProductMap, setEventProductMap] = useState<Record<string, string[]>>({});
  const [eventNames, setEventNames] = useState<Record<string, string>>({});

  useEffect(() => {
    scanProducts()
      .then(res => {
        setProducts(res.data || []);
      })
      .catch((error: any) => {
        alert('Fout bij laden producten: ' + (error.response?.data?.error || error.message));
        setProducts([]);
      });

    // Fetch events to build product → event(s) reverse lookup
    ApiService.get('/events')
      .then((res: any) => {
        const events = res.data || res || [];
        if (!Array.isArray(events)) return;
        const reverseMap: Record<string, string[]> = {};
        const names: Record<string, string> = {};
        events.forEach((evt: any) => {
          const eventId = evt.event_id;
          const eventName = evt.name || evt.event_id;
          if (eventId) names[eventId] = eventName;
          const pids: string[] = evt.product_ids || [];
          pids.forEach((pid: string) => {
            if (!reverseMap[pid]) reverseMap[pid] = [];
            reverseMap[pid].push(eventId);
          });
        });
        setEventProductMap(reverseMap);
        setEventNames(names);
      })
      .catch(() => {
        // Silently fail — source column will just show empty
      });
  }, []);

  const handleSave = (data: Product) => {
    // Remove fields managed by backend or no longer used
    const { updated_at, created_at, opties, ...cleanData } = data as any;
    
    // Use canonical Dutch field names only (per schema-driven.md)
    const processedData = {
      ...cleanData,
      prijs: cleanData.prijs ? cleanData.prijs.toString() : undefined,
      naam: cleanData.naam || undefined,
    };
    // Remove any legacy English field names that may have leaked in
    delete processedData.name;
    delete processedData.price;
    delete processedData.id;
    
    const productId = data.product_id;
    if (productId) {
      updateProduct(productId, processedData)
        .then((response: any) => {
          if (response && response.success === false) {
            const errorDetail = response.data?.errors 
              ? '\n' + JSON.stringify(response.data.errors, null, 2)
              : '';
            alert('Fout bij opslaan: ' + (response.error || 'Onbekende fout') + errorDetail);
            return;
          }
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


  // Source/event filter state (dropdown above table)
  const [sourceFilter, setSourceFilter] = useState<string>(activeFilter);

  // Build event options from the event-product reverse map
  const sourceOptions = useMemo(() => {
    const opts: { value: string; label: string }[] = [];
    // Add each event that has products
    Object.entries(eventNames).forEach(([eventId, name]) => {
      opts.push({ value: eventId, label: name });
    });
    // Sort alphabetically by label
    opts.sort((a, b) => a.label.localeCompare(b.label));
    return opts;
  }, [eventNames]);

  // Prepare data for useFilterableTable: add computed display fields
  const tableData = useMemo(() => {
    let filtered = products;
    // Apply active/inactive filter (default: show only active)
    if (!showInactive) {
      filtered = filtered.filter(p => !isDeactivated(p));
    }
    // Apply source/event filter: only show products that belong to the selected event
    const effectiveFilter = sourceFilter || activeFilter;
    if (effectiveFilter) {
      filtered = filtered.filter(p => {
        const pid = p.product_id || (p as any).id || '';
        const productEvents = eventProductMap[pid] || [];
        return productEvents.includes(effectiveFilter);
      });
    }
    // Map to records with computed display fields for column filtering
    return filtered.map(p => {
      const pid = p.product_id || (p as any).id || '';
      const productEvents = eventProductMap[pid] || [];
      const sourceDisplay = productEvents.length === 0 ? '-'
        : productEvents.map(eid => eventNames[eid] || eid.slice(0, 8)).join(', ');
      return {
        ...p,
        _groepDisplay: `${p.groep || ''} - ${p.subgroep || ''}`,
        _statusDisplay: isDeactivated(p) ? 'inactief' : 'actief',
        _sourceDisplay: sourceDisplay,
      };
    });
  }, [products, showInactive, activeFilter, sourceFilter, eventProductMap, eventNames]);

  const INITIAL_FILTERS = {
    artikelcode: '',
    groep: '',
    naam: '',
    prijs: '',
    status: '',
    source: '',
  };

  // useFilterableTable: column text filters + sort on the pre-filtered data
  const {
    filters,
    setFilter,
    resetFilters,
    hasActiveFilters,
    sortField,
    sortDirection,
    handleSort,
    processedData,
    filteredCount,
  } = useFilterableTable(tableData as unknown as Record<string, unknown>[], {
    initialFilters: INITIAL_FILTERS,
    defaultSort: { field: 'naam', direction: 'asc' },
  });

  // Cast filters to the expected shape for ProductTable
  const columnFilters: ProductColumnFilters = filters as unknown as ProductColumnFilters;

  // Custom filter: override 'groep' filter to match _groepDisplay, 'status' to match _statusDisplay
  const filteredProducts = useMemo(() => {
    let data = processedData as unknown as (Product & { _groepDisplay: string; _statusDisplay: string; _sourceDisplay: string })[];
    // Apply groep filter on the combined _groepDisplay field
    if (columnFilters.groep) {
      const lower = columnFilters.groep.toLowerCase();
      data = data.filter(p => p._groepDisplay.toLowerCase().includes(lower));
    }
    // Apply status filter on the _statusDisplay field
    if (columnFilters.status) {
      const lower = columnFilters.status.toLowerCase();
      data = data.filter(p => p._statusDisplay.toLowerCase().includes(lower));
    }
    // Apply source filter on the _sourceDisplay field
    if (columnFilters.source) {
      const lower = columnFilters.source.toLowerCase();
      data = data.filter(p => p._sourceDisplay.toLowerCase().includes(lower));
    }
    return data;
  }, [processedData, columnFilters.groep, columnFilters.status, columnFilters.source]);

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
                    naam: p.naam,
                    prijs: p.prijs,
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
                    naam: p.naam,
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
          <Box flex={1}>
            <FilterPanel
              hasActiveFilters={hasActiveFilters || !!sourceFilter}
              onReset={() => { resetFilters(); setSourceFilter(''); }}
              filteredCount={filteredCount}
              totalCount={tableData.length}
            >
              <GenericFilter
                label="Bron / Event"
                value={sourceFilter}
                options={sourceOptions}
                onChange={(v) => setSourceFilter(v)}
                placeholder="Alle bronnen"
                width="180px"
              />
              {hasProductsFullAccess && (
                <Button
                  leftIcon={<AddIcon />}
                  colorScheme="green"
                  size="sm"
                  onClick={() => setSelected({ product_id: '', naam: '', prijs: '', groep: '', subgroep: '' })}
                >
                  {t('management.add_product', 'Nieuw product')}
                </Button>
              )}
            </FilterPanel>
            <ProductTable
              products={filteredProducts as Product[]}
              onSelect={setSelected}
              showStatusColumn={hasProductsFullAccess}
              filters={columnFilters}
              onFilterChange={(key, value) => setFilter(key, value)}
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={handleSort}
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
                filteredProducts={filteredProducts as Product[]}
                onSave={() => {}} // Disabled save function
                onDelete={() => {}} // Disabled delete function
                onNew={() => {}} // Disabled new function
                onClose={() => setSelected(null)}
                readOnly={true} // Add read-only mode
              />
            }
          >
            <ProductCard
              key={selected.id}
              product={selected}
              products={products}
              filteredProducts={filteredProducts as Product[]}
              onSave={handleSave}
              onDelete={handleDelete}
              onNew={() => setSelected({ product_id: '', naam: '', prijs: '', groep: '', subgroep: '' })}
              onCopy={(sourceProduct) => {
                const { product_id, id, created_at, updated_at, ...rest } = sourceProduct as any;
                setSelected({
                  ...rest,
                  product_id: '',
                  naam: `${rest.naam || ''} (kopie)`,
                });
              }}
              onClose={() => setSelected(null)}
              readOnly={false}
              onDeactivate={handleDeactivateClick}
              onActivate={handleActivate}
              onHardDelete={handleHardDeleteClick}
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
          <AlertDialogContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
            <AlertDialogHeader fontSize="lg" fontWeight="bold" color="orange.300">
              {t('management.deactivate_confirm_title')}
            </AlertDialogHeader>

            <AlertDialogBody color="white">
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
          <AlertDialogContent bg="gray.800" borderColor="orange.400" borderWidth="1px">
            <AlertDialogHeader fontSize="lg" fontWeight="bold" color="orange.300">
              {t('management.hard_delete_confirm_title')}
            </AlertDialogHeader>

            <AlertDialogBody color="white">
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
