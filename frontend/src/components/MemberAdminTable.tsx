/**
 * Member Admin Table - Using Field Registry System
 * 
 * Dynamic member table with context switching and field registry integration
 */

import React, { useState, useMemo } from 'react';
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
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  Flex,
  Spacer,
  Card,
  CardHeader,
  CardBody,
  Tooltip,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useDisclosure
} from '@chakra-ui/react';
import { 
  ViewIcon, 
  EditIcon, 
  SearchIcon, 
  DownloadIcon,
  ChevronDownIcon,
  SettingsIcon
} from '@chakra-ui/icons';
import { MEMBER_TABLE_CONTEXTS, MEMBER_FIELDS, HDCNGroup } from '../config/memberFields';
import { resolveFieldsForContext, canViewField, canEditField } from '../utils/fieldResolver';
import { renderFieldValue } from '../utils/fieldRenderers';
import { canPerformAction, hasRegionalAccess } from '../utils/permissionHelpers';

interface MemberAdminTableProps {
  members: any[];
  userRole: HDCNGroup;
  userRegion?: string;
  onMemberView: (member: any) => void;
  onMemberEdit: (member: any) => void;
  onMemberDelete?: (member: any) => void;
  onExport?: (context: string) => void;
}

const MemberAdminTable: React.FC<MemberAdminTableProps> = ({
  members,
  userRole,
  userRegion,
  onMemberView,
  onMemberEdit,
  onMemberDelete,
  onExport
}) => {
  const [selectedContext, setSelectedContext] = useState('memberOverview');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState('achternaam');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Get available contexts based on user permissions
  const availableContexts = useMemo(() => {
    return Object.entries(MEMBER_TABLE_CONTEXTS).filter(([key, context]) => 
      context.permissions.view.includes(userRole)
    );
  }, [userRole]);

  // Get current table context
  const tableContext = MEMBER_TABLE_CONTEXTS[selectedContext];

  // Filter members based on regional restrictions and search
  const filteredMembers = useMemo(() => {
    let filtered = members;

    // Apply regional filtering if needed
    if (tableContext.regionalRestricted && userRole === 'Members_Read_All' && userRegion) {
      filtered = filtered.filter(member => member.regio === userRegion);
    }

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(member => {
        const searchFields = ['voornaam', 'achternaam', 'email', 'lidnummer'];
        return searchFields.some(field => 
          member[field]?.toString().toLowerCase().includes(searchTerm.toLowerCase())
        );
      });
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const aValue = a[sortField] || '';
      const bValue = b[sortField] || '';
      
      if (sortDirection === 'asc') {
        return aValue.toString().localeCompare(bValue.toString());
      } else {
        return bValue.toString().localeCompare(aValue.toString());
      }
    });

    return filtered;
  }, [members, tableContext, userRole, userRegion, searchTerm, sortField, sortDirection]);

  // Get visible columns based on context and permissions
  const visibleColumns = useMemo(() => {
    return tableContext.columns
      .filter(col => col.visible)
      .filter(col => {
        const field = MEMBER_FIELDS[col.fieldKey];
        return field && canViewField(field, userRole, filteredMembers[0]);
      })
      .sort((a, b) => a.order - b.order);
  }, [tableContext, userRole, filteredMembers]);

  const handleSort = (fieldKey: string) => {
    if (sortField === fieldKey) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(fieldKey);
      setSortDirection('asc');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Actief': return 'green';
      case 'Aangemeld': return 'yellow';
      case 'Opgezegd': return 'red';
      case 'Geschorst': return 'red';
      case 'wachtRegio': return 'orange';
      default: return 'gray';
    }
  };

  const getMembershipColor = (membership: string) => {
    switch (membership) {
      case 'Gewoon lid': return 'blue';
      case 'Gezins lid': return 'purple';
      case 'Erelid': return 'gold';
      case 'Donateur': return 'teal';
      case 'Gezins donateur': return 'teal';
      case 'Sponsor': return 'orange';
      default: return 'gray';
    }
  };

  const renderCellValue = (field: any, value: any, member: any) => {
    const renderedValue = renderFieldValue(field, value);
    
    if (field.key === 'status') {
      return (
        <Badge colorScheme={getStatusColor(value)} size="sm">
          {renderedValue}
        </Badge>
      );
    }
    
    if (field.key === 'lidmaatschap') {
      return (
        <Badge colorScheme={getMembershipColor(value)} size="sm">
          {renderedValue}
        </Badge>
      );
    }
    
    if (field.key === 'bankrekeningnummer' && value) {
      // Mask IBAN for table display
      return (
        <Text fontSize="sm" fontFamily="mono">
          {value.replace(/(.{4})(.*)(.{4})/, '$1****$3')}
        </Text>
      );
    }
    
    return (
      <Text fontSize="sm" isTruncated maxW="150px">
        {renderedValue}
      </Text>
    );
  };

  return (
    <Box>
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <Card>
          <CardHeader>
            <Flex align="center">
              <VStack align="start" spacing={1}>
                <Heading size="lg" color="orange.500">
                  Ledenadministratie
                </Heading>
                <Text color="gray.600">
                  {filteredMembers.length} van {members.length} leden
                </Text>
              </VStack>
              <Spacer />
              <HStack>
                {onExport && tableContext.exportable && (
                  <Button
                    leftIcon={<DownloadIcon />}
                    variant="outline"
                    onClick={() => onExport(selectedContext)}
                  >
                    Exporteren
                  </Button>
                )}
              </HStack>
            </Flex>
          </CardHeader>
        </Card>

        {/* Controls */}
        <Card>
          <CardBody>
            <HStack spacing={4} wrap="wrap">
              {/* Context Selector */}
              <Box minW="200px">
                <Text fontSize="sm" fontWeight="semibold" mb={2}>
                  Tabelweergave:
                </Text>
                <Select 
                  value={selectedContext} 
                  onChange={(e) => setSelectedContext(e.target.value)}
                  size="sm"
                >
                  {availableContexts.map(([key, context]) => (
                    <option key={key} value={key}>
                      {context.name}
                    </option>
                  ))}
                </Select>
              </Box>

              {/* Search */}
              <Box flex="1" minW="200px">
                <Text fontSize="sm" fontWeight="semibold" mb={2}>
                  Zoeken:
                </Text>
                <InputGroup size="sm">
                  <InputLeftElement>
                    <SearchIcon color="gray.400" />
                  </InputLeftElement>
                  <Input
                    placeholder="Zoek op naam, email of lidnummer..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </InputGroup>
              </Box>

              {/* Context Info */}
              <Box>
                <Text fontSize="sm" fontWeight="semibold" mb={2}>
                  Context:
                </Text>
                <Text fontSize="sm" color="gray.600">
                  {tableContext.description}
                </Text>
              </Box>
            </HStack>
          </CardBody>
        </Card>

        {/* Table */}
        <Card>
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead bg="gray.50">
                <Tr>
                  <Th minW="120px" position="sticky" left={0} bg="gray.50" zIndex={1}>
                    Acties
                  </Th>
                  {visibleColumns.map(column => {
                    const field = MEMBER_FIELDS[column.fieldKey];
                    if (!field) return null;
                    
                    return (
                      <Th 
                        key={column.fieldKey}
                        minW={column.width || '120px'}
                        cursor={column.sortable ? 'pointer' : 'default'}
                        onClick={column.sortable ? () => handleSort(column.fieldKey) : undefined}
                        _hover={column.sortable ? { bg: 'gray.100' } : {}}
                      >
                        <HStack spacing={1}>
                          <Text>{field.label}</Text>
                          {column.sortable && sortField === column.fieldKey && (
                            <Text fontSize="xs">
                              {sortDirection === 'asc' ? '↑' : '↓'}
                            </Text>
                          )}
                        </HStack>
                      </Th>
                    );
                  })}
                </Tr>
              </Thead>
              <Tbody>
                {filteredMembers.map((member) => (
                  <Tr key={member.member_id} _hover={{ bg: 'gray.50' }}>
                    <Td position="sticky" left={0} bg="white" zIndex={1}>
                      <HStack spacing={1}>
                        <Tooltip label="Bekijken">
                          <IconButton
                            aria-label="View member"
                            icon={<ViewIcon />}
                            size="xs"
                            colorScheme="blue"
                            onClick={() => onMemberView(member)}
                          />
                        </Tooltip>
                        {canPerformAction('edit', userRole, member, userRegion) && (
                          <Tooltip label="Bewerken">
                            <IconButton
                              aria-label="Edit member"
                              icon={<EditIcon />}
                              size="xs"
                              colorScheme="orange"
                              onClick={() => onMemberEdit(member)}
                            />
                          </Tooltip>
                        )}
                      </HStack>
                    </Td>
                    {visibleColumns.map(column => {
                      const field = MEMBER_FIELDS[column.fieldKey];
                      if (!field) return null;
                      
                      const value = member[column.fieldKey];
                      
                      return (
                        <Td key={column.fieldKey} textAlign={column.align || 'left'}>
                          {renderCellValue(field, value, member)}
                        </Td>
                      );
                    })}
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        </Card>

        {/* Footer */}
        {filteredMembers.length === 0 && (
          <Card>
            <CardBody textAlign="center" py={8}>
              <Text color="gray.500">
                Geen leden gevonden die voldoen aan de criteria.
              </Text>
            </CardBody>
          </Card>
        )}
      </VStack>
    </Box>
  );
};

export default MemberAdminTable;