import { useEffect, useState } from 'react';
import { Box, Button, HStack, Text, VStack, Alert, AlertIcon, AlertTitle, AlertDescription, Heading } from '@chakra-ui/react';
import { scanProducts } from '../products/api/productApi';
import { Product } from '../../types';
import { FunctionGuard } from '../../components/common/FunctionGuard';
import { getUserRoles } from '../../utils/functionPermissions';

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

interface AdvancedExportsPageProps {
  user: User;
}

export default function AdvancedExportsPage({ user }: AdvancedExportsPageProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  // Enhanced role-based access checks
  const userRoles = getUserRoles(user);
  const hasAdvancedAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Products_CRUD_All' ||
    role === 'Webmaster' ||
    role === 'Webshop_Management'
  );

  useEffect(() => {
    if (hasAdvancedAccess) {
      setLoading(true);
      scanProducts()
        .then(res => {
          setProducts(res.data || []);
        })
        .catch((error: any) => {
          console.error('Error loading products:', error);
          setProducts([]);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [hasAdvancedAccess]);

  const handleBulkProductOperations = () => {
    const activeProducts = products.filter(p => (p.price || p.prijs) > 0);
    
    // Create CSV export
    const csvHeaders = ['ID', 'Naam', 'Groep', 'Subgroep', 'Prijs', 'Opties'];
    const csvData = activeProducts.map(p => [
      p.id,
      p.naam || p.name,
      p.groep || p.category,
      p.subgroep || '',
      p.prijs || p.price,
      Array.isArray(p.opties) ? p.opties.join(';') : p.opties || ''
    ]);
    
    const csvContent = [csvHeaders, ...csvData]
      .map(row => row.map(field => `"${field}"`).join(','))
      .join('\n');
    
    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `producten_export_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    alert(`📦 ${activeProducts.length} actieve producten geëxporteerd naar CSV`);
  };

  const handleInventoryManagement = () => {
    // Create inventory report
    const inventoryData = products.map(p => ({
      id: p.id,
      naam: p.naam || p.name,
      groep: p.groep || p.category,
      subgroep: p.subgroep || '',
      prijs: p.prijs || p.price,
      status: (p.prijs || p.price) > 0 ? 'Actief' : 'Inactief'
    }));
    
    const jsonContent = JSON.stringify(inventoryData, null, 2);
    
    // Download JSON
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `voorraad_rapport_${new Date().toISOString().split('T')[0]}.json`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    alert('📊 Voorraad rapport gedownload');
  };

  const handleProductAnalytics = () => {
    const productStats = {
      totaal: products.length,
      actief: products.filter(p => (p.prijs || p.price) > 0).length,
      inactief: products.filter(p => (p.prijs || p.price) <= 0).length,
      categorieën: [...new Set(products.map(p => p.groep || p.category))].filter(Boolean).length,
      gemiddeldePrijs: products.length > 0 
        ? products.reduce((sum, p) => sum + (parseFloat(String(p.prijs || p.price)) || 0), 0) / products.length 
        : 0,
      hoogstePrijs: Math.max(...products.map(p => parseFloat(String(p.prijs || p.price)) || 0)),
      laagstePrijs: Math.min(...products.filter(p => (p.prijs || p.price) > 0).map(p => parseFloat(String(p.prijs || p.price)) || 0)),
      categorieVerdeling: products.reduce((acc, p) => {
        const cat = p.groep || p.category || 'Onbekend';
        acc[cat] = (acc[cat] || 0) + 1;
        return acc;
      }, {} as Record<string, number>)
    };
    
    const analyticsContent = JSON.stringify(productStats, null, 2);
    
    // Download analytics
    const blob = new Blob([analyticsContent], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `product_analytics_${new Date().toISOString().split('T')[0]}.json`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show summary
    alert(`📈 Product Analytics:\n` +
          `Totaal: ${productStats.totaal}\n` +
          `Actief: ${productStats.actief}\n` +
          `Inactief: ${productStats.inactief}\n` +
          `Categorieën: ${productStats.categorieën}\n` +
          `Gemiddelde prijs: €${productStats.gemiddeldePrijs.toFixed(2)}\n` +
          `Hoogste prijs: €${productStats.hoogstePrijs.toFixed(2)}\n` +
          `Laagste prijs: €${productStats.laagstePrijs.toFixed(2)}\n\n` +
          `Gedetailleerd rapport gedownload.`);
  };

  return (
    <>
      <FunctionGuard 
        user={user} 
        functionName="advanced-exports" 
        action="read"
        requiredRoles={['Products_CRUD_All', 'Webmaster', 'Webshop_Management', 'hdcnAdmins']}
        fallback={
          <Alert status="warning" mt={4}>
            <AlertIcon />
            <Box>
              <AlertTitle>Geen toegang!</AlertTitle>
              <AlertDescription>
                U heeft geen toegang tot de geavanceerde export module. Deze module is alleen beschikbaar voor gebruikers met Products_CRUD_All, Webshop_Management, Webmaster of hdcnAdmins rechten.
                <br /><br />
                <strong>Vereiste rollen:</strong> Products_CRUD_All, Webshop_Management, Webmaster, of hdcnAdmins
              </AlertDescription>
            </Box>
          </Alert>
        }
      >
        <Box p={6} bg="black" minH="100vh">
          <VStack spacing={6} align="stretch">
            <Heading color="orange.400">Export gegevens</Heading>

            {loading && (
              <Alert status="info">
                <AlertIcon />
                Gegevens laden...
              </Alert>
            )}

            {/* Leden Section */}
            <Box bg="gray.800" p={6} borderRadius="md" border="1px" borderColor="blue.400">
              <Text color="blue.400" fontWeight="bold" mb={4} fontSize="lg">
                👥 Leden
              </Text>
              <Text color="gray.300" mb={4}>
                Export van ledengegevens en lidmaatschappen
              </Text>
              <HStack spacing={4} wrap="wrap">
                <Button
                  size="md"
                  colorScheme="blue"
                  isDisabled={true}
                >
                  📊 Basisgegevens Leden (Binnenkort beschikbaar)
                </Button>
              </HStack>
            </Box>

            {/* Producten Section */}
            <Box bg="gray.800" p={6} borderRadius="md" border="1px" borderColor="green.400">
              <Text color="green.400" fontWeight="bold" mb={4} fontSize="lg">
                🛍️ Producten
              </Text>
              <Text color="gray.300" mb={4}>
                Export van productgegevens en voorraad
              </Text>
              <HStack spacing={4} wrap="wrap">
                <Button
                  size="md"
                  colorScheme="green"
                  onClick={handleBulkProductOperations}
                  isDisabled={loading || products.length === 0}
                >
                  📦 Basisgegevens Producten (CSV)
                </Button>
                <Button
                  size="md"
                  colorScheme="blue"
                  onClick={handleInventoryManagement}
                  isDisabled={loading || products.length === 0}
                >
                  📊 Voorraad Rapport (JSON)
                </Button>
                <Button
                  size="md"
                  colorScheme="purple"
                  onClick={handleProductAnalytics}
                  isDisabled={loading || products.length === 0}
                >
                  📈 Product Analytics
                </Button>
              </HStack>
            </Box>

            {/* Orders Section */}
            <Box bg="gray.800" p={6} borderRadius="md" border="1px" borderColor="orange.400">
              <Text color="orange.400" fontWeight="bold" mb={4} fontSize="lg">
                📋 Orders
              </Text>
              <Text color="gray.300" mb={4}>
                Export van bestellingen en transacties
              </Text>
              <HStack spacing={4} wrap="wrap">
                <Button
                  size="md"
                  colorScheme="orange"
                  isDisabled={true}
                >
                  📊 Basisgegevens Orders (Binnenkort beschikbaar)
                </Button>
              </HStack>
            </Box>
          </VStack>
        </Box>
      </FunctionGuard>
    </>
  );
}