/**
 * Web Worker Example Component
 * 
 * This component demonstrates how to use Web Workers for background
 * data processing in the member reporting system.
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Progress,
  Alert,
  AlertIcon,
  Code,
  Divider,
  useToast
} from '@chakra-ui/react';
import { useWebWorkers } from '../../hooks/useWebWorkers';
import { WebWorkerStatus } from '../common/WebWorkerStatus';

// ============================================================================
// COMPONENT
// ============================================================================

export const WebWorkerExample: React.FC = () => {
  const {
    isAvailable,
    isProcessing,
    currentTask,
    processData,
    applyCalculatedFields,
    applyRegionalFilter,
    clearTask
  } = useWebWorkers();

  const [results, setResults] = useState<any>(null);
  const toast = useToast();

  // Sample data for testing
  const sampleData = [
    {
      id: '1',
      voornaam: 'John',
      tussenvoegsel: 'van',
      achternaam: 'Doe',
      geboortedatum: '1990-01-15',
      ingangsdatum: '2020-03-01',
      regio: 'Noord-Holland',
      status: 'Actief'
    },
    {
      id: '2',
      voornaam: 'Jane',
      achternaam: 'Smith',
      geboortedatum: '1985-07-22',
      ingangsdatum: '2018-06-15',
      regio: 'Zuid-Holland',
      status: 'Actief'
    },
    {
      id: '3',
      voornaam: 'Bob',
      achternaam: 'Johnson',
      geboortedatum: '1975-12-03',
      ingangsdatum: '2015-09-10',
      regio: 'Noord-Holland',
      status: 'Actief'
    }
  ];

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  const handleCalculatedFields = async () => {
    if (!isAvailable) {
      toast({
        title: 'Web Workers Not Available',
        description: 'Web Workers are not supported in this environment',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    try {
      const result = await applyCalculatedFields(sampleData);
      setResults(result);
      toast({
        title: 'Success',
        description: `Processed ${result.data.length} members with calculated fields`,
        status: 'success',
        duration: 3000
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Processing failed',
        status: 'error',
        duration: 5000
      });
    }
  };

  const handleRegionalFilter = async () => {
    if (!isAvailable) {
      toast({
        title: 'Web Workers Not Available',
        description: 'Web Workers are not supported in this environment',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    try {
      const filterOptions = {
        userRoles: ['hdcnRegio_Noord-Holland'],
        userEmail: 'test@example.com'
      };

      const result = await applyRegionalFilter(sampleData, filterOptions);
      setResults(result);
      toast({
        title: 'Success',
        description: `Filtered to ${result.data.length} members from Noord-Holland`,
        status: 'success',
        duration: 3000
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Filtering failed',
        status: 'error',
        duration: 5000
      });
    }
  };

  const handleCombinedProcessing = async () => {
    if (!isAvailable) {
      toast({
        title: 'Web Workers Not Available',
        description: 'Web Workers are not supported in this environment',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    try {
      const result = await processData(sampleData, {
        applyCalculatedFields: true,
        applyRegionalFiltering: true,
        regionalFilterOptions: {
          userRoles: ['hdcnRegio_Noord-Holland'],
          userEmail: 'test@example.com'
        }
      });
      setResults(result);
      toast({
        title: 'Success',
        description: `Combined processing completed: ${result.data.length} members`,
        status: 'success',
        duration: 3000
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Processing failed',
        status: 'error',
        duration: 5000
      });
    }
  };

  const handleClearResults = () => {
    setResults(null);
    clearTask();
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <Box p={6} maxW="800px" mx="auto">
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Text fontSize="2xl" fontWeight="bold" mb={2}>
            Web Worker Example
          </Text>
          <Text color="gray.600">
            Demonstrates background data processing using Web Workers to prevent UI blocking.
          </Text>
        </Box>

        {/* Web Worker Status */}
        <WebWorkerStatus showDetails />

        {/* Availability Alert */}
        {!isAvailable && (
          <Alert status="warning">
            <AlertIcon />
            Web Workers are not available in this environment. 
            Processing will fall back to the main thread.
          </Alert>
        )}

        {/* Sample Data */}
        <Box>
          <Text fontSize="lg" fontWeight="medium" mb={2}>
            Sample Data ({sampleData.length} members)
          </Text>
          <Code p={3} borderRadius="md" fontSize="sm" whiteSpace="pre-wrap">
            {JSON.stringify(sampleData, null, 2)}
          </Code>
        </Box>

        <Divider />

        {/* Action Buttons */}
        <VStack spacing={4} align="stretch">
          <Text fontSize="lg" fontWeight="medium">
            Web Worker Operations
          </Text>

          <HStack spacing={4} wrap="wrap">
            <Button
              colorScheme="blue"
              onClick={handleCalculatedFields}
              isLoading={isProcessing && currentTask?.type === 'APPLY_CALCULATED_FIELDS'}
              isDisabled={isProcessing}
            >
              Apply Calculated Fields
            </Button>

            <Button
              colorScheme="green"
              onClick={handleRegionalFilter}
              isLoading={isProcessing && currentTask?.type === 'APPLY_REGIONAL_FILTER'}
              isDisabled={isProcessing}
            >
              Apply Regional Filter
            </Button>

            <Button
              colorScheme="purple"
              onClick={handleCombinedProcessing}
              isLoading={isProcessing && currentTask?.type === 'PROCESS_DATA'}
              isDisabled={isProcessing}
            >
              Combined Processing
            </Button>

            <Button
              variant="outline"
              onClick={handleClearResults}
              isDisabled={isProcessing}
            >
              Clear Results
            </Button>
          </HStack>
        </VStack>

        {/* Progress Indicator */}
        {currentTask && isProcessing && (
          <Box>
            <Text fontSize="sm" color="gray.600" mb={2}>
              {currentTask.message || 'Processing...'}
            </Text>
            <Progress
              value={currentTask.progress}
              colorScheme="blue"
              borderRadius="md"
              hasStripe
              isAnimated
            />
            <Text fontSize="xs" color="gray.500" mt={1}>
              {Math.round(currentTask.progress)}% complete
            </Text>
          </Box>
        )}

        {/* Results */}
        {results && (
          <Box>
            <Text fontSize="lg" fontWeight="medium" mb={2}>
              Processing Results
            </Text>
            
            {/* Stats */}
            {results.stats && (
              <Box mb={4} p={3} bg="gray.50" borderRadius="md">
                <Text fontSize="sm" fontWeight="medium" mb={2}>Statistics:</Text>
                <VStack align="start" spacing={1} fontSize="sm">
                  <Text>Total Records: {results.stats.totalRecords}</Text>
                  <Text>Processed Records: {results.stats.processedRecords}</Text>
                  {results.stats.calculatedFieldsComputed > 0 && (
                    <Text>Calculated Fields Applied: {results.stats.calculatedFieldsComputed}</Text>
                  )}
                  {results.stats.regionallyFiltered > 0 && (
                    <Text>Records Filtered: {results.stats.regionallyFiltered}</Text>
                  )}
                  <Text>Processing Time: {results.stats.processingTime}ms</Text>
                </VStack>
              </Box>
            )}

            {/* Data */}
            <Code p={3} borderRadius="md" fontSize="sm" whiteSpace="pre-wrap" maxH="300px" overflowY="auto">
              {JSON.stringify(results.data, null, 2)}
            </Code>
          </Box>
        )}

        {/* Task Completion */}
        {currentTask?.status === 'completed' && (
          <Alert status="success">
            <AlertIcon />
            Task completed successfully!
          </Alert>
        )}

        {/* Task Error */}
        {currentTask?.status === 'error' && (
          <Alert status="error">
            <AlertIcon />
            Task failed: {currentTask.error}
          </Alert>
        )}
      </VStack>
    </Box>
  );
};

export default WebWorkerExample;