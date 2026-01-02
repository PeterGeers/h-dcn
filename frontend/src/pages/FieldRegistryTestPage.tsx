/**
 * Field Registry Test Page
 * 
 * Comprehensive test page for the field registry system integrated with HDCN portal
 * Shows table views, modal contexts, and field resolution testing
 */

import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Select,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Alert,
  AlertIcon,
  Code,
  Divider,
  Flex,
  Spacer,
  IconButton,
  Tooltip
} from '@chakra-ui/react';
import { ViewIcon, EditIcon, InfoIcon } from '@chakra-ui/icons';
import { resolveFieldsForContext, canViewField, canEditField } from '../utils/fieldResolver';
import { renderFieldValue, getFieldInputComponent, validateFieldValue } from '../utils/fieldRenderers';
import { canPerformAction, hasRegionalAccess, getRoleName } from '../utils/permissionHelpers';
import { HDCNGroup, MEMBER_TABLE_CONTEXTS, MEMBER_MODAL_CONTEXTS } from '../config/memberFields';

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

interface FieldRegistryTestPageProps {
  user: User;
}

const FieldRegistryTestPage: React.FC<FieldRegistryTestPageProps> = ({ user }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedContext, setSelectedContext] = useState('memberOverview');
  const [selectedRole, setSelectedRole] = useState<HDCNGroup>('System_CRUD_All');
  const [userRegion, setUserRegion] = useState('Noord-Holland');
  const [selectedMember, setSelectedMember] = useState<any>(null);
  const [modalContext, setModalContext] = useState('memberView');

  // Sample member data for testing
  const sampleMembers = [
    {
      member_id: '1',
      lidnummer: 1001,
      voornaam: 'Jan',
      tussenvoegsel: 'de',
      achternaam: 'Vries',
      email: 'jan.devries@example.com',
      telefoon: '06-12345678',
      geboortedatum: '1990-05-15',
      geslacht: 'Man',
      straat: 'Hoofdstraat 123',
      postcode: '1234AB',
      woonplaats: 'Amsterdam',
      land: 'Nederland',
      lidmaatschap: 'Gewoon lid',
      status: 'Actief',
      regio: 'Noord-Holland',
      motormerk: 'Harley-Davidson',
      motortype: 'Street Glide',
      bouwjaar: 2020,
      kenteken: 'AB-123-CD',
      bankrekeningnummer: 'NL91ABNA0417164300',
      betaalwijze: 'Automatische incasso',
      privacy: 'Ja',
      clubblad: 'Digitaal',
      nieuwsbrief: 'Ja',
      tijdstempel: '2020-01-15',
      created_at: '2020-01-15T10:00:00Z',
      updated_at: '2024-12-01T15:30:00Z'
    },
    {
      member_id: '2',
      lidnummer: 1002,
      voornaam: 'Maria',
      achternaam: 'Jansen',
      email: 'maria.jansen@example.com',
      telefoon: '06-87654321',
      geboortedatum: '1985-08-22',
      geslacht: 'Vrouw',
      straat: 'Kerkstraat 45',
      postcode: '5678CD',
      woonplaats: 'Utrecht',
      land: 'Nederland',
      lidmaatschap: 'Gezins lid',
      status: 'Actief',
      regio: 'Utrecht',
      motormerk: 'BMW',
      motortype: 'R1250GS',
      bouwjaar: 2019,
      kenteken: 'EF-456-GH',
      bankrekeningnummer: 'NL12RABO0123456789',
      betaalwijze: 'Automatische incasso',
      privacy: 'Nee',
      clubblad: 'Papier',
      nieuwsbrief: 'Ja',
      tijdstempel: '2019-03-10',
      created_at: '2019-03-10T14:20:00Z',
      updated_at: '2024-11-15T09:45:00Z'
    },
    {
      member_id: '3',
      lidnummer: null,
      voornaam: 'Peter',
      achternaam: 'Bakker',
      email: 'peter.bakker@example.com',
      telefoon: '06-11223344',
      geboortedatum: '1995-12-03',
      geslacht: 'Man',
      straat: 'Dorpsstraat 78',
      postcode: '9876ZX',
      woonplaats: 'Groningen',
      land: 'Nederland',
      lidmaatschap: 'Donateur',
      status: 'Aangemeld',
      regio: 'Groningen/Drenthe',
      bankrekeningnummer: 'NL34INGB0987654321',
      betaalwijze: 'Handmatige overmaking',
      privacy: 'Ja',
      clubblad: 'Digitaal',
      nieuwsbrief: 'Ja',
      tijdstempel: '2024-12-01',
      created_at: '2024-12-01T12:00:00Z',
      updated_at: '2024-12-01T12:00:00Z'
    }
  ];

  const contexts = [
    'memberOverview',
    'memberCompact', 
    'motorView',
    'communicationView',
    'financialView'
  ];

  const modalContexts = [
    'memberView',
    'memberQuickView',
    'memberRegistration',
    'membershipApplication'
  ];

  const roles: HDCNGroup[] = [
    'System_CRUD_All',
    'Members_CRUD_All',
    'Members_Read_All',
    'System_User_Management',
    'hdcnLeden'
  ];

  const regions = [
    'Noord-Holland',
    'Zuid-Holland', 
    'Friesland',
    'Utrecht',
    'Oost',
    'Limburg',
    'Groningen/Drenthe',
    'Noord-Brabant',
    'Zeeland'
  ];

  const resolvedFields = resolveFieldsForContext(selectedContext, selectedRole, sampleMembers[0]);
  const tableContext = MEMBER_TABLE_CONTEXTS[selectedContext];

  const openMemberModal = (member: any) => {
    setSelectedMember(member);
    onOpen();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Actief': return 'green';
      case 'Aangemeld': return 'yellow';
      case 'Inactief': return 'red';
      default: return 'gray';
    }
  };

  const getMembershipColor = (membership: string) => {
    switch (membership) {
      case 'Gewoon lid': return 'blue';
      case 'Gezins lid': return 'purple';
      case 'Erelid': return 'gold';
      case 'Donateur': return 'teal';
      default: return 'gray';
    }
  };

  return (
    <Box maxW="1400px" mx="auto" p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box textAlign="center">
          <Heading color="orange.500" mb={2}>
            🧪 Field Registry Test Portal
          </Heading>
          <Text color="gray.600">
            Test the complete field registry system with table views and modal contexts
          </Text>
        </Box>

        {/* Controls */}
        <Card>
          <CardHeader>
            <Heading size="md">Test Configuration</Heading>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
              <Box>
                <Text mb={2} fontWeight="semibold">Table Context:</Text>
                <Select 
                  value={selectedContext} 
                  onChange={(e) => setSelectedContext(e.target.value)}
                  bg="white"
                >
                  {contexts.map(context => (
                    <option key={context} value={context}>{context}</option>
                  ))}
                </Select>
              </Box>
              
              <Box>
                <Text mb={2} fontWeight="semibold">User Role:</Text>
                <Select 
                  value={selectedRole} 
                  onChange={(e) => setSelectedRole(e.target.value as HDCNGroup)}
                  bg="white"
                >
                  {roles.map(role => (
                    <option key={role} value={role}>{getRoleName(role)}</option>
                  ))}
                </Select>
              </Box>

              <Box>
                <Text mb={2} fontWeight="semibold">User Region:</Text>
                <Select 
                  value={userRegion} 
                  onChange={(e) => setUserRegion(e.target.value)}
                  bg="white"
                >
                  {regions.map(region => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </Select>
              </Box>
            </SimpleGrid>
          </CardBody>
        </Card>

        {/* Statistics */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Stat>
            <StatLabel>Resolved Fields</StatLabel>
            <StatNumber color="blue.500">{resolvedFields.length}</StatNumber>
            <StatHelpText>For current context</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Viewable Fields</StatLabel>
            <StatNumber color="green.500">
              {resolvedFields.filter(f => canViewField(f, selectedRole, sampleMembers[0])).length}
            </StatNumber>
            <StatHelpText>With current role</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Editable Fields</StatLabel>
            <StatNumber color="orange.500">
              {resolvedFields.filter(f => canEditField(f, selectedRole, sampleMembers[0])).length}
            </StatNumber>
            <StatHelpText>With current role</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Sample Members</StatLabel>
            <StatNumber color="purple.500">{sampleMembers.length}</StatNumber>
            <StatHelpText>Test data available</StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Main Content Tabs */}
        <Tabs variant="enclosed" colorScheme="orange">
          <TabList>
            <Tab>📊 Table View</Tab>
            <Tab>🔍 Field Details</Tab>
            <Tab>⚙️ Context Info</Tab>
            <Tab>🔐 Permissions</Tab>
          </TabList>

          <TabPanels>
            {/* Table View Tab */}
            <TabPanel>
              <VStack spacing={4} align="stretch">
                <Flex>
                  <Heading size="md">Members Table - {selectedContext}</Heading>
                  <Spacer />
                  <Text fontSize="sm" color="gray.600">
                    Click on a member to open modal view
                  </Text>
                </Flex>
                
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Actions</Th>
                        {resolvedFields
                          .filter(f => canViewField(f, selectedRole, sampleMembers[0]))
                          .slice(0, 8) // Limit columns for display
                          .map(field => (
                            <Th key={field.key}>{field.label}</Th>
                          ))}
                      </Tr>
                    </Thead>
                    <Tbody>
                      {sampleMembers.map(member => (
                        <Tr key={member.member_id} _hover={{ bg: 'gray.50' }}>
                          <Td>
                            <HStack spacing={1}>
                              <Tooltip label="View Details">
                                <IconButton
                                  aria-label="View member"
                                  icon={<ViewIcon />}
                                  size="xs"
                                  colorScheme="blue"
                                  onClick={() => openMemberModal(member)}
                                />
                              </Tooltip>
                              {canEditField(resolvedFields[0], selectedRole, member) && (
                                <Tooltip label="Edit Member">
                                  <IconButton
                                    aria-label="Edit member"
                                    icon={<EditIcon />}
                                    size="xs"
                                    colorScheme="orange"
                                    onClick={() => {
                                      setModalContext('memberView');
                                      openMemberModal(member);
                                    }}
                                  />
                                </Tooltip>
                              )}
                            </HStack>
                          </Td>
                          {resolvedFields
                            .filter(f => canViewField(f, selectedRole, member))
                            .slice(0, 8)
                            .map(field => {
                              const value = member[field.key as keyof typeof member];
                              const renderedValue = renderFieldValue(field, value);
                              
                              return (
                                <Td key={field.key}>
                                  {field.key === 'status' ? (
                                    <Badge colorScheme={getStatusColor(value as string)}>
                                      {renderedValue}
                                    </Badge>
                                  ) : field.key === 'lidmaatschap' ? (
                                    <Badge colorScheme={getMembershipColor(value as string)}>
                                      {renderedValue}
                                    </Badge>
                                  ) : (
                                    <Text fontSize="sm" noOfLines={1}>
                                      {renderedValue}
                                    </Text>
                                  )}
                                </Td>
                              );
                            })}
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </VStack>
            </TabPanel>

            {/* Field Details Tab */}
            <TabPanel>
              <VStack spacing={4} align="stretch">
                <Heading size="md">Field Resolution Details</Heading>
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Field Key</Th>
                        <Th>Label</Th>
                        <Th>Type</Th>
                        <Th>Group</Th>
                        <Th>View</Th>
                        <Th>Edit</Th>
                        <Th>Sample Value</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {resolvedFields.map(field => {
                        const sampleValue = sampleMembers[0][field.key as keyof typeof sampleMembers[0]];
                        const renderedValue = renderFieldValue(field, sampleValue);
                        
                        return (
                          <Tr key={field.key}>
                            <Td><Code fontSize="xs">{field.key}</Code></Td>
                            <Td>{field.label}</Td>
                            <Td>
                              <Badge size="sm" colorScheme="blue">
                                {field.dataType}
                              </Badge>
                            </Td>
                            <Td>
                              <Badge size="sm" colorScheme="purple">
                                {field.group}
                              </Badge>
                            </Td>
                            <Td>
                              {canViewField(field, selectedRole, sampleMembers[0]) ? '✅' : '❌'}
                            </Td>
                            <Td>
                              {canEditField(field, selectedRole, sampleMembers[0]) ? '✅' : '❌'}
                            </Td>
                            <Td>
                              <Code fontSize="xs" bg="gray.100">
                                {renderedValue}
                              </Code>
                            </Td>
                          </Tr>
                        );
                      })}
                    </Tbody>
                  </Table>
                </Box>
              </VStack>
            </TabPanel>

            {/* Context Info Tab */}
            <TabPanel>
              <VStack spacing={4} align="stretch">
                <Heading size="md">Context Configuration</Heading>
                {tableContext && (
                  <Card>
                    <CardHeader>
                      <Heading size="sm">{tableContext.name}</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack align="stretch" spacing={3}>
                        <Text><strong>Description:</strong> {tableContext.description}</Text>
                        <Text><strong>Total Columns:</strong> {tableContext.columns.length}</Text>
                        <Text><strong>Visible Columns:</strong> {tableContext.columns.filter(c => c.visible).length}</Text>
                        <Text><strong>Sortable Columns:</strong> {tableContext.columns.filter(c => c.sortable).length}</Text>
                        <Text><strong>Filterable Columns:</strong> {tableContext.columns.filter(c => c.filterable).length}</Text>
                        <Divider />
                        <Text><strong>View Permissions:</strong></Text>
                        <HStack wrap="wrap">
                          {tableContext.permissions.view.map(role => (
                            <Badge key={role} colorScheme="green">{role}</Badge>
                          ))}
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>
                )}
              </VStack>
            </TabPanel>

            {/* Permissions Tab */}
            <TabPanel>
              <VStack spacing={4} align="stretch">
                <Heading size="md">Permission Analysis</Heading>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  <Card>
                    <CardHeader>
                      <Heading size="sm">Current User Permissions</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack align="stretch" spacing={2}>
                        <Text>
                          <strong>Can View Members:</strong> {' '}
                          {canPerformAction('view', selectedRole, sampleMembers[0], userRegion) ? '✅' : '❌'}
                        </Text>
                        <Text>
                          <strong>Can Edit Members:</strong> {' '}
                          {canPerformAction('edit', selectedRole, sampleMembers[0], userRegion) ? '✅' : '❌'}
                        </Text>
                        <Text>
                          <strong>Can Delete Members:</strong> {' '}
                          {canPerformAction('delete', selectedRole, sampleMembers[0], userRegion) ? '✅' : '❌'}
                        </Text>
                        <Text>
                          <strong>Regional Access:</strong> {' '}
                          {hasRegionalAccess(selectedRole, sampleMembers[0].regio, userRegion) ? '✅' : '❌'}
                        </Text>
                      </VStack>
                    </CardBody>
                  </Card>
                  
                  <Card>
                    <CardHeader>
                      <Heading size="sm">Role Information</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack align="stretch" spacing={2}>
                        <Text><strong>Selected Role:</strong> {getRoleName(selectedRole)}</Text>
                        <Text><strong>User Region:</strong> {userRegion}</Text>
                        <Text><strong>Test Member Region:</strong> {sampleMembers[0].regio}</Text>
                        <Divider />
                        <Text fontSize="sm" color="gray.600">
                          Regional restrictions apply to Members_Read_All role only
                        </Text>
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>

        {/* Member Modal */}
        <Modal isOpen={isOpen} onClose={onClose} size="6xl">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>
              <HStack>
                <Text>Member Details - {selectedMember?.voornaam} {selectedMember?.achternaam}</Text>
                <Spacer />
                <Select 
                  value={modalContext} 
                  onChange={(e) => setModalContext(e.target.value)}
                  size="sm"
                  w="200px"
                >
                  {modalContexts.map(context => (
                    <option key={context} value={context}>{context}</option>
                  ))}
                </Select>
              </HStack>
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              {selectedMember && (
                <VStack spacing={4} align="stretch">
                  <Alert status="info">
                    <AlertIcon />
                    <Text fontSize="sm">
                      Showing modal context: <strong>{modalContext}</strong> with role: <strong>{getRoleName(selectedRole)}</strong>
                    </Text>
                  </Alert>
                  
                  {/* Modal field rendering would go here */}
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                    {resolvedFields
                      .filter(f => canViewField(f, selectedRole, selectedMember))
                      .slice(0, 12) // Limit for modal display
                      .map(field => {
                        const value = selectedMember[field.key as keyof typeof selectedMember];
                        const renderedValue = renderFieldValue(field, value);
                        const canEdit = canEditField(field, selectedRole, selectedMember);
                        
                        return (
                          <Card key={field.key} size="sm">
                            <CardBody>
                              <VStack align="stretch" spacing={2}>
                                <HStack>
                                  <Text fontSize="sm" fontWeight="semibold" color="gray.600">
                                    {field.label}
                                  </Text>
                                  <Spacer />
                                  {canEdit && <Badge colorScheme="orange" size="sm">Editable</Badge>}
                                </HStack>
                                <Text fontSize="md">
                                  {field.key === 'status' ? (
                                    <Badge colorScheme={getStatusColor(value as string)}>
                                      {renderedValue}
                                    </Badge>
                                  ) : field.key === 'lidmaatschap' ? (
                                    <Badge colorScheme={getMembershipColor(value as string)}>
                                      {renderedValue}
                                    </Badge>
                                  ) : (
                                    renderedValue
                                  )}
                                </Text>
                                <Text fontSize="xs" color="gray.500">
                                  {field.group} • {field.dataType}
                                </Text>
                              </VStack>
                            </CardBody>
                          </Card>
                        );
                      })}
                  </SimpleGrid>
                </VStack>
              )}
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="blue" mr={3} onClick={onClose}>
                Close
              </Button>
              {selectedMember && canEditField(resolvedFields[0], selectedRole, selectedMember) && (
                <Button colorScheme="orange">
                  Edit Member
                </Button>
              )}
            </ModalFooter>
          </ModalContent>
        </Modal>
      </VStack>
    </Box>
  );
};

export default FieldRegistryTestPage;