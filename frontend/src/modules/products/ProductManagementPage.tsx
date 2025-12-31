import { useEffect, useState } from 'react';
import { scanProducts, updateProduct, deleteProduct, insertProduct } from './api/productApi';
import ProductTable from './components/ProductTable';
import ProductCard from './components/ProductCard';
import ProductFilter from './components/ProductFilter';
import Header from './components/Header';
import { Product } from '../../types';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { getUserRoles } from '../../utils/functionPermissions';

import { Button, Box, HStack, Stack, Alert, AlertIcon, AlertTitle, AlertDescription, Text } from '@chakra-ui/react';

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
}

export default function ProductManagementPage({ user }: ProductManagementPageProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [selected, setSelected] = useState<Product | null>(null);

  // Enhanced role-based access checks for products
  const userRoles = getUserRoles(user);
  const hasProductsFullAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Products_CRUD_All' ||
    role === 'Webmaster' ||
    role === 'Webshop_Management'
  );

  const hasProductsReadAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Products_Read_All' ||
    role === 'Products_CRUD_All' ||
    role === 'Webmaster' ||
    role === 'Webshop_Management' ||
    role === 'hdcnLeden' ||
    role === 'National_Chairman' ||
    role === 'National_Secretary' ||
    role === 'Tour_Commissioner' ||
    role === 'Club_Magazine_Editorial'
  );

  const hasProductsFinancialAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Products_CRUD_All' ||
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
    const { updated_at, created_at, ...cleanData } = data as any;
    
    const processedData = {
      ...cleanData,
      prijs: cleanData.prijs ? cleanData.prijs.toString() : cleanData.prijs
    };
    
    if (data.id) {
      updateProduct(data.id, processedData)
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
      <Header />
      
      {/* Check if user has read access to products */}
      <FunctionGuard 
        user={user} 
        functionName="products" 
        action="read"
        requiredRoles={['Products_Read_All', 'Products_CRUD_All', 'Webmaster', 'Webshop_Management', 'hdcnLeden']}
        fallback={
          <Alert status="warning" mt={4}>
            <AlertIcon />
            <Box>
              <AlertTitle>Geen toegang!</AlertTitle>
              <AlertDescription>
                U heeft geen toegang tot de productbeheer module. Neem contact op met de beheerder als u denkt dat dit een fout is.
                <br /><br />
                <strong>Vereiste rollen:</strong> Products_Read_All, Products_CRUD_All, Webmaster, Webshop_Management, of hdcnLeden (voor catalogus)
              </AlertDescription>
            </Box>
          </Alert>
        }
      >
        {/* Enhanced functionality for different admin roles */}
        {hasProductsFullAccess && (
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="green.400" mb={4}>
            <Text color="green.400" fontWeight="bold" mb={3}>
              🛍️ Geavanceerd Productbeheer (Products_CRUD_All / Webshop_Management)
            </Text>
            <HStack spacing={4} wrap="wrap">
              <Button
                size="sm"
                colorScheme="green"
                onClick={() => {
                  // Bulk product operations
                  const activeProducts = products.filter(p => p.price > 0);
                  alert(`🛍️ ${activeProducts.length} actieve producten gevonden`);
                }}
              >
                📦 Bulk Product Beheer
              </Button>
              <Button
                size="sm"
                colorScheme="blue"
                onClick={() => {
                  // Inventory management
                  alert('📊 Voorraad beheer functionaliteit - nog niet geïmplementeerd');
                }}
              >
                📊 Voorraad Beheer
              </Button>
              <Button
                size="sm"
                colorScheme="purple"
                onClick={() => {
                  // Product analytics
                  const productStats = {
                    totaal: products.length,
                    categorieën: [...new Set(products.map(p => p.groep))].length,
                    gemiddeldePrijs: products.reduce((sum, p) => sum + (p.price || 0), 0) / products.length
                  };
                  alert(`📈 Product statistieken:\nTotaal: ${productStats.totaal}\nCategorieën: ${productStats.categorieën}\nGemiddelde prijs: €${productStats.gemiddeldePrijs.toFixed(2)}`);
                }}
              >
                📈 Product Analytics
              </Button>
            </HStack>
          </Box>
        )}

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
            requiredRoles={['Products_CRUD_All', 'Webmaster', 'Webshop_Management']}
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
              onNew={() => setSelected({ id: '', name: '', naam: '', price: 0, category: '', groep: '', subgroep: '', opties: [] })}
              onClose={() => setSelected(null)}
              onNavigate={setSelected}
              readOnly={false}
            />
          </FunctionGuard>
        )}
      </FunctionGuard>
    </>
  );
}
