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

function MemberAdminPage({ user }) {
  const [members, setMembers] = useState([]);
  const [filteredMembers, setFilteredMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [displaySearchTerm, setDisplaySearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [regionFilter, setRegionFilter] = useState('all');
  const [uniqueStatuses, setUniqueStatuses] = useState([]);
  const [uniqueRegions, setUniqueRegions] = useState([]);
  const [selectedMember, setSelectedMember] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const toast = useToast();
  const isMobile = useBreakpointValue({ base: true, md: false });

  useEffect(() => {
    loadMembers();
  }, []);

  useEffect(() => {
    filterMembers();
    extractUniqueStatuses();
    extractUniqueRegions();
  }, [members, searchTerm, statusFilter, regionFilter]);

  const extractUniqueStatuses = () => {
    const statuses = [...new Set(members.map(member => member.status).filter(Boolean))];
    setUniqueStatuses(statuses.sort());
  };

  const extractUniqueRegions = () => {
    const regions = [...new Set(members.map(member => member.regio).filter(Boolean))];
    setUniqueRegions(regions.sort());
  };

  const loadMembers = async () => {
    try {
      const response = await fetch('https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/members');
      if (response.ok) {
        const data = await response.json();
        setMembers(data);
      }
    } catch (error) {
      toast({
        title: 'Fout bij laden leden',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };



  const filterMembers = () => {
    let filtered = members;

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

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'green';
      case 'inactive': return 'red';
      case 'pending': return 'yellow';
      default: return 'gray';
    }
  };

  const handleViewMember = (member) => {
    setSelectedMember(member);
    setIsDetailModalOpen(true);
  };

  const handleEditMember = (member) => {
    setSelectedMember(member);
    setIsEditModalOpen(true);
  };



  const handleDeleteMember = async (member) => {
    try {
      const response = await fetch(`https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/members/${member.member_id}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await loadMembers();
        toast({
          title: 'Lid verwijderd',
          status: 'success',
          duration: 3000,
        });
      } else {
        const errorText = await response.text();
        throw new Error(`API Error ${response.status}: ${errorText}`);
      }
    } catch (error) {
      toast({
        title: 'Fout bij verwijderen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleMemberUpdate = async (updatedMember) => {
    try {
      const response = await fetch(`https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/members/${updatedMember.member_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedMember)
      });

      if (response.ok) {
        await loadMembers();
        toast({
          title: 'Lid bijgewerkt',
          status: 'success',
          duration: 3000,
        });
      } else {
        const errorText = await response.text();
        throw new Error(`API Error ${response.status}: ${errorText}`);
      }
    } catch (error) {
      toast({
        title: 'Fout bij bijwerken',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
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
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Cognito Beheer
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel p={0} pt={6}>
              <VStack spacing={6} align="stretch">

                {/* Filters */}
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
                      {member.lidmaatschap || member.membership_type}
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
                          <IconButton
                            size="xs"
                            colorScheme="blue"
                            icon={<ViewIcon />}
                            onClick={() => handleViewMember(member)}
                            title="Bekijk"
                          />
                          <IconButton
                            size="xs"
                            colorScheme="orange"
                            icon={<EditIcon />}
                            onClick={() => handleEditMember(member)}
                            title="Bewerk"
                          />
                        </HStack>
                      ) : (
                        <HStack spacing={2}>
                          <Button
                            size="sm"
                            colorScheme="blue"
                            leftIcon={<ViewIcon />}
                            onClick={() => handleViewMember(member)}
                          >
                            Bekijk
                          </Button>
                          <Button
                            size="sm"
                            colorScheme="orange"
                            leftIcon={<EditIcon />}
                            onClick={() => handleEditMember(member)}
                          >
                            Bewerk
                          </Button>
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
            <TabPanel p={0} pt={6}>
              <CognitoAdminPage user={user} />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>

      {/* Modals */}
      <MemberDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        member={selectedMember}
      />

      <MemberEditModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        member={selectedMember}
        onSave={handleMemberUpdate}
      />


    </Box>
  );
}

export default MemberAdminPage;