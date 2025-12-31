import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Heading, Button, Table, Thead, Tbody, Tr, Th, Td,
  Input, Select, Badge, useToast, Spinner, Text, Tabs, TabList, TabPanels, Tab, TabPanel,
  Stack, useBreakpointValue, IconButton
} from '@chakra-ui/react';
import { SearchIcon, EditIcon, ViewIcon } from '@chakra-ui/icons';
import MemberDetailModal from './components/MemberDetailModal';
import MemberEditModal from './components/MemberEditModal';
import CognitoAdminPage from './CognitoAdminPage';
import { hasRegionalAccess } from '../../utils/regionalMapping';
import { Member } from '../../types';
import { getAuthHeaders, getAuthHeadersForGet } from '../../utils/authHeaders';
import { API_URLS } from '../../config/api';
import { useErrorHandler, apiCall } from '../../utils/errorHandler';
import { FunctionPermissionManager, getUserRoles } from '../../utils/functionPermissions';

interface MemberAdminPageProps {
  user: any;
}

function MemberAdminPage({ user }: MemberAdminPageProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [filteredMembers, setFilteredMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [displaySearchTerm, setDisplaySearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [regionFilter, setRegionFilter] = useState('all');
  const [uniqueStatuses, setUniqueStatuses] = useState<string[]>([]);
  const [uniqueRegions, setUniqueRegions] = useState<string[]>([]);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [permissionManager, setPermissionManager] = useState<FunctionPermissionManager | null>(null);
  const [userRoles, setUserRoles] = useState<string[]>([]);

  // Enhanced role-based access checks for Members_CRUD_All and other admin roles
  const hasMembersCRUDAllRole = userRoles.includes('Members_CRUD_All');
  const hasMembersReadAllRole = userRoles.includes('Members_Read_All');
  const hasMembersStatusApproveRole = userRoles.includes('Members_Status_Approve');
  const hasMembersExportAllRole = userRoles.includes('Members_Export_All');
  const hasSystemUserManagementRole = userRoles.includes('System_User_Management');
  const hasWebmasterRole = userRoles.includes('Webmaster');
  const hasNationalChairmanRole = userRoles.includes('National_Chairman');
  const hasNationalSecretaryRole = userRoles.includes('National_Secretary');
  
  // Members_CRUD_All role gets full member management capabilities
  const hasFullMemberAccess = hasMembersCRUDAllRole || userRoles.includes('hdcnAdmins') || hasWebmasterRole;
  
  // Enhanced member read access for various admin roles
  const hasEnhancedMemberReadAccess = hasFullMemberAccess || 
    hasMembersReadAllRole || 
    hasNationalChairmanRole || 
    hasNationalSecretaryRole ||
    userRoles.includes('Tour_Commissioner') ||
    userRoles.includes('Club_Magazine_Editorial') ||
    userRoles.some(role => role.includes('Regional_Chairman_') || role.includes('Regional_Secretary_'));
  
  // Member export capabilities for communication and administrative roles
  const hasMemberExportAccess = hasFullMemberAccess || 
    hasMembersExportAllRole ||
    hasNationalSecretaryRole ||
    userRoles.includes('Tour_Commissioner') ||
    userRoles.includes('Club_Magazine_Editorial') ||
    userRoles.some(role => role.includes('Regional_Secretary_'));
  
  // Status approval capabilities
  const hasStatusApprovalAccess = hasFullMemberAccess || 
    hasMembersStatusApproveRole ||
    hasNationalChairmanRole;

  // System administration access (Cognito management)
  const hasSystemAdminAccess = hasFullMemberAccess ||
    hasSystemUserManagementRole ||
    userRoles.includes('hdcnAdmins');

  const { handleError, handleSuccess } = useErrorHandler();
  const isMobile = useBreakpointValue({ base: true, md: false });

  useEffect(() => {
    loadMembers();
    initializePermissions();
  }, []);

  useEffect(() => {
    filterMembers();
    extractUniqueStatuses();
    extractUniqueRegions();
  }, [members, searchTerm, statusFilter, regionFilter]);

  const initializePermissions = async () => {
    try {
      const manager = await FunctionPermissionManager.create(user);
      setPermissionManager(manager);
      setUserRoles(getUserRoles(user));
    } catch (error) {
      console.error('Failed to initialize permissions:', error);
      // Fallback: extract roles directly from user token
      setUserRoles(getUserRoles(user));
    }
  };

  const extractUniqueStatuses = () => {
    const statuses = Array.from(new Set(members.map(member => member.status).filter(Boolean)));
    setUniqueStatuses(statuses.sort());
  };

  const extractUniqueRegions = () => {
    const regions = Array.from(new Set(members.map(member => member.regio).filter(Boolean)));
    setUniqueRegions(regions.sort());
  };

  const loadMembers = async () => {
    try {
      const headers = await getAuthHeadersForGet();
      const data = await apiCall<Member[]>(
        fetch(API_URLS.members(), { headers }),
        'laden leden'
      );
      setMembers(data);
    } catch (error: any) {
      handleError(error, 'laden leden');
    } finally {
      setLoading(false);
    }
  };



  const filterMembers = () => {
    let filtered = members;

    // Apply role-based filtering first
    if (permissionManager && userRoles.length > 0) {
      filtered = filtered.filter(member => {
        // Check if user has permission to view this member
        const canViewMember = canViewMemberRecord(member);
        return canViewMember;
      });
    }

    if (searchTerm) {
      filtered = filtered.filter(member =>
        member.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        member.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        member.voornaam?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        member.achternaam?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        member.lidnummer?.toString().toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(member => member.status === statusFilter);
    }

    if (regionFilter !== 'all') {
      filtered = filtered.filter(member => member.regio === regionFilter);
    }

    setFilteredMembers(filtered);
  };

  /**
   * Check if current user can view a specific member record based on their roles
   */
  const canViewMemberRecord = (member: Member): boolean => {
    if (!permissionManager) return true; // Fallback to allow access if permissions not loaded

    // Admin roles can view all members
    if (userRoles.includes('hdcnAdmins') || 
        userRoles.includes('Members_CRUD_All') || 
        userRoles.includes('Members_Read_All')) {
      return true;
    }

    // Check if user is viewing their own record
    const isOwnRecord = member.email === user?.attributes?.email;
    if (isOwnRecord && userRoles.includes('hdcnLeden')) {
      return true;
    }

    // Regional access - check if user has regional permissions for this member's region
    if (member.regio) {
      if (hasRegionalAccess(userRoles, member.regio)) {
        return true;
      }
    }

    // National roles with member read access
    if (userRoles.includes('National_Chairman') || 
        userRoles.includes('National_Secretary') ||
        userRoles.includes('Webmaster') ||
        userRoles.includes('Tour_Commissioner') ||
        userRoles.includes('Club_Magazine_Editorial')) {
      return true;
    }

    // Additional role-based access checks
    if (userRoles.includes('Members_Export_All') ||
        userRoles.includes('Members_Status_Approve')) {
      return true;
    }

    return false;
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'green';
      case 'inactive': return 'red';
      case 'pending': return 'yellow';
      default: return 'gray';
    }
  };

  const handleViewMember = (member: Member) => {
    if (canViewMemberRecord(member)) {
      setSelectedMember(member);
      setIsDetailModalOpen(true);
    } else {
      handleError({ status: 403, message: 'Geen toestemming om dit lid te bekijken' }, 'toegang geweigerd');
    }
  };

  const handleEditMember = (member: Member) => {
    if (canEditMemberRecord(member)) {
      setSelectedMember(member);
      setIsEditModalOpen(true);
    } else {
      handleError({ status: 403, message: 'Geen toestemming om dit lid te bewerken' }, 'toegang geweigerd');
    }
  };

  /**
   * Check if current user can edit a specific member record based on their roles
   */
  const canEditMemberRecord = (member: Member): boolean => {
    if (!permissionManager) return false; // Fallback to deny access if permissions not loaded

    // Admin roles can edit all members
    if (userRoles.includes('hdcnAdmins') || userRoles.includes('Members_CRUD_All')) {
      return true;
    }

    // Check if user is editing their own record (basic members can edit their own data)
    const isOwnRecord = member.email === user?.attributes?.email;
    if (isOwnRecord && userRoles.includes('hdcnLeden')) {
      return true;
    }

    // Regional roles with write access
    if (member.regio) {
      if (hasRegionalAccess(userRoles, member.regio)) {
        // Check if user has write permissions (Chairman roles)
        const hasRegionalWriteAccess = userRoles.some(role => 
          role.includes('Regional_Chairman_') && role.includes('Region')
        );
        
        if (hasRegionalWriteAccess) {
          return true;
        }
      }
    }

    // Webmaster has full edit access
    if (userRoles.includes('Webmaster')) {
      return true;
    }

    // Additional roles with specific edit permissions
    if (userRoles.includes('Members_Status_Approve') && 
        member.status && member.status !== 'active') {
      // Can only edit status field for non-active members
      return true;
    }

    return false;
  };



  const handleDeleteMember = async (member: Member) => {
    try {
      const headers = await getAuthHeaders();
      await apiCall<void>(
        fetch(API_URLS.member(member.member_id), { method: 'DELETE', headers }),
        'verwijderen lid'
      );
      await loadMembers();
      handleSuccess('Lid succesvol verwijderd');
    } catch (error: any) {
      handleError(error, 'verwijderen lid');
    }
  };

  const handleMemberUpdate = async (updatedMember: Member) => {
    try {
      const headers = await getAuthHeaders();
      await apiCall<void>(
        fetch(API_URLS.member(updatedMember.member_id), {
          method: 'PUT',
          headers,
          body: JSON.stringify(updatedMember)
        }),
        'bijwerken lid'
      );
      await loadMembers();
      handleSuccess('Lid succesvol bijgewerkt');
    } catch (error: any) {
      handleError(error, 'bijwerken lid');
    }
  };

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Spinner size="xl" color="orange.400" />
        <Text mt={4} color="orange.400">Leden laden...</Text>
      </Box>
    );
  }

  return (
    <Box p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        <Heading color="orange.400">Ledenadministratie</Heading>
        
        <Tabs colorScheme="orange" variant="enclosed">
          <TabList>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Leden Overzicht
            </Tab>
            {hasSystemAdminAccess && (
              <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
                Cognito Beheer
              </Tab>
            )}
          </TabList>

          <TabPanels>
            <TabPanel p={0} pt={6}>
              <VStack spacing={6} align="stretch">

                {/* Enhanced functionality for Members_CRUD_All role */}
                {hasFullMemberAccess && (
                  <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="green.400" mb={4}>
                    <Text color="green.400" fontWeight="bold" mb={3}>
                      🔧 Geavanceerde Ledenadministratie (Members_CRUD_All)
                    </Text>
                    <HStack spacing={4} wrap="wrap">
                      <Button
                        size="sm"
                        colorScheme="green"
                        onClick={() => {
                          // Bulk status update functionality
                          const selectedMembers = filteredMembers.filter(m => m.status === 'pending');
                          if (selectedMembers.length > 0) {
                            handleSuccess(`${selectedMembers.length} leden met status 'pending' gevonden voor bulk bewerking`);
                          } else {
                            handleError({ status: 404, message: 'Geen leden met status pending gevonden' }, 'bulk bewerking');
                          }
                        }}
                      >
                        📋 Bulk Status Update
                      </Button>
                      <Button
                        size="sm"
                        colorScheme="blue"
                        onClick={() => {
                          // Member data export functionality
                          const exportData = filteredMembers.map(m => ({
                            lidnummer: m.lidnummer,
                            naam: m.name,
                            email: m.email,
                            status: m.status,
                            regio: m.regio,
                            lidmaatschap: m.lidmaatschap
                          }));
                          const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `leden-export-${new Date().toISOString().split('T')[0]}.json`;
                          a.click();
                          URL.revokeObjectURL(url);
                          handleSuccess('Ledendata geëxporteerd');
                        }}
                      >
                        📊 Export Ledendata
                      </Button>
                      <Button
                        size="sm"
                        colorScheme="purple"
                        onClick={() => {
                          // Advanced member statistics
                          const stats = {
                            totaal: filteredMembers.length,
                            perStatus: uniqueStatuses.reduce((acc, status) => {
                              acc[status] = filteredMembers.filter(m => m.status === status).length;
                              return acc;
                            }, {}),
                            perRegio: uniqueRegions.reduce((acc, regio) => {
                              acc[regio] = filteredMembers.filter(m => m.regio === regio).length;
                              return acc;
                            }, {})
                          };
                          console.log('📊 Geavanceerde ledenstatistieken:', stats);
                          handleSuccess('Statistieken gegenereerd (zie console)');
                        }}
                      >
                        📈 Geavanceerde Statistieken
                      </Button>
                    </HStack>
                  </Box>
                )}

                {/* Enhanced functionality for other admin roles */}
                {(hasMemberExportAccess && !hasFullMemberAccess) && (
                  <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="blue.400" mb={4}>
                    <Text color="blue.400" fontWeight="bold" mb={3}>
                      📧 Communicatie & Export Functies
                    </Text>
                    <HStack spacing={4} wrap="wrap">
                      <Button
                        size="sm"
                        colorScheme="blue"
                        onClick={() => {
                          // Email list export for communication roles
                          const emailList = filteredMembers
                            .filter(m => m.email && m.nieuwsbrief !== 'Nee')
                            .map(m => m.email)
                            .join('\n');
                          const blob = new Blob([emailList], { type: 'text/plain' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `email-lijst-${new Date().toISOString().split('T')[0]}.txt`;
                          a.click();
                          URL.revokeObjectURL(url);
                          handleSuccess('Email lijst geëxporteerd');
                        }}
                      >
                        📧 Export Email Lijst
                      </Button>
                      <Button
                        size="sm"
                        colorScheme="teal"
                        onClick={() => {
                          // Newsletter subscribers export
                          const newsletterSubscribers = filteredMembers.filter(m => m.nieuwsbrief === 'Ja');
                          handleSuccess(`${newsletterSubscribers.length} nieuwsbrief abonnees gevonden`);
                        }}
                      >
                        📰 Nieuwsbrief Abonnees
                      </Button>
                    </HStack>
                  </Box>
                )}

                {/* Enhanced functionality for status approval roles */}
                {(hasStatusApprovalAccess && !hasFullMemberAccess) && (
                  <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="yellow.400" mb={4}>
                    <Text color="yellow.400" fontWeight="bold" mb={3}>
                      ✅ Status Goedkeuring Functies
                    </Text>
                    <HStack spacing={4} wrap="wrap">
                      <Button
                        size="sm"
                        colorScheme="yellow"
                        onClick={() => {
                          const pendingMembers = filteredMembers.filter(m => m.status === 'pending' || m.status === 'new_applicant');
                          handleSuccess(`${pendingMembers.length} leden wachten op status goedkeuring`);
                        }}
                      >
                        ⏳ Wachtende Goedkeuringen
                      </Button>
                      <Button
                        size="sm"
                        colorScheme="green"
                        onClick={() => {
                          // Quick approve functionality would go here
                          handleSuccess('Bulk goedkeuring functionaliteit beschikbaar');
                        }}
                      >
                        ✅ Bulk Goedkeuring
                      </Button>
                    </HStack>
                  </Box>
                )}
        <Stack direction={{ base: 'column', md: 'row' }} spacing={4}>
          <HStack flex={1}>
            <SearchIcon color="orange.400" />
            <Input
              placeholder="Zoek op naam, email of lidnummer..."
              value={displaySearchTerm}
              onChange={(e) => {
                const value = e.target.value;
                setDisplaySearchTerm(value);
                setSearchTerm(value);
              }}
              bg="gray.800"
              color="white"
              borderColor="orange.400"
              focusBorderColor="orange.500"
              data-1p-ignore
              data-lpignore="true"
              autoComplete="off"
            />
          </HStack>
          <Stack direction={{ base: 'column', sm: 'row' }} spacing={2}>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              bg="gray.800"
              color="orange.400"
              borderColor="orange.400"
              maxW={{ base: 'full', md: '200px' }}
              sx={{
                '& option': {
                  bg: 'black',
                  color: 'orange'
                }
              }}
            >
              <option value="all" style={{backgroundColor: 'black', color: 'orange'}}>Alle statussen</option>
              {uniqueStatuses.map(status => (
                <option key={status} value={status} style={{backgroundColor: 'black', color: 'orange'}}>{status}</option>
              ))}
            </Select>
            <Select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              bg="gray.800"
              color="orange.400"
              borderColor="orange.400"
              maxW={{ base: 'full', md: '200px' }}
              sx={{
                '& option': {
                  bg: 'black',
                  color: 'orange'
                }
              }}
            >
              <option value="all" style={{backgroundColor: 'black', color: 'orange'}}>Alle regio's</option>
              {uniqueRegions.map(region => (
                <option key={region} value={region} style={{backgroundColor: 'black', color: 'orange'}}>{region}</option>
              ))}
            </Select>
          </Stack>
        </Stack>

                {/* Stats */}
        <HStack spacing={4} wrap="wrap">
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="orange.400">
            <Text color="orange.400" fontSize="sm">Gefilterd Totaal</Text>
            <Text color="white" fontSize="2xl" fontWeight="bold">{filteredMembers.length}</Text>
          </Box>
          {uniqueStatuses.map(status => {
            const count = filteredMembers.filter(m => m.status === status).length;
            const color = getStatusColor(status);
            return (
              <Box key={status} bg="gray.800" p={4} borderRadius="md" border="1px" borderColor={`${color}.400`}>
                <Text color={`${color}.400`} fontSize="sm">{status}</Text>
                <Text color="white" fontSize="2xl" fontWeight="bold">{count}</Text>
              </Box>
            );
          })}
        </HStack>

                {/* Members Table */}
        <Box 
          bg="gray.800" 
          borderRadius="md" 
          border="1px" 
          borderColor="orange.400" 
          overflow="auto"
          maxW="100%"
        >
          <Table variant="simple" size={{ base: 'sm', md: 'md' }}>
            <Thead bg="gray.700">
              <Tr>
                <Th color="orange.300" minW="80px" display={{ base: 'none', md: 'table-cell' }}>Lidnummer</Th>
                <Th color="orange.300" minW="120px">Naam</Th>
                <Th color="orange.300" minW="150px">Email</Th>
                <Th color="orange.300" minW="100px" display={{ base: 'none', lg: 'table-cell' }}>Lidmaatschap</Th>
                <Th color="orange.300" minW="80px">Status</Th>
                <Th color="orange.300" minW="100px" display={{ base: 'none', md: 'table-cell' }}>Lid sinds</Th>
                <Th color="orange.300" minW="150px" position="sticky" right={0} bg="gray.700">Acties</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredMembers.map((member) => (
                  <Tr key={member.member_id} _hover={{ bg: 'gray.700' }}>
                    <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                      {member.lidnummer || '-'}
                    </Td>
                    <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                      <Text isTruncated maxW="120px">
                        {member.name || `${member.voornaam} ${member.achternaam}`}
                      </Text>
                    </Td>
                    <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                      <Text isTruncated maxW="150px">{member.email}</Text>
                    </Td>
                    <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                      {member.lidmaatschap || member.membership_type || member.membershipType || '-'}
                    </Td>
                    <Td>
                      <Badge colorScheme={getStatusColor(member.status)} fontSize={{ base: 'xs', md: 'sm' }}>
                        {member.status || 'Onbekend'}
                      </Badge>
                    </Td>
                    <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                      {member.created_at ? new Date(member.created_at).toLocaleDateString('nl-NL') : '-'}
                    </Td>
                    <Td position="sticky" right={0} bg="gray.800">
                      {isMobile ? (
                        <HStack spacing={1}>
                          {canViewMemberRecord(member) && (
                            <IconButton
                              size="xs"
                              colorScheme="blue"
                              icon={<ViewIcon />}
                              onClick={() => handleViewMember(member)}
                              title="Bekijk"
                              aria-label="Bekijk"
                            />
                          )}
                          {canEditMemberRecord(member) && (
                            <IconButton
                              size="xs"
                              colorScheme="orange"
                              icon={<EditIcon />}
                              onClick={() => handleEditMember(member)}
                              title="Bewerk"
                              aria-label="Bewerk"
                            />
                          )}
                        </HStack>
                      ) : (
                        <HStack spacing={2}>
                          {canViewMemberRecord(member) && (
                            <Button
                              size="sm"
                              colorScheme="blue"
                              leftIcon={<ViewIcon />}
                              onClick={() => handleViewMember(member)}
                            >
                              Bekijk
                            </Button>
                          )}
                          {canEditMemberRecord(member) && (
                            <Button
                              size="sm"
                              colorScheme="orange"
                              leftIcon={<EditIcon />}
                              onClick={() => handleEditMember(member)}
                            >
                              Bewerk
                            </Button>
                          )}
                        </HStack>
                      )}
                    </Td>
                  </Tr>
                )
              )}
            </Tbody>
          </Table>
        </Box>

                {filteredMembers.length === 0 && (
                  <Text textAlign="center" color="gray.400" py={8}>
                    Geen leden gevonden met de huidige filters.
                  </Text>
                )}
              </VStack>
            </TabPanel>
            {hasSystemAdminAccess && (
              <TabPanel p={0} pt={6}>
                <CognitoAdminPage user={user} />
              </TabPanel>
            )}
          </TabPanels>
        </Tabs>
      </VStack>

      {/* Modals */}
      <MemberDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        member={selectedMember}
        user={user}
      />

      <MemberEditModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        member={selectedMember}
        onSave={handleMemberUpdate}
        user={user}
      />


    </Box>
  );
}

export default MemberAdminPage;