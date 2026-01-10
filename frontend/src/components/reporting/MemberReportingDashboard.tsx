/**
 * Member Reporting Dashboard - Main reporting interface
 * 
 * Provides comprehensive reporting capabilities for H-DCN member data
 * Now uses ParquetDataService for self-contained data loading
 */

import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Alert,
  AlertIcon,
  Button,
  useToast,
  Spinner,
  Badge,
  Flex
} from '@chakra-ui/react';
import { HDCNGroup } from '../../config/memberFields';
import { getAuthHeaders } from '../../utils/authHeaders';
import { API_CONFIG } from '../../config/api';
import { useLatestParquetData } from '../../hooks/useParquetData';
import AddressLabelsSection from './AddressLabelsSection';
import AnalyticsSection from './AnalyticsSection';

interface MemberReportingDashboardProps {
  userRole: HDCNGroup;
  userRegion?: string;
}

const MemberReportingDashboard: React.FC<MemberReportingDashboardProps> = ({
  userRole,
  userRegion
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const toast = useToast();

  // Use ParquetDataService for self-contained data loading
  const {
    data: members,
    loading,
    error: dataError,
    metadata,
    fileStatus,
    refreshData,
    retry,
    hasPermission,
    isDataAvailable,
    lastLoadTime,
    retryCount
  } = useLatestParquetData({
    applyCalculatedFields: true,
    applyRegionalFiltering: true,
    enableCaching: true,
    retryOnError: true,
    maxRetries: 3
  });

  // Check if user has reporting access
  const hasReportingAccess = ['System_User_Management', 'Members_CRUD', 'Members_Read', 'System_User_Management'].includes(userRole);
  
  // Check if user can generate parquet files (Members_CRUD or System_User_Management only)
  const canGenerateParquet = ['Members_CRUD', 'System_User_Management'].includes(userRole);

  const handleGenerateParquet = async () => {
    if (!canGenerateParquet) {
      toast({
        title: 'Geen toegang',
        description: 'Alleen Members_CRUD en System_User_Management gebruikers kunnen Parquet bestanden genereren.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      return;
    }

    setIsGenerating(true);
    
    try {
      const headers = await getAuthHeaders();
      
      // Call the Lambda function via API Gateway
      const response = await fetch(`${API_CONFIG.BASE_URL}/analytics/generate-parquet`, {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          options: {
            // Add any options here if needed
          }
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      toast({
        title: '✅ Parquet bestand gegenereerd!',
        description: `Bestand opgeslagen: ${result.data?.s3_key || 'Onbekende locatie'}`,
        status: 'success',
        duration: 8000,
        isClosable: true,
      });

      console.log('Parquet generation result:', result);
      
      // Refresh data after successful generation
      if (refreshData) {
        await refreshData();
      }
      
    } catch (error) {
      console.error('Error generating parquet:', error);
      
      toast({
        title: '❌ Fout bij genereren',
        description: `Kon Parquet bestand niet genereren: ${error instanceof Error ? error.message : 'Onbekende fout'}`,
        status: 'error',
        duration: 8000,
        isClosable: true,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  if (!hasReportingAccess) {
    return (
      <Box p={6}>
        <Alert status="warning">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold">Geen toegang tot rapportages</Text>
            <Text fontSize="sm">
              U heeft geen toegang tot de rapportagefuncties. Neem contact op met een beheerder.
            </Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // Show permission error if user doesn't have parquet data access
  if (!hasPermission && dataError) {
    return (
      <Box p={6}>
        <Alert status="error">
          <AlertIcon />
          <VStack align="start" spacing={2}>
            <Text fontWeight="semibold">Geen toegang tot rapportagegegevens</Text>
            <Text fontSize="sm">{dataError}</Text>
            <Button size="sm" colorScheme="red" variant="outline" onClick={retry}>
              Opnieuw proberen
            </Button>
          </VStack>
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <VStack spacing={2} align="start">
          <Flex justify="space-between" align="center" w="full">
            <Heading color="orange.500" size="lg">
              📊 Rapportages
            </Heading>
            <HStack spacing={2}>
              {/* Data freshness indicator */}
              {lastLoadTime && (
                <Badge colorScheme="green" fontSize="xs">
                  Laatste update: {new Date(lastLoadTime).toLocaleTimeString('nl-NL')}
                </Badge>
              )}
              {metadata && (
                <Badge colorScheme="blue" fontSize="xs">
                  {metadata.recordCount} records
                </Badge>
              )}
              {metadata?.fromCache && (
                <Badge colorScheme="purple" fontSize="xs">
                  Gecached
                </Badge>
              )}
              {retryCount > 0 && (
                <Badge colorScheme="yellow" fontSize="xs">
                  Retry {retryCount}
                </Badge>
              )}
            </HStack>
          </Flex>
          <Text color="gray.300" fontSize="sm">
            Uitgebreide rapportage- en exportfuncties voor ledengegevens
          </Text>
          {/* Loading indicator */}
          {loading && (
            <HStack spacing={2}>
              <Spinner size="sm" color="orange.500" />
              <Text color="gray.400" fontSize="sm">
                Laden van parquet data...
              </Text>
            </HStack>
          )}
          {/* Error indicator */}
          {dataError && !loading && (
            <Alert status="error" size="sm">
              <AlertIcon />
              <Text fontSize="sm">{dataError}</Text>
              <Button size="xs" ml={2} onClick={retry}>
                Retry
              </Button>
            </Alert>
          )}
        </VStack>

        {/* Address Labels Section */}
        <AddressLabelsSection
          members={members || []}
          userRole={userRole}
          userRegion={userRegion}
        />

        {/* Analytics Section */}
        <AnalyticsSection
          members={members || []}
          loading={loading}
          error={dataError}
          userRegion={userRegion}
          onRefreshData={refreshData}
        />

        {/* Test Section for Parquet Generation */}
        {canGenerateParquet && (
          <Box 
            bg="gray.800" 
            borderColor="green.400" 
            border="1px" 
            borderRadius="lg"
            p={6}
          >
            <VStack spacing={4} align="start">
              <Heading color="green.300" size="md">
                🧪 Test: Parquet Generatie
              </Heading>
              <Text color="gray.300" fontSize="sm">
                Test de nieuwe Parquet generatie functionaliteit. Dit genereert een Parquet bestand 
                met alle ledengegevens voor analytics doeleinden.
              </Text>
              <HStack spacing={4}>
                <Button
                  colorScheme="green"
                  onClick={handleGenerateParquet}
                  isLoading={isGenerating}
                  loadingText="Genereren..."
                  leftIcon={isGenerating ? <Spinner size="sm" /> : undefined}
                  size="sm"
                >
                  📊 Genereer Parquet Bestand
                </Button>
                <Text color="gray.400" fontSize="xs">
                  Vereist: Members_CRUD of System_User_Management rol
                </Text>
              </HStack>
            </VStack>
          </Box>
        )}

        {/* Placeholder content - will be replaced with more reporting features */}
        <Box 
          bg="gray.800" 
          borderColor="orange.400" 
          border="1px" 
          borderRadius="lg"
          p={8}
          textAlign="center"
        >
          <VStack spacing={4}>
            <Text color="orange.300" fontSize="xl" fontWeight="semibold">
              🚧 Meer functies in ontwikkeling
            </Text>
            <Text color="gray.300">
              Aanvullende rapportagefuncties zoals analytics, AI-rapporten en certificaten worden binnenkort toegevoegd.
            </Text>
            <Text color="gray.400" fontSize="sm">
              Gebruikersrol: {userRole}
              {userRegion && ` | Regio: ${userRegion}`}
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
};

export default MemberReportingDashboard;