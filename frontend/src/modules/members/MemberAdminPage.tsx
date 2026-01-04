/**
 * Member Admin Page - Using Field Registry System
 * 
 * Complete member administration using field registry components
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Button,
  useToast,
  Spinner,
  Text,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useDisclosure,
  Alert,
  AlertIcon
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import MemberAdminTable from '../../components/MemberAdminTable';
import MemberReadView from '../../components/MemberReadView';
import MemberEditView from '../../components/MemberEditView';
import MemberSelfServiceView from '../../components/MemberSelfServiceView';
import { HDCNGroup } from '../../config/memberFields';
import { Member } from '../../types';
import { getAuthHeaders, getAuthHeadersForGet } from '../../utils/authHeaders';
import { API_URLS } from '../../config/api';
import { useErrorHandler, apiCall } from '../../utils/errorHandler';
import { getUserRoles } from '../../utils/functionPermissions';

interface MemberAdminPageProps {
  user: any;
}

function MemberAdminPage({ user }: MemberAdminPageProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [userRoles, setUserRoles] = useState<string[]>([]);
  const [userRegion, setUserRegion] = useState<string>('');
  
  const toast = useToast();
  const { handleError } = useErrorHandler();
  
  // Modal controls
  const { 
    isOpen: isReadModalOpen, 
    onOpen: onReadModalOpen, 
    onClose: onReadModalClose 
  } = useDisclosure();
  
  const { 
    isOpen: isEditModalOpen, 
    onOpen: onEditModalOpen, 
    onClose: onEditModalClose 
  } = useDisclosure();

  // Get user role for field registry system
  const getUserRole = (): HDCNGroup => {
    if (userRoles.includes('System_CRUD_All')) return 'System_CRUD_All';
    if (userRoles.includes('Members_CRUD_All')) return 'Members_CRUD_All';
    if (userRoles.includes('Members_Read_All')) return 'Members_Read_All';
    if (userRoles.includes('System_User_Management')) return 'System_User_Management';
    if (userRoles.includes('hdcnLeden')) return 'hdcnLeden';
    return 'hdcnLeden'; // Default fallback
  };

  // Check if user is viewing their own data
  const isOwnRecord = (member: Member) => {
    return user?.attributes?.email === member.email;
  };

  // Load user roles and region
  useEffect(() => {
    const loadUserInfo = async () => {
      try {
        const roles = getUserRoles(user);
        setUserRoles(roles);
        
        // Get user region if they have regional restrictions
        if (roles.includes('Members_Read_All') && user?.attributes?.email) {
          // In a real implementation, you'd fetch the user's region from the API
          // For now, we'll use a placeholder
          setUserRegion('Noord-Holland'); // This should come from user profile
        }
      } catch (error) {
        console.error('Error loading user info:', error);
      }
    };

    loadUserInfo();
  }, [user]);

  // Load members
  useEffect(() => {
    const loadMembers = async () => {
      try {
        setLoading(true);
        
        const headers = await getAuthHeadersForGet();
        const data = await apiCall<any>(
          fetch(API_URLS.members(), { headers }),
          'laden leden'
        );
        setMembers(Array.isArray(data) ? data : (data?.members || []));
      } catch (error) {
        handleError(error, 'Fout bij het laden van leden');
      } finally {
        setLoading(false);
      }
    };

    if (userRoles.length > 0) {
      loadMembers();
    }
  }, [userRoles]); // Removed handleError from dependencies

  // Handle member view
  const handleMemberView = (member: Member) => {
    setSelectedMember(member);
    onReadModalOpen();
  };

  // Handle member edit
  const handleMemberEdit = (member: Member) => {
    setSelectedMember(member);
    onEditModalOpen();
  };

  // Handle member save
  const handleMemberSave = async (memberData: any) => {
    try {
      const headers = await getAuthHeaders();
      await apiCall<void>(
        fetch(API_URLS.member(selectedMember?.member_id || ''), {
          method: 'PUT',
          headers,
          body: JSON.stringify(memberData)
        }),
        'bijwerken lid'
      );

      // Update local state
      setMembers(prev => prev.map(m => 
        m.member_id === selectedMember?.member_id 
          ? { ...m, ...memberData }
          : m
      ));
      
      toast({
        title: 'Lid bijgewerkt',
        description: 'De lidgegevens zijn succesvol bijgewerkt.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      handleError(error, 'Fout bij het bijwerken van lid');
      throw error; // Re-throw so the component can handle it
    }
  };

  // Handle export (disabled for now - no backend endpoint)
  const handleExport = async (context: string) => {
    toast({
      title: 'Export functie',
      description: 'Export functionaliteit wordt binnenkort toegevoegd.',
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  // Handle edit modal close
  const handleEditModalClose = () => {
    onEditModalClose();
    setSelectedMember(null);
  };

  // Handle read modal close
  const handleReadModalClose = () => {
    onReadModalClose();
    setSelectedMember(null);
  };

  // Handle edit from read modal
  const handleEditFromReadModal = () => {
    onReadModalClose();
    onEditModalOpen();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minH="400px">
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.500" />
          <Text>Leden laden...</Text>
        </VStack>
      </Box>
    );
  }

  // Check if user has any member access
  const hasAnyMemberAccess = userRoles.some(role => 
    ['System_CRUD_All', 'Members_CRUD_All', 'Members_Read_All', 'System_User_Management'].includes(role)
  );

  if (!hasAnyMemberAccess) {
    return (
      <Box p={6}>
        <Alert status="warning">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold">Geen toegang</Text>
            <Text fontSize="sm">
              U heeft geen toegang tot de ledenadministratie. Neem contact op met een beheerder.
            </Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // Show self-service view for regular members
  if (getUserRole() === 'hdcnLeden' && members.length > 0) {
    const ownMember = members.find(m => isOwnRecord(m));
    if (ownMember) {
      return (
        <MemberSelfServiceView 
          member={ownMember}
          onUpdate={handleMemberSave}
        />
      );
    }
  }

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Heading color="orange.500">
            Ledenadministratie
          </Heading>
          
          {/* Add member button for admins */}
          {['System_CRUD_All', 'Members_CRUD_All'].includes(getUserRole()) && (
            <Button
              leftIcon={<AddIcon />}
              colorScheme="orange"
              onClick={() => {
                // Navigate to membership form or open add modal
                window.location.href = '/membership';
              }}
            >
              Nieuw Lid
            </Button>
          )}
        </HStack>

        {/* Main Content */}
        <Tabs variant="enclosed" colorScheme="orange">
          <TabList>
            <Tab>📊 Leden Overzicht</Tab>
            {getUserRole() === 'System_CRUD_All' && (
              <Tab>👥 Gebruikersbeheer</Tab>
            )}
          </TabList>

          <TabPanels>
            {/* Members Table Tab */}
            <TabPanel p={0}>
              <MemberAdminTable
                members={members}
                userRole={getUserRole()}
                userRegion={userRegion}
                onMemberView={handleMemberView}
                onMemberEdit={handleMemberEdit}
                onExport={handleExport}
              />
            </TabPanel>

            {/* User Management Tab (System_CRUD_All only) */}
            {getUserRole() === 'System_CRUD_All' && (
              <TabPanel>
                <Box p={4}>
                  <Text>Gebruikersbeheer functionaliteit komt hier...</Text>
                </Box>
              </TabPanel>
            )}
          </TabPanels>
        </Tabs>

        {/* Read Modal */}
        {selectedMember && (
          <MemberReadView
            isOpen={isReadModalOpen}
            onClose={handleReadModalClose}
            member={selectedMember}
            userRole={getUserRole()}
            userRegion={userRegion}
            onEdit={handleEditFromReadModal}
          />
        )}

        {/* Edit Modal */}
        {selectedMember && (
          <MemberEditView
            isOpen={isEditModalOpen}
            onClose={handleEditModalClose}
            member={selectedMember}
            userRole={getUserRole()}
            userRegion={userRegion}
            onSave={handleMemberSave}
          />
        )}
      </VStack>
    </Box>
  );
}

export default MemberAdminPage;