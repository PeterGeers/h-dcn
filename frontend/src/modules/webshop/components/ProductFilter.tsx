import React, { useMemo, useCallback } from 'react';
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
  Tabs,
  TabList,
  Tab,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../../hooks/useAuth';
import { Tenant } from '../types/unifiedProduct.types';
import { HDCNGroup } from '../../../types/user';

interface Product {
  groep?: string;
  subgroep?: string;
  tenant?: Tenant;
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
  /** Currently selected tenant for filtering (controlled by parent or internal state) */
  selectedTenant?: Tenant | null;
  /** Callback when user switches tenant tab */
  onTenantChange?: (tenant: Tenant | null) => void;
}

/**
 * Derive accessible tenants from user's Cognito group claims.
 * - hdcnLeden → 'h-dcn'
 * - Regio_Pressmeet or Regio_All → 'presmeet'
 */
function resolveTenants(groups: HDCNGroup[]): Tenant[] {
  const tenants: Set<Tenant> = new Set();

  for (const group of groups) {
    if (group === 'hdcnLeden') {
      tenants.add('h-dcn');
    }
    if (group === 'Regio_Pressmeet' || group === 'Regio_All') {
      tenants.add('presmeet');
    }
  }

  return Array.from(tenants);
}

const ProductFilter: React.FC<ProductFilterProps> = ({
  products,
  selectedFilter,
  onFilterChange,
  selectedTenant: controlledTenant,
  onTenantChange,
}) => {
  const { t } = useTranslation('products');
  const { user } = useAuth();

  // Derive accessible tenants from user's Cognito roles
  const userTenants = useMemo(() => {
    const groups = user?.groups ?? [];
    return resolveTenants(groups);
  }, [user]);

  // Internal tenant state when not controlled by parent
  const [internalTenant, setInternalTenant] = React.useState<Tenant | null>(null);

  const activeTenant = controlledTenant !== undefined ? controlledTenant : internalTenant;

  const handleTenantChange = useCallback(
    (tenant: Tenant | null) => {
      if (onTenantChange) {
        onTenantChange(tenant);
      } else {
        setInternalTenant(tenant);
      }
      // Reset filter when tenant changes
      onFilterChange(null);
    },
    [onTenantChange, onFilterChange]
  );

  // Filter products by user's accessible tenants and optionally active tenant tab
  const visibleProducts = useMemo(() => {
    if (userTenants.length === 0) return [];

    return products.filter((product) => {
      // Only show active products (default to true if not specified)
      if (product.active === false) return false;

      // If product has no tenant, include for backward compat with legacy products
      if (!product.tenant) return true;

      // Product must belong to one of the user's accessible tenants
      if (!userTenants.includes(product.tenant)) return false;

      // If a specific tenant tab is selected, filter to that tenant
      if (activeTenant && product.tenant !== activeTenant) return false;

      return true;
    });
  }, [products, userTenants, activeTenant]);

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

  // No tenant access — show info message
  if (userTenants.length === 0) {
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

  const tenantTabIndex = activeTenant
    ? userTenants.indexOf(activeTenant)
    : -1;

  const tenantLabels: Record<Tenant, string> = {
    'h-dcn': 'H-DCN',
    'presmeet': 'PresMeet',
  };

  return (
    <Box bg="gray.800" borderRadius="md" mb={4} color="white" w={{ base: 'full', lg: '300px' }}>
      {/* Tenant tabs — only shown when user has access to multiple tenants */}
      {userTenants.length > 1 && (
        <Box px={2} pt={2}>
          <Tabs
            variant="soft-rounded"
            colorScheme="orange"
            size="sm"
            index={tenantTabIndex === -1 ? userTenants.length : tenantTabIndex}
            onChange={(index) => {
              if (index >= userTenants.length) {
                handleTenantChange(null);
              } else {
                handleTenantChange(userTenants[index]);
              }
            }}
          >
            <TabList>
              {userTenants.map((tenant) => (
                <Tab key={tenant} color="gray.300" _selected={{ color: 'white', bg: 'orange.500' }}>
                  {tenantLabels[tenant]}
                </Tab>
              ))}
              <Tab color="gray.300" _selected={{ color: 'white', bg: 'orange.500' }}>
                {t('filter.all', { defaultValue: 'Alles' })}
              </Tab>
            </TabList>
          </Tabs>
        </Box>
      )}

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
