/**
 * Member Admin Table - Using Field Registry System
 * 
 * Dynamic member table with context switching and field registry integration
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
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
  Flex,
  Spacer,
  Card,
  CardBody,
  useColorModeValue
} from '@chakra-ui/react';
import { 
  AddIcon
} from '@chakra-ui/icons';
import { MEMBER_TABLE_CONTEXTS, MEMBER_FIELDS, HDCNGroup, getFilteredEnumOptions } from '../config/memberFields';
import { canViewField } from '../utils/fieldResolver';
import { renderFieldValue } from '../utils/fieldRenderers';
import { computeCalculatedFieldsForArray, getMemberFullName } from '../utils/calculatedFields';
import { useFilterableTable } from '../hooks/useFilterableTable';
import { FilterableHeader, FilterPanel, GenericFilter } from '../components/filters';


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
  const [selectedContext, setSelectedContext] = useState('memberCompact');
  // Select-type filters (dropdown pre-filters, outside framework)
  const [selectFilters, setSelectFilters] = useState<Record<string, string>>({});

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _filterBg = useColorModeValue('gray.50', 'gray.700');

  // Get available contexts based on user permissions
  const availableContexts = useMemo(() => {
    return Object.entries(MEMBER_TABLE_CONTEXTS).filter(([key, context]) => 
      context.permissions.view.includes(userRole)
    );
  }, [userRole]);

  // Get current table context
  const tableContext = MEMBER_TABLE_CONTEXTS[selectedContext];

  // Get visible columns based on context and permissions
  const visibleColumns = useMemo(() => {
    if (!tableContext) return [];
    const visibleCols = tableContext.columns.filter(col => col.visible);
    const permissionFilteredCols = visibleCols.filter(col => {
      const field = MEMBER_FIELDS[col.fieldKey];
      if (!field) return false;
      return canViewField(field, userRole, members[0]);
    });
    return permissionFilteredCols.sort((a, b) => a.order - b.order);
  }, [tableContext, userRole, members]);

  // Determine which columns are text-filterable (for framework) vs select-filterable (pre-filter)
  const { textFilterColumns, selectFilterColumns } = useMemo(() => {
    const textCols: string[] = [];
    const selectCols: string[] = [];
    visibleColumns.forEach(col => {
      if (!col.filterable) return;
      if (col.filterType === 'select') {
        selectCols.push(col.fieldKey);
      } else {
        textCols.push(col.fieldKey);
      }
    });
    return { textFilterColumns: textCols, selectFilterColumns: selectCols };
  }, [visibleColumns]);

  // Build initial filters for the framework (text columns only)
  const initialFilters = useMemo(() => {
    const filters: Record<string, string> = {};
    textFilterColumns.forEach(key => { filters[key] = ''; });
    // Always include fullName for mobile
    filters['fullName'] = '';
    return filters;
  }, [textFilterColumns]);

  // Pre-process members with calculated fields
  const processedMembers = useMemo(() => {
    return computeCalculatedFieldsForArray(members).map(m => ({
      ...m,
      fullName: getMemberFullName(m),
    }));
  }, [members]);

  // Pre-filter: regional permissions
  const regionalFiltered = useMemo(() => {
    if (tableContext?.regionalRestricted && userRole === 'Members_Read' && userRegion) {
      return processedMembers.filter(member => member.regio === userRegion);
    }
    return processedMembers;
  }, [processedMembers, tableContext?.regionalRestricted, userRole, userRegion]);

  // Pre-filter: select/dropdown filters (exact match)
  const preFilteredMembers = useMemo(() => {
    let data = regionalFiltered;
    Object.entries(selectFilters).forEach(([fieldKey, filterValue]) => {
      if (filterValue) {
        data = data.filter(member => member[fieldKey] === filterValue);
      }
    });
    return data;
  }, [regionalFiltered, selectFilters]);

  // Framework: text filters + sort
  const { filters, setFilter, handleSort, sortField, sortDirection, processedData, resetFilters } =
    useFilterableTable(preFilteredMembers as unknown as Record<string, unknown>[], {
      initialFilters,
      defaultSort: { field: 'lidnummer', direction: 'desc' },
    });

  const filteredMembers = processedData as any[];

  // Reset filters when context changes
  const handleContextChange = useCallback((newContext: string) => {
    setSelectedContext(newContext);
    setSelectFilters({});
    resetFilters();
  }, [resetFilters]);

  // Select filter handler
  const handleSelectFilter = useCallback((fieldKey: string, value: string) => {
    setSelectFilters(prev => ({ ...prev, [fieldKey]: value }));
  }, []);

  const getFilterOptions = (fieldKey: string) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (field?.enumOptions) {
      return getFilteredEnumOptions(field, userRole);
    }
    const uniqueValues = [...new Set(members.map(m => m[fieldKey]).filter(Boolean))];
    return uniqueValues.sort();
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
                  onChange={(e) => handleContextChange(e.target.value)}
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
                    onChange={(e) => handleContextChange(e.target.value)}
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
                {onAddMember && ['System_User_Management', 'Members_CRUD'].includes(userRole) && (
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

        {/* Select Filters (dropdown pre-filters) */}
        {selectFilterColumns.length > 0 && (
          <FilterPanel
            layout="horizontal"
            filters={selectFilterColumns
              .filter(fieldKey => MEMBER_FIELDS[fieldKey])
              .map(fieldKey => {
                const field = MEMBER_FIELDS[fieldKey];
                return {
                  type: 'single' as const,
                  label: field.label,
                  value: selectFilters[fieldKey] || '',
                  options: getFilterOptions(fieldKey).map(opt => ({ value: opt, label: opt })),
                  onChange: (v: string | string[]) => handleSelectFilter(fieldKey, v as string),
                  placeholder: 'Alle',
                };
              })}
          />
        )}

        {/* Table */}
        <Card bg="gray.800" borderColor="orange.400" border="1px">
          <Box overflowX="auto">
            <Table variant="simple" size="xs">
              <Thead bg="gray.700">
                <Tr>
                  {/* Mobile Portrait: Lidnummer, Name, Status */}
                  <Th 
                    py={2}
                    color="orange.300"
                    display={{ base: 'table-cell', md: 'none' }}
                    w="60px"
                  >
                    <FilterableHeader
                      label="Lidnr"
                      filterValue={filters.lidnummer || ''}
                      onFilterChange={(v) => setFilter('lidnummer' as any, v)}
                      sortable
                      sortDirection={sortField === 'lidnummer' ? sortDirection : null}
                      onSort={() => handleSort('lidnummer')}
                      w="60px"
                      placeholder="Nr..."
                    />
                  </Th>
                  <Th 
                    py={2}
                    color="orange.300"
                    display={{ base: 'table-cell', md: 'none' }}
                  >
                    <FilterableHeader
                      label="Naam"
                      filterValue={filters.fullName || ''}
                      onFilterChange={(v) => setFilter('fullName' as any, v)}
                      sortable
                      sortDirection={sortField === 'fullName' ? sortDirection : null}
                      onSort={() => handleSort('fullName')}
                      w="120px"
                      placeholder="Naam..."
                    />
                  </Th>
                  <Th 
                    py={2}
                    color="orange.300"
                    display={{ base: 'table-cell', md: 'none' }}
                    w="80px"
                  >
                    <GenericFilter
                      label="Status"
                      value={selectFilters['status'] || ''}
                      options={getFilterOptions('status').map(opt => ({ value: opt, label: opt }))}
                      onChange={(v) => handleSelectFilter('status', v)}
                      placeholder="Alle"
                      width="90px"
                    />
                  </Th>
                  
                  {/* Desktop: Dynamic columns from context with FilterableHeader */}
                  {visibleColumns.map(column => {
                    const field = MEMBER_FIELDS[column.fieldKey];
                    if (!field) return null;

                    // Select columns get a plain Th (their filter is in FilterPanel above)
                    if (column.filterType === 'select') {
                      return (
                        <Th
                          key={column.fieldKey}
                          w={column.width ? `${column.width}px` : '120px'}
                          cursor={column.sortable ? 'pointer' : 'default'}
                          onClick={column.sortable ? () => handleSort(column.fieldKey) : undefined}
                          _hover={column.sortable ? { bg: 'gray.600' } : {}}
                          py={2}
                          color="orange.300"
                          display={{ base: 'none', md: 'table-cell' }}
                        >
                          <HStack spacing={1}>
                            <Text fontSize="xs">{field.label}</Text>
                            {column.sortable && sortField === column.fieldKey && (
                              <Text fontSize="xs" color="orange.400">
                                {sortDirection === 'asc' ? '↑' : '↓'}
                              </Text>
                            )}
                          </HStack>
                        </Th>
                      );
                    }

                    // Text/number/date columns get FilterableHeader
                    return (
                      <FilterableHeader
                        key={column.fieldKey}
                        label={field.label}
                        filterValue={column.filterable ? (filters[column.fieldKey as keyof typeof filters] || '') : undefined}
                        onFilterChange={column.filterable ? (v) => setFilter(column.fieldKey as any, v) : undefined}
                        sortable={column.sortable}
                        sortDirection={sortField === column.fieldKey ? sortDirection : null}
                        onSort={() => handleSort(column.fieldKey)}
                        w={column.width ? `${column.width}px` : '120px'}
                      />
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
                        {getMemberFullName(member) || '-'}
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
                      
                      // Use field.key to access the actual database field name
                      // (e.g., 'ingangsdatum' field definition has key: 'tijdstempel')
                      const value = member[field.key];
                      
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