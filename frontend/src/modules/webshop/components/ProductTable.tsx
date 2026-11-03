import React, { useMemo, useState } from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Box,
  Image
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useTableSort } from '../../../hooks/useTableSort';
import { FilterableHeader } from '../../../components/filters';
import { getPrimaryImageUrl } from '../../../utils/productImage';
import { formatPrice } from '../../../utils/formatPrice';

export interface Product {
  product_id: string;
  id?: string;
  name?: string;
  naam?: string;
  groep?: string;
  subgroep?: string;
  price?: number;
  prijs?: number | string;
  /** Primary image source (array form). */
  images?: string[];
  /** Legacy image source (string or array). */
  image?: string | string[];
  /** Retained in the type but intentionally not rendered by this table. */
  is_parent?: boolean;
}

/** Text filters applied to the public product table (one per filterable column). */
export interface ProductFilters {
  naam: string;
  groep: string;
  subgroep: string;
}

/** The product fields that can be filtered by text. */
export type ProductFilterField = keyof ProductFilters;

/**
 * Does a single product field satisfy a single filter value?
 *
 * Pure helper. Rules:
 * - An empty (or whitespace-only) filter matches everything.
 * - For a non-empty filter, the field must be a string that contains the
 *   filter as a case-insensitive substring.
 * - An absent / null / undefined / non-string field never matches a non-empty
 *   filter.
 */
export function fieldMatches(fieldValue: unknown, filterValue: string): boolean {
  const needle = filterValue.trim().toLowerCase();
  // Empty filter matches all.
  if (needle === '') return true;
  // Non-empty filter requires a string field.
  if (typeof fieldValue !== 'string') return false;
  return fieldValue.toLowerCase().includes(needle);
}

/**
 * Does a product satisfy all active filters?
 *
 * Pure helper. Filters are combined with AND: every non-empty filter must
 * match its corresponding field. An all-empty filter set matches every
 * product.
 */
export function matchesFilters(product: Product, filters: ProductFilters): boolean {
  return (
    fieldMatches(product.naam, filters.naam) &&
    fieldMatches(product.groep, filters.groep) &&
    fieldMatches(product.subgroep, filters.subgroep)
  );
}

interface ProductTableProps {
  products: Product[];
  onProductSelect: (product: Product) => void;
}

const EMPTY_FILTERS: ProductFilters = { naam: '', groep: '', subgroep: '' };

const ProductTable: React.FC<ProductTableProps> = ({ products, onProductSelect }) => {
  const { t } = useTranslation('products');

  // Self-contained text filter state (one per filterable column).
  const [filters, setFilters] = useState<ProductFilters>(EMPTY_FILTERS);
  const setFilter = (key: ProductFilterField, value: string) =>
    setFilters((prev) => ({ ...prev, [key]: value }));

  // Filter first (case-insensitive substring, AND across active filters)...
  const filtered = useMemo(
    () => products.filter((product) => matchesFilters(product, filters)),
    [products, filters],
  );

  // ...then sort the filtered result.
  const { sortField, sortDirection, handleSort, sortedData } = useTableSort<Product>(
    filtered,
    'naam',
    'asc',
  );

  return (
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
            {/* Thumbnail column: not sortable, not filterable. */}
            <Th color="orange.300" w="56px" aria-hidden />
            <FilterableHeader
              label={t('table.name')}
              filterValue={filters.naam}
              onFilterChange={(value) => setFilter('naam', value)}
              sortable
              sortDirection={sortField === 'naam' ? sortDirection : null}
              onSort={() => handleSort('naam')}
              placeholder={t('table.filter_name')}
              w="40%"
            />
            <FilterableHeader
              label={t('table.group')}
              filterValue={filters.groep}
              onFilterChange={(value) => setFilter('groep', value)}
              sortable
              sortDirection={sortField === 'groep' ? sortDirection : null}
              onSort={() => handleSort('groep')}
              placeholder={t('table.filter_group')}
              minW="100px"
              display={{ base: 'none', md: 'table-cell' }}
            />
            <FilterableHeader
              label={t('table.subgroup')}
              filterValue={filters.subgroep}
              onFilterChange={(value) => setFilter('subgroep', value)}
              sortable
              sortDirection={sortField === 'subgroep' ? sortDirection : null}
              onSort={() => handleSort('subgroep')}
              placeholder={t('table.filter_subgroup')}
              minW="100px"
              display={{ base: 'none', lg: 'table-cell' }}
            />
            <FilterableHeader
              label={t('table.price')}
              sortable
              sortDirection={sortField === 'prijs' ? sortDirection : null}
              onSort={() => handleSort('prijs')}
              isNumeric
              minW="80px"
            />
          </Tr>
        </Thead>
        <Tbody>
          {sortedData.map((product) => {
            const displayName = product.naam || '';
            const imageUrl = getPrimaryImageUrl(product);
            return (
              <Tr
                key={product.product_id}
                cursor="pointer"
                _hover={{ bg: 'orange.500', color: 'white' }}
                onClick={() => onProductSelect(product)}
                color="white"
              >
                {/* Thumbnail cell: render the image only when a usable URL
                    exists; otherwise an empty cell (no broken-image icon). */}
                <Td>
                  {imageUrl && (
                    <Image
                      src={imageUrl}
                      alt={displayName || t('table.thumbnail_alt')}
                      boxSize="48px"
                      objectFit="cover"
                      borderRadius="md"
                    />
                  )}
                </Td>
                <Td fontWeight="medium" fontSize={{ base: 'xs', md: 'sm' }}>
                  {displayName}
                </Td>
                <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                  <Text isTruncated maxW="100px">{product.groep}</Text>
                </Td>
                <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                  <Text isTruncated maxW="100px">{product.subgroep}</Text>
                </Td>
                <Td fontSize={{ base: 'xs', md: 'sm' }} isNumeric>
                  {formatPrice(product.prijs)}
                </Td>
              </Tr>
            );
          })}
        </Tbody>
      </Table>
    </Box>
  );
};

export default ProductTable;
