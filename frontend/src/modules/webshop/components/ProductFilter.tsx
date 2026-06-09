import React, { useMemo } from 'react';
import {
  Box,
  Text,
  VStack,
  Button,
  Collapse,
  useDisclosure,
  HStack,
  Alert,
  AlertIcon,
  AlertDescription,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../../hooks/useAuth';

interface Product {
  groep?: string;
  subgroep?: string;
  event_id?: string | null;
  active?: boolean;
}

interface Filter {
  type: 'group' | 'subgroup';
  value: string;
  group?: string;
}

interface GroupData {
  group: string;
  subgroups: string[];
}

interface GroupItemProps {
  groupData: GroupData;
}

interface ProductFilterProps {
  products: Product[];
  selectedFilter: Filter | null;
  onFilterChange: (filter: Filter | null) => void;
}

const ProductFilter: React.FC<ProductFilterProps> = ({
  products,
  selectedFilter,
  onFilterChange,
}) => {
  const { t } = useTranslation('products');
  const { user } = useAuth();

  // Filter products: only show active webshop products (event_id is null)
  const visibleProducts = useMemo(() => {
    return products.filter((product) => {
      // Only show active products (default to true if not specified)
      if (product.active === false) return false;
      return true;
    });
  }, [products]);

  // Build groep/subgroep filter structure from visible products
  const filterStructure = useMemo(() => {
    const groups: { [key: string]: Set<string> } = {};

    visibleProducts.forEach((product) => {
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
      .map((group) => ({
        group,
        subgroups: Array.from(groups[group]).sort(),
      }));
  }, [visibleProducts]);

  const GroupItem: React.FC<GroupItemProps> = ({ groupData }) => {
    const { isOpen, onToggle } = useDisclosure();
    const isGroupSelected =
      selectedFilter?.type === 'group' && selectedFilter?.value === groupData.group;

    return (
      <Box>
        <Button
          variant="ghost"
          justifyContent="flex-start"
          width="full"
          leftIcon={
            groupData.subgroups.length > 0
              ? isOpen
                ? <ChevronDownIcon />
                : <ChevronRightIcon />
              : undefined
          }
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
          <Box
            flex={1}
            textAlign="left"
            onClick={(e) => {
              e.stopPropagation();
              onFilterChange({ type: 'group', value: groupData.group });
            }}
          >
            {groupData.group}
          </Box>
        </Button>

        {groupData.subgroups.length > 0 && (
          <Collapse in={isOpen}>
            <VStack align="stretch" pl={6} spacing={1}>
              {groupData.subgroups.map((subgroup) => {
                const isSubgroupSelected =
                  selectedFilter?.type === 'subgroup' &&
                  selectedFilter?.value === subgroup &&
                  selectedFilter?.group === groupData.group;

                return (
                  <Button
                    key={subgroup}
                    variant="ghost"
                    size="sm"
                    justifyContent="flex-start"
                    onClick={() =>
                      onFilterChange({ type: 'subgroup', value: subgroup, group: groupData.group })
                    }
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

  const getSelectedText = (): string => {
    if (!selectedFilter) return t('filter.all');
    if (selectedFilter.type === 'group') return selectedFilter.value;
    if (selectedFilter.type === 'subgroup')
      return `${selectedFilter.group} - ${selectedFilter.value}`;
    return t('filter.group', { defaultValue: 'Filter' });
  };

  // No user — show info message
  if (!user) {
    return (
      <Box bg="gray.800" borderRadius="md" mb={4} color="white" w={{ base: 'full', lg: '300px' }}>
        <Alert status="info" bg="gray.700" borderRadius="md" color="white">
          <AlertIcon color="orange.300" />
          <AlertDescription>
            Je hebt geen toegang tot producten.
          </AlertDescription>
        </Alert>
      </Box>
    );
  }

  return (
    <Box bg="gray.800" borderRadius="md" mb={4} color="white" w={{ base: 'full', lg: '300px' }}>
      {/* Group/subgroup filter */}
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
          <Text fontWeight="bold">{t('filter.group', { defaultValue: 'Filter' })}:</Text>
          <Text>{getSelectedText()}</Text>
        </HStack>
      </Button>

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
            {t('filter.all')}
          </Button>
          <VStack align="stretch" spacing={1}>
            {filterStructure.map((groupData) => (
              <GroupItem key={groupData.group} groupData={groupData} />
            ))}
          </VStack>
        </Box>
      </Collapse>
    </Box>
  );
};

export default ProductFilter;
