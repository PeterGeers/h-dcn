/**
 * Member Reporting Dashboard - Main reporting interface
 * 
 * Now uses simple JSON export instead of complex parquet files!
 * Much simpler and more reliable.
 */

import React, { useEffect } from 'react';
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
import { useMemberExport } from '../../hooks/useMemberExport';
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
  const toast = useToast();

  // Use simple member export instead of complex parquet files
  const {
    members,
    loading,
    error,
    metadata,
    exportMembers,
    hasPermission,
    checkPermission
  } = useMemberExport();

  // Check permissions on mount
  useEffect(() => {
    checkPermission();
  }, [checkPermission]);

  // Auto-load data if user has permission
  useEffect(() => {
    if (hasPermission === true && !members && !loading) {
      exportMembers();
    }
  }, [hasPermission, members, loading, exportMembers]);

  const handleRefresh = async () => {
    try {
      await exportMembers();
      toast({
        title: 'Data Refreshed',
        description: `Successfully loaded ${members?.length || 0} members`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Refresh Failed',
        description: 'Failed to refresh member data',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  // Show permission check loading
  if (hasPermission === null) {
    return (
      <Box p={6}>
        <VStack spacing={4}>
          <Spinner size="lg" />
          <Text>Checking permissions...</Text>
        </VStack>
      </Box>
    );
  }

  // Show permission denied
  if (hasPermission === false) {
    return (
      <Box p={6}>
        <Alert status="warning">
          <AlertIcon />
          <VStack align="start" spacing={2}>
            <Text fontWeight="bold">Access Denied</Text>
            <Text>
              You need Members_Read or Members_CRUD permissions to access member reporting.
            </Text>
            {error && <Text fontSize="sm" color="gray.600">{error}</Text>}
          </VStack>
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <VStack align="start" spacing={1}>
            <Heading size="lg">Member Reporting Dashboard</Heading>
            <Text color="gray.600">
              Simple JSON export - much better than parquet files!
            </Text>
          </VStack>
          
          <HStack spacing={3}>
            {metadata && (
              <VStack align="end" spacing={0}>
                <Badge colorScheme="green" variant="subtle">
                  {metadata.total_count} members
                </Badge>
                <Text fontSize="xs" color="gray.500">
                  {new Date(metadata.export_date).toLocaleString()}
                </Text>
              </VStack>
            )}
            
            <Button
              onClick={handleRefresh}
              isLoading={loading}
              loadingText="Loading..."
              colorScheme="blue"
              size="sm"
            >
              Refresh Data
            </Button>
          </HStack>
        </Flex>

        {/* Error Display */}
        {error && (
          <Alert status="error">
            <AlertIcon />
            <VStack align="start" spacing={1}>
              <Text fontWeight="bold">Error Loading Member Data</Text>
              <Text>{error}</Text>
            </VStack>
          </Alert>
        )}

        {/* Loading State */}
        {loading && (
          <Box textAlign="center" py={8}>
            <VStack spacing={4}>
              <Spinner size="lg" />
              <Text>Loading member data...</Text>
              <Text fontSize="sm" color="gray.600">
                Using simple JSON export (much faster than parquet!)
              </Text>
            </VStack>
          </Box>
        )}

        {/* Data Display */}
        {members && members.length > 0 && (
          <>
            {/* Success Message */}
            <Alert status="success">
              <AlertIcon />
              <VStack align="start" spacing={1}>
                <Text fontWeight="bold">Member Data Loaded Successfully</Text>
                <Text>
                  Loaded {members.length} members using simple JSON export.
                  {metadata?.applied_filters?.regional && " Regional filtering applied."}
                </Text>
              </VStack>
            </Alert>

            {/* Analytics Section */}
            <AnalyticsSection 
              members={members}
              loading={loading}
              error={error}
              userRegion={userRegion}
              onRefreshData={exportMembers}
            />

            {/* Address Labels Section */}
            <AddressLabelsSection 
              members={members}
              userRole={userRole}
              userRegion={userRegion}
            />
          </>
        )}

        {/* No Data State */}
        {members && members.length === 0 && (
          <Alert status="info">
            <AlertIcon />
            <Text>No member data available for your region/permissions.</Text>
          </Alert>
        )}
      </VStack>
    </Box>
  );
};

export default MemberReportingDashboard;