/**
 * MemberList Component
 * 
 * Displays a list of members with regional filtering, caching, and refresh capability.
 * Integrates with MemberDataService for data fetching and session storage caching.
 * 
 * Features:
 * - Fetches regionally-filtered member data from backend
 * - Caches data in browser session storage
 * - Loading and error states
 * - Manual refresh button for CRUD users
 * - Displays member count (filtered / total)
 * - Preserves UI state during refresh
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Center,
  Badge,
  useToast,
  Flex,
} from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MemberDataService } from '../services/MemberDataService';
import { Member } from '../types/index';
import { useAuth } from '../hooks/useAuth';
import { userHasPermissionType } from '../utils/functionPermissions';

interface MemberListProps {
  /**
   * Optional filter function to apply to members
   * Allows parent components to control filtering
   */
  filterFn?: (member: Member) => boolean;
  
  /**
   * Optional callback when members are loaded
   */
  onMembersLoaded?: (members: Member[]) => void;
  
  /**
   * Optional render function for member display
   * If not provided, uses default table display
   */
  renderMembers?: (members: Member[]) => React.ReactNode;
}

export const MemberList: React.FC<MemberListProps> = ({
  filterFn,
  onMembersLoaded,
  renderMembers,
}) => {
  // State management
  const [members, setMembers] = useState<Member[]>([]);
  const [filteredMembers, setFilteredMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  
  // Refs for preserving UI state
  const scrollPositionRef = useRef<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Hooks
  const { user } = useAuth();
  const toast = useToast();
  
  // Check if user has CRUD permissions for refresh button
  const canRefresh = user ? (
    userHasPermissionType(user, 'members', 'crud')
  ) : false;
  
  // Load members on mount
  useEffect(() => {
    loadMembers();
  }, []);
  
  // Apply filters when members or filterFn changes
  useEffect(() => {
    if (filterFn) {
      const filtered = members.filter(filterFn);
      setFilteredMembers(filtered);
    } else {
      setFilteredMembers(members);
    }
  }, [members, filterFn]);
  
  // Notify parent when members are loaded
  useEffect(() => {
    if (onMembersLoaded && members.length > 0) {
      onMembersLoaded(members);
    }
  }, [members, onMembersLoaded]);
  
  /**
   * Load members from backend (with caching)
   */
  const loadMembers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('[MemberList] Loading members...');
      const data = await MemberDataService.fetchMembers();
      
      setMembers(data);
      console.log(`[MemberList] Loaded ${data.length} members`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load member data';
      setError(errorMessage);
      console.error('[MemberList] Error loading members:', err);
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Handle manual refresh
   * Preserves scroll position and UI state
   */
  const handleRefresh = async () => {
    try {
      // Save current scroll position
      if (containerRef.current) {
        scrollPositionRef.current = containerRef.current.scrollTop;
      }
      
      setRefreshing(true);
      setError(null);
      
      console.log('[MemberList] Refreshing member data...');
      const data = await MemberDataService.refreshMembers();
      
      setMembers(data);
      
      // Restore scroll position after a brief delay
      setTimeout(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = scrollPositionRef.current;
        }
      }, 100);
      
      // Show success toast
      toast({
        title: 'Data Refreshed',
        description: `Successfully loaded ${data.length} members`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      console.log(`[MemberList] Refreshed ${data.length} members`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to refresh member data';
      setError(errorMessage);
      
      // Show error toast
      toast({
        title: 'Refresh Failed',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      
      console.error('[MemberList] Error refreshing members:', err);
    } finally {
      setRefreshing(false);
    }
  };
  
  /**
   * Render loading state
   */
  if (loading && !refreshing) {
    return (
      <Box p={6}>
        <Center py={10}>
          <VStack spacing={4}>
            <Spinner size="xl" color="blue.500" thickness="4px" />
            <Text fontSize="lg" color="gray.600">
              Loading member data...
            </Text>
            <Text fontSize="sm" color="gray.500">
              Using regional filtering and session cache
            </Text>
          </VStack>
        </Center>
      </Box>
    );
  }
  
  /**
   * Render error state
   */
  if (error && !members.length) {
    return (
      <Box p={6}>
        <Alert
          status="error"
          variant="subtle"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          textAlign="center"
          minHeight="200px"
        >
          <AlertIcon boxSize="40px" mr={0} />
          <AlertTitle mt={4} mb={1} fontSize="lg">
            Error Loading Member Data
          </AlertTitle>
          <AlertDescription maxWidth="sm" mb={4}>
            {error}
          </AlertDescription>
          <Button
            colorScheme="red"
            variant="outline"
            onClick={loadMembers}
            leftIcon={<RepeatIcon />}
          >
            Try Again
          </Button>
        </Alert>
      </Box>
    );
  }
  
  /**
   * Render main content
   */
  return (
    <Box p={6} ref={containerRef}>
      <VStack spacing={6} align="stretch">
        {/* Header with member count and refresh button */}
        <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
          <VStack align="start" spacing={1}>
            <HStack spacing={3}>
              <Heading size="lg">Members</Heading>
              <Badge colorScheme="blue" fontSize="md" px={3} py={1}>
                {filteredMembers.length}
                {filteredMembers.length !== members.length && ` / ${members.length}`}
              </Badge>
            </HStack>
            <Text color="gray.600" fontSize="sm">
              {filteredMembers.length === members.length
                ? `Showing all ${members.length} members`
                : `Showing ${filteredMembers.length} of ${members.length} members`}
            </Text>
          </VStack>
          
          {/* Refresh button (only for CRUD users) */}
          {canRefresh && (
            <Button
              leftIcon={<RepeatIcon />}
              onClick={handleRefresh}
              isLoading={refreshing}
              loadingText="Refreshing..."
              colorScheme="blue"
              size="md"
              variant="outline"
            >
              Refresh Data
            </Button>
          )}
        </Flex>
        
        {/* Error banner (if error but we have cached data) */}
        {error && members.length > 0 && (
          <Alert status="warning">
            <AlertIcon />
            <VStack align="start" spacing={1} flex={1}>
              <AlertTitle>Refresh Failed</AlertTitle>
              <AlertDescription fontSize="sm">
                {error}. Showing cached data.
              </AlertDescription>
            </VStack>
          </Alert>
        )}
        
        {/* Member display */}
        {members.length === 0 ? (
          <Alert status="info">
            <AlertIcon />
            <VStack align="start" spacing={1}>
              <AlertTitle>No Members Found</AlertTitle>
              <AlertDescription>
                No member data available for your region/permissions.
              </AlertDescription>
            </VStack>
          </Alert>
        ) : (
          <>
            {/* Custom render function or default display */}
            {renderMembers ? (
              renderMembers(filteredMembers)
            ) : (
              <Box>
                <Text color="gray.600">
                  Use the <code>renderMembers</code> prop to display member data.
                </Text>
                <Text color="gray.500" fontSize="sm" mt={2}>
                  Example: Pass a table component or custom layout to display the {filteredMembers.length} loaded members.
                </Text>
              </Box>
            )}
          </>
        )}
      </VStack>
    </Box>
  );
};

export default MemberList;
