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
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useDisclosure,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverHeader,
  PopoverBody,
  PopoverCloseButton,
  FormControl,
  FormLabel,
  Collapse,
  useColorModeValue
} from '@chakra-ui/react';
import { 
  SearchIcon, 
  DownloadIcon,
  ChevronDownIcon,
  SettingsIcon,
  ChevronUpIcon,
  AddIcon
} from '@chakra-ui/icons';
import { MEMBER_TABLE_CONTEXTS, MEMBER_FIELDS, HDCNGroup, getFilteredEnumOptions } from '../config/memberFields';
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
  onAddMember?: () => void; // Add this prop
}

const MemberAdminTable: React.FC<MemberAdminTableProps> = ({
  members,
  userRole,
  userRegion,
  onMemberView,
  onMemberEdit,
  onMemberDelete,
  onExport,
  onAddMember
}) => {
  const [selectedContext, setSelectedContext] = useState('memberCompact'); // Changed to memberCompact
  const [sortField, setSortField] = useState('achternaam');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>({});

  const filterBg = useColorModeValue('gray.50', 'gray.700');

  // Get available contexts based on user permissions
  const availableContexts = useMemo(() => {
    return Object.entries(MEMBER_TABLE_CONTEXTS).filter(([key, context]) => 
      context.permissions.view.includes(userRole)
    );
  }, [userRole]);

  // Get current table context
  const tableContext = MEMBER_TABLE_CONTEXTS[selectedContext];

  // Filter members based on regional restrictions and column filters
  const filteredMembers = useMemo(() => {
    let filtered = members;

    // Apply regional filtering if needed
    if (tableContext?.regionalRestricted && userRole === 'Members_Read_All' && userRegion) {
      filtered = filtered.filter(member => member.regio === userRegion);
    }

    // Apply column-specific filters
    Object.entries(columnFilters).forEach(([fieldKey, filterValue]) => {
      if (filterValue) {
        if (fieldKey === 'fullName') {
          // Special handling for full name filter (mobile)
          filtered = filtered.filter(member => {
            const fullName = [member.voornaam, member.tussenvoegsel, member.achternaam]
              .filter(Boolean)
              .join(' ')
              .toLowerCase();
            return fullName.includes(filterValue.toLowerCase());
          });
        } else {
          const field = MEMBER_FIELDS[fieldKey];
          if (field) {
            filtered = filtered.filter(member => {
              const memberValue = member[fieldKey];
              
              if (field.inputType === 'select' || field.dataType === 'enum') {
                return memberValue === filterValue;
              } else if (field.dataType === 'date') {
                // For date filters, you might want more sophisticated logic
                return memberValue?.toString().includes(filterValue);
              } else if (field.dataType === 'number') {
                return memberValue?.toString() === filterValue;
              } else {
                // Text filter
                return memberValue?.toString().toLowerCase().includes(filterValue.toLowerCase());
              }
            });
          }
        }
      }
    });

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
  }, [members, tableContext?.regionalRestricted, userRole, userRegion, columnFilters, sortField, sortDirection]);

  // Get visible columns based on context and permissions
  const visibleColumns = useMemo(() => {
    if (!tableContext) return [];
    
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

  const handleColumnFilter = (fieldKey: string, value: string) => {
    setColumnFilters(prev => ({
      ...prev,
      [fieldKey]: value
    }));
  };

  const clearAllFilters = () => {
    setColumnFilters({});
  };

  const getFilterOptions = (fieldKey: string) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (field?.enumOptions) {
      // Use filtered enum options based on user role
      return getFilteredEnumOptions(field, userRole);
    }
    
    // For non-enum fields, get unique values from data
    const uniqueValues = [...new Set(members.map(m => m[fieldKey]).filter(Boolean))];
    return uniqueValues.sort();
  };

  const renderColumnFilter = (column: any) => {
    const field = MEMBER_FIELDS[column.fieldKey];
    if (!field || !column.filterable) return null;

    const filterValue = columnFilters[column.fieldKey] || '';

    if (column.filterType === 'select') {
      const options = getFilterOptions(column.fieldKey);
      return (
        <Select
          size="xs"
          placeholder="Alle"
          value={filterValue}
          onChange={(e) => handleColumnFilter(column.fieldKey, e.target.value)}
          bg="white"
          color="black"
          maxW="120px"
          fontSize={{ base: "xs", md: "sm" }}
        >
          {options.map(option => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </Select>
      );
    } else if (column.filterType === 'text') {
      return (
        <Input
          size="xs"
          placeholder="Filter..."
          value={filterValue}
          onChange={(e) => handleColumnFilter(column.fieldKey, e.target.value)}
          bg="white"
          color="black"
          maxW="120px"
          fontSize={{ base: "xs", md: "sm" }}
        />
      );
    } else if (column.filterType === 'number') {
      return (
        <Input
          size="xs"
          type="number"
          placeholder="Nr..."
          value={filterValue}
          onChange={(e) => handleColumnFilter(column.fieldKey, e.target.value)}
          bg="white"
          color="black"
          maxW="120px"
          fontSize={{ base: "xs", md: "sm" }}
        />
      );
    } else if (column.filterType === 'date') {
      return (
        <Input
          size="xs"
          type="date"
          value={filterValue}
          onChange={(e) => handleColumnFilter(column.fieldKey, e.target.value)}
          bg="white"
          color="black"
          maxW="120px"
          fontSize={{ base: "xs", md: "sm" }}
        />
      );
    }

    return null;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Actief': return 'green';
      case 'Aangemeld': return 'yellow';
      case 'Opgezegd': return 'red';
      case 'Geschorst': return 'red';
      case 'wachtRegio': return 'orange';
      case 'HdcnAccount': return 'purple';
      case 'Club': return 'blue';
      case 'Sponsor': return 'teal';
      case 'Overig': return 'gray';
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
        {/* Controls */}
        <Card bg="gray.800" borderColor="orange.400" border="1px">
          <CardBody bg="orange.300" borderRadius="0 0 lg lg">
            <Flex align="start" wrap="wrap" gap={4} direction={{ base: "column", md: "row" }}>
              {/* Mobile Context Selector */}
              <VStack spacing={2} align="start" w="full" display={{ base: "flex", md: "none" }}>
                <Text fontSize="sm" fontWeight="semibold" color="gray.700">
                  Tabelweergave:
                </Text>
                <Select 
                  value={selectedContext} 
                  onChange={(e) => setSelectedContext(e.target.value)}
                  size="sm"
                  bg="white"
                  color="black"
                  w="full"
                >
                  {availableContexts.map(([key, context]) => (
                    <option key={key} value={key}>
                      {context.name}
                    </option>
                  ))}
                </Select>
              </VStack>

              {/* Desktop Context Selector */}
              <HStack spacing={4} display={{ base: "none", md: "flex" }}>
                <Box minW="200px">
                  <Text fontSize="sm" fontWeight="semibold" mb={2} color="gray.700">
                    Tabelweergave:
                  </Text>
                  <Select 
                    value={selectedContext} 
                    onChange={(e) => setSelectedContext(e.target.value)}
                    size="sm"
                    bg="white"
                    color="black"
                  >
                    {availableContexts.map(([key, context]) => (
                      <option key={key} value={key}>
                        {context.name}
                      </option>
                    ))}
                  </Select>
                </Box>

                {/* Add Member Button */}
                {onAddMember && ['System_CRUD_All', 'Members_CRUD_All'].includes(userRole) && (
                  <Button
                    leftIcon={<AddIcon />}
                    colorScheme="orange"
                    onClick={onAddMember}
                    bg="orange.500"
                    color="white"
                    _hover={{ bg: "orange.600" }}
                  >
                    Nieuw Lid
                  </Button>
                )}
              </HStack>

              <Spacer display={{ base: "none", md: "block" }} />

              {/* Mobile Statistics */}
              <VStack spacing={2} align="start" display={{ base: "flex", md: "none" }}>
                {(() => {
                  // Calculate status counts from filtered members
                  const statusCounts = {
                    'Actief': filteredMembers.filter(m => m.status === 'Actief').length,
                    'Aangemeld': filteredMembers.filter(m => m.status === 'Aangemeld').length,
                    'HdcnAccount': filteredMembers.filter(m => m.status === 'HdcnAccount').length,
                    'Club': filteredMembers.filter(m => m.status === 'Club').length,
                    'Sponsor': filteredMembers.filter(m => m.status === 'Sponsor').length,
                    'Opgezegd': filteredMembers.filter(m => m.status === 'Opgezegd').length,
                    'Geschorst': filteredMembers.filter(m => m.status === 'Geschorst').length,
                    'wachtRegio': filteredMembers.filter(m => m.status === 'wachtRegio').length,
                    'Overig': filteredMembers.filter(m => m.status === 'Overig').length
                  };

                  const statusColors = {
                    'Actief': 'green.700',
                    'Aangemeld': 'yellow.700',
                    'HdcnAccount': 'purple.700',
                    'Club': 'blue.700',
                    'Sponsor': 'teal.700',
                    'Opgezegd': 'red.700',
                    'Geschorst': 'red.700',
                    'wachtRegio': 'orange.700',
                    'Overig': 'gray.700'
                  };

                  // Filter out statuses with 0 count
                  const nonZeroStatuses = Object.entries(statusCounts).filter(([_, count]) => count > 0);
                  
                  // Group statuses into rows of 3
                  const statusRows = [];
                  for (let i = 0; i < nonZeroStatuses.length; i += 3) {
                    statusRows.push(nonZeroStatuses.slice(i, i + 3));
                  }

                  return (
                    <>
                      {/* Total count row */}
                      <HStack spacing={4} wrap="wrap">
                        <Text color="gray.700" fontSize="xs">
                          <Text as="span" fontWeight="semibold">{filteredMembers.length}</Text>/<Text as="span" fontWeight="semibold">{members.length}</Text> leden
                        </Text>
                        <Text color="gray.700" fontSize="xs">
                          Hoogste Lidnr: <Text as="span" fontWeight="semibold" color="blue.700">
                            {Math.max(...members.filter(m => m.lidnummer && !isNaN(m.lidnummer)).map(m => Number(m.lidnummer)), 0)}
                          </Text>
                        </Text>
                      </HStack>
                      
                      {/* Status rows */}
                      {statusRows.map((row, rowIndex) => (
                        <HStack key={rowIndex} spacing={4} wrap="wrap">
                          {row.map(([status, count]) => (
                            <Text key={status} color="gray.700" fontSize="xs">
                              {status}: <Text as="span" fontWeight="semibold" color={statusColors[status]}>{count}</Text>
                            </Text>
                          ))}
                        </HStack>
                      ))}
                    </>
                  );
                })()}
              </VStack>

              {/* Desktop Statistics */}
              <VStack spacing={2} align="start" display={{ base: "none", md: "flex" }}>
                {(() => {
                  // Calculate status counts from filtered members
                  const statusCounts = {
                    'Actief': filteredMembers.filter(m => m.status === 'Actief').length,
                    'Aangemeld': filteredMembers.filter(m => m.status === 'Aangemeld').length,
                    'HdcnAccount': filteredMembers.filter(m => m.status === 'HdcnAccount').length,
                    'Club': filteredMembers.filter(m => m.status === 'Club').length,
                    'Sponsor': filteredMembers.filter(m => m.status === 'Sponsor').length,
                    'Opgezegd': filteredMembers.filter(m => m.status === 'Opgezegd').length,
                    'Geschorst': filteredMembers.filter(m => m.status === 'Geschorst').length,
                    'wachtRegio': filteredMembers.filter(m => m.status === 'wachtRegio').length,
                    'Overig': filteredMembers.filter(m => m.status === 'Overig').length
                  };

                  const statusColors = {
                    'Actief': 'green.700',
                    'Aangemeld': 'yellow.700',
                    'HdcnAccount': 'purple.700',
                    'Club': 'blue.700',
                    'Sponsor': 'teal.700',
                    'Opgezegd': 'red.700',
                    'Geschorst': 'red.700',
                    'wachtRegio': 'orange.700',
                    'Overig': 'gray.700'
                  };

                  // Filter out statuses with 0 count
                  const nonZeroStatuses = Object.entries(statusCounts).filter(([_, count]) => count > 0);
                  
                  // Group statuses into rows of 4-5
                  const statusRows = [];
                  for (let i = 0; i < nonZeroStatuses.length; i += 4) {
                    statusRows.push(nonZeroStatuses.slice(i, i + 4));
                  }

                  return (
                    <>
                      {/* Total count row */}
                      <HStack spacing={6}>
                        <Text color="gray.700" fontSize="sm">
                          <Text as="span" fontWeight="semibold">{filteredMembers.length}</Text> van <Text as="span" fontWeight="semibold">{members.length}</Text> leden
                        </Text>
                        <Text color="gray.700" fontSize="sm">
                          Hoogste Lidnr: <Text as="span" fontWeight="semibold" color="blue.700">
                            {Math.max(...members.filter(m => m.lidnummer && !isNaN(m.lidnummer)).map(m => Number(m.lidnummer)), 0)}
                          </Text>
                        </Text>
                      </HStack>
                      
                      {/* Status rows */}
                      {statusRows.map((row, rowIndex) => (
                        <HStack key={rowIndex} spacing={6}>
                          {row.map(([status, count]) => (
                            <Text key={status} color="gray.700" fontSize="sm">
                              {status}: <Text as="span" fontWeight="semibold" color={statusColors[status]}>{count}</Text>
                            </Text>
                          ))}
                        </HStack>
                      ))}
                    </>
                  );
                })()}
              </VStack>
            </Flex>
          </CardBody>
        </Card>

        {/* Table */}
        <Card bg="gray.800" borderColor="orange.400" border="1px">
          <Box overflowX="auto">
            <Table variant="simple" size="xs">
              <Thead bg="gray.700">
                <Tr>
                  {/* Mobile Portrait: Only Lidnummer and Full Name */}
                  <Th 
                    py={2}
                    color="orange.300"
                    display={{ base: 'table-cell', md: 'none' }}
                    minW="60px"
                  >
                    <VStack spacing={1} align="start">
                      <Text fontSize="xs">Lidnr</Text>
                      <Box onClick={(e) => e.stopPropagation()}>
                        <Input
                          size="xs"
                          type="number"
                          placeholder="Nr..."
                          value={columnFilters['lidnummer'] || ''}
                          onChange={(e) => handleColumnFilter('lidnummer', e.target.value)}
                          bg="white"
                          color="black"
                          maxW="50px"
                          fontSize="xs"
                        />
                      </Box>
                    </VStack>
                  </Th>
                  <Th 
                    py={2}
                    color="orange.300"
                    display={{ base: 'table-cell', md: 'none' }}
                  >
                    <VStack spacing={1} align="start">
                      <Text fontSize="xs">Naam</Text>
                      <Box onClick={(e) => e.stopPropagation()}>
                        <Input
                          size="xs"
                          placeholder="Naam..."
                          value={columnFilters['fullName'] || ''}
                          onChange={(e) => handleColumnFilter('fullName', e.target.value)}
                          bg="white"
                          color="black"
                          maxW="120px"
                          fontSize="xs"
                        />
                      </Box>
                    </VStack>
                  </Th>
                  <Th 
                    py={2}
                    color="orange.300"
                    display={{ base: 'table-cell', md: 'none' }}
                    minW="80px"
                  >
                    <VStack spacing={1} align="start">
                      <Text fontSize="xs">Status</Text>
                      <Box onClick={(e) => e.stopPropagation()}>
                        <Select
                          size="xs"
                          placeholder="Alle"
                          value={columnFilters['status'] || ''}
                          onChange={(e) => handleColumnFilter('status', e.target.value)}
                          bg="white"
                          color="black"
                          maxW="80px"
                          fontSize="xs"
                        >
                          {getFilterOptions('status').map(option => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </Select>
                      </Box>
                    </VStack>
                  </Th>
                  
                  {/* Desktop: Regular columns */}
                  {visibleColumns.map(column => {
                    const field = MEMBER_FIELDS[column.fieldKey];
                    if (!field) return null;
                    
                    return (
                      <Th 
                        key={column.fieldKey}
                        minW={column.width ? `${column.width}px` : '120px'}
                        cursor={column.sortable ? 'pointer' : 'default'}
                        onClick={column.sortable ? () => handleSort(column.fieldKey) : undefined}
                        _hover={column.sortable ? { bg: 'gray.600' } : {}}
                        py={2}
                        color="orange.300"
                        display={{ base: 'none', md: 'table-cell' }}
                      >
                        <VStack spacing={1} align="start">
                          <HStack spacing={1}>
                            <Text fontSize="xs">{field.label}</Text>
                            {column.sortable && sortField === column.fieldKey && (
                              <Text fontSize="xs">
                                {sortDirection === 'asc' ? '↑' : '↓'}
                              </Text>
                            )}
                          </HStack>
                          
                          {/* Column Filter - Always Visible */}
                          <Box onClick={(e) => e.stopPropagation()}>
                            {renderColumnFilter(column)}
                          </Box>
                        </VStack>
                      </Th>
                    );
                  })}
                </Tr>
              </Thead>
              <Tbody>
                {filteredMembers.map((member) => (
                  <Tr 
                    key={member.member_id} 
                    _hover={{ bg: 'gray.600', cursor: 'pointer' }}
                    onClick={() => onMemberEdit(member)}
                  >
                    
                    {/* Mobile Portrait: Lidnummer, Full Name, Status */}
                    <Td py={1} color="white" display={{ base: 'table-cell', md: 'none' }} fontSize="xs">
                      <Text fontWeight="semibold">{member.lidnummer || '-'}</Text>
                    </Td>
                    <Td py={1} color="white" display={{ base: 'table-cell', md: 'none' }} fontSize="xs">
                      <Text fontWeight="medium">
                        {[member.voornaam, member.tussenvoegsel, member.achternaam]
                          .filter(Boolean)
                          .join(' ') || '-'}
                      </Text>
                    </Td>
                    <Td py={1} color="white" display={{ base: 'table-cell', md: 'none' }} fontSize="xs">
                      <Badge colorScheme={getStatusColor(member.status)} size="sm" fontSize="xs">
                        {member.status}
                      </Badge>
                    </Td>
                    
                    {/* Desktop: Regular columns */}
                    {visibleColumns.map(column => {
                      const field = MEMBER_FIELDS[column.fieldKey];
                      if (!field) return null;
                      
                      const value = member[column.fieldKey];
                      
                      return (
                        <Td 
                          key={column.fieldKey} 
                          textAlign={column.align || 'left'} 
                          py={1} 
                          color="white"
                          display={{ base: 'none', md: 'table-cell' }}
                        >
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