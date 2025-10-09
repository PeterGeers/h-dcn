import React, { useMemo } from 'react';
import { Box, Text, VStack, Button, Collapse, useDisclosure, HStack } from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon } from '@chakra-ui/icons';

const ProductFilter = ({ products, selectedFilter, onFilterChange }) => {
  const filterStructure = useMemo(() => {
    const groups = {};
    
    products.forEach(product => {
      if (product.groep) {
        if (!groups[product.groep]) {
          groups[product.groep] = new Set();
        }
        if (product.subgroep) {
          groups[product.groep].add(product.subgroep);
        }
      }
    });
    
    return Object.keys(groups)
      .sort()
      .map(group => ({
        group,
        subgroups: Array.from(groups[group]).sort()
      }));
  }, [products]);

  const GroupItem = ({ groupData }) => {
    const { isOpen, onToggle } = useDisclosure();
    const isGroupSelected = selectedFilter?.type === 'group' && selectedFilter?.value === groupData.group;
    
    return (
      <Box>
        <Button
          variant="ghost"
          justifyContent="flex-start"
          width="full"
          leftIcon={groupData.subgroups.length > 0 ? (isOpen ? <ChevronDownIcon /> : <ChevronRightIcon />) : null}
          onClick={(e) => {
            e.preventDefault();
            if (groupData.subgroups.length > 0) {
              onToggle();
            } else {
              onFilterChange({ type: 'group', value: groupData.group });
            }
          }}
          onDoubleClick={() => {
            onFilterChange({ type: 'group', value: groupData.group });
          }}
          bg={isGroupSelected ? 'orange.500' : 'transparent'}
          color={isGroupSelected ? 'white' : 'inherit'}
          _hover={{ bg: isGroupSelected ? 'orange.500' : 'gray.600' }}
        >
          <Box flex={1} textAlign="left" onClick={(e) => {
            e.stopPropagation();
            onFilterChange({ type: 'group', value: groupData.group });
          }}>
            {groupData.group}
          </Box>
        </Button>
        
        {groupData.subgroups.length > 0 && (
          <Collapse in={isOpen}>
            <VStack align="stretch" pl={6} spacing={1}>
              {groupData.subgroups.map(subgroup => {
                const isSubgroupSelected = selectedFilter?.type === 'subgroup' && 
                  selectedFilter?.value === subgroup && selectedFilter?.group === groupData.group;
                
                return (
                  <Button
                    key={subgroup}
                    variant="ghost"
                    size="sm"
                    justifyContent="flex-start"
                    onClick={() => onFilterChange({ type: 'subgroup', value: subgroup, group: groupData.group })}
                    bg={isSubgroupSelected ? 'orange.500' : 'transparent'}
                    color={isSubgroupSelected ? 'white' : 'gray.300'}
                    _hover={{ bg: isSubgroupSelected ? 'orange.500' : 'gray.600' }}
                  >
                    {subgroup}
                  </Button>
                );
              })}
            </VStack>
          </Collapse>
        )}
      </Box>
    );
  };

  const { isOpen, onToggle } = useDisclosure();
  
  const getSelectedText = () => {
    if (!selectedFilter) return 'Alle producten';
    if (selectedFilter.type === 'group') return selectedFilter.value;
    if (selectedFilter.type === 'subgroup') return `${selectedFilter.group} - ${selectedFilter.value}`;
    return 'Filter';
  };

  return (
    <Box bg="gray.800" borderRadius="md" mb={4} color="white" w={{ base: 'full', lg: '300px' }}>
      {/* Dropdown Header */}
      <Button
        onClick={onToggle}
        variant="ghost"
        w="full"
        justifyContent="space-between"
        rightIcon={isOpen ? <ChevronDownIcon /> : <ChevronRightIcon />}
        bg="gray.700"
        color="white"
        _hover={{ bg: 'gray.600' }}
        borderRadius="md"
        p={4}
      >
        <HStack>
          <Text fontWeight="bold">Filter:</Text>
          <Text>{getSelectedText()}</Text>
        </HStack>
      </Button>
      
      {/* Dropdown Content */}
      <Collapse in={isOpen}>
        <Box p={4} pt={2}>
          <Button
            variant="ghost"
            size="sm"
            mb={2}
            onClick={() => onFilterChange(null)}
            bg={!selectedFilter ? 'orange.500' : 'transparent'}
            color={!selectedFilter ? 'white' : 'gray.300'}
            _hover={{ bg: !selectedFilter ? 'orange.500' : 'gray.600' }}
            w="full"
            justifyContent="flex-start"
          >
            Alle producten
          </Button>
          <VStack align="stretch" spacing={1}>
            {filterStructure.map(groupData => (
              <GroupItem key={groupData.group} groupData={groupData} />
            ))}
          </VStack>
        </Box>
      </Collapse>
    </Box>
  );
};

export default ProductFilter;