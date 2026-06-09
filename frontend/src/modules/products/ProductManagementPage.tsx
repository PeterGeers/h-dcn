import { useEffect, useState } from 'react';
import { scanProducts, updateProduct, deleteProduct, insertProduct } from './api/productApi';
import ProductTable from './components/ProductTable';
import ProductCard from './components/ProductCard';
import ProductFilter from './components/ProductFilter';
import { Product } from '../../types';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { getUserRoles } from '../../utils/functionPermissions';

import { Button, Box, HStack, Stack, Alert, AlertIcon, AlertTitle, AlertDescription, Text, VStack, Heading } from '@chakra-ui/react';

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
    
    const processedData = {
      ...cleanData,
      prijs: cleanData.prijs ? cleanData.prijs.toString() : cleanData.prijs
    };
    
    // Use product_id (unified key) if available, fallback to id
    const productId = data.product_id || data.id;
    if (productId) {
      updateProduct(productId, processedData)
        .then(() => refresh())
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

  const [selectedFilter, setSelectedFilter] = useState<FilterOption | null>(null);
  const filteredProducts = products.filter((p: Product) => {
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
          <Heading color="orange.400">Product Management</Heading>
      
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
    </>
  );
}
