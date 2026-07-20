import React from 'react';
import { Table, Tbody, Td, Thead, Tr, Box, Text, Badge } from '@chakra-ui/react';
import { Product } from '../../../types';
import { useTranslation } from 'react-i18next';
import { isDeactivated } from '../../../utils/productHelpers';
import { FilterableHeader } from '../../../components/filters';
import type { SortDirection } from '../../../components/filters/types';

export interface ProductColumnFilters {
  artikelcode: string;
  groep: string;
  naam: string;
  prijs: string;
  status: string;
  source: string;
}

interface ProductTableProps {
  products: Product[];
  onSelect: (product: Product) => void;
  renderActions?: (product: Product) => React.ReactNode;
  showStatusColumn?: boolean;
  /** Column filter values */
  filters?: ProductColumnFilters;
  /** Set a column filter */
  onFilterChange?: (key: keyof ProductColumnFilters, value: string) => void;
  /** Current sort field */
  sortField?: string | null;
  /** Current sort direction */
  sortDirection?: SortDirection | null;
  /** Sort toggle handler */
  onSort?: (field: string) => void;
}

export default function ProductTable({
  products,
  onSelect,
  renderActions,
  showStatusColumn,
  filters,
  onFilterChange,
  sortField,
  sortDirection,
  onSort,
}: ProductTableProps): React.ReactElement {
  const { t } = useTranslation('products');

  const isFilterable = !!filters && !!onFilterChange;

  return (
    <Box overflow="auto" maxW="100%" bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400">
      <Table variant="simple" colorScheme="orange" size={{ base: 'sm', md: 'md' }}>
        <Thead bg="gray.700">
          <Tr>
            {isFilterable ? (
              <>
                <FilterableHeader
                  label="Artikelcode"
                  filterValue={filters.artikelcode}
                  onFilterChange={(v) => onFilterChange('artikelcode', v)}
                  sortable
                  sortDirection={sortField === 'artikelcode' ? sortDirection : null}
                  onSort={() => onSort?.('artikelcode')}
                  minW="80px"
                />
                <FilterableHeader
                  label="Categorie"
                  filterValue={filters.groep}
                  onFilterChange={(v) => onFilterChange('groep', v)}
                  sortable
                  sortDirection={sortField === 'groep' ? sortDirection : null}
                  onSort={() => onSort?.('groep')}
                  minW="120px"
                  display={{ base: 'none', md: 'table-cell' }}
                />
                <FilterableHeader
                  label="Naam"
                  filterValue={filters.naam}
                  onFilterChange={(v) => onFilterChange('naam', v)}
                  sortable
                  sortDirection={sortField === 'naam' ? sortDirection : null}
                  onSort={() => onSort?.('naam')}
                  minW="150px"
                />
                <FilterableHeader
                  label="Prijs"
                  filterValue={filters.prijs}
                  onFilterChange={(v) => onFilterChange('prijs', v)}
                  sortable
                  sortDirection={sortField === 'prijs' ? sortDirection : null}
                  onSort={() => onSort?.('prijs')}
                  minW="80px"
                />
                {showStatusColumn && (
                  <FilterableHeader
                    label="Status"
                    filterValue={filters.status}
                    onFilterChange={(v) => onFilterChange('status', v)}
                    sortable
                    sortDirection={sortField === 'status' ? sortDirection : null}
                    onSort={() => onSort?.('status')}
                    minW="80px"
                  />
                )}
                <FilterableHeader
                  label="Bron"
                  filterValue={filters.source}
                  onFilterChange={(v) => onFilterChange('source', v)}
                  sortable
                  sortDirection={sortField === 'source' ? sortDirection : null}
                  onSort={() => onSort?.('source')}
                  minW="100px"
                />
              </>
            ) : (
              <>
                <FilterableHeader label="Artikelcode" minW="60px" />
                <FilterableHeader label="Categorie" minW="120px" display={{ base: 'none', md: 'table-cell' }} />
                <FilterableHeader label="Naam" minW="150px" />
                <FilterableHeader label="Prijs" minW="80px" />
                {showStatusColumn && <FilterableHeader label="Status" minW="80px" />}
                <FilterableHeader label="Bron" minW="100px" />
              </>
            )}
            {renderActions && <FilterableHeader label={t('table.actions')} minW="120px" />}
          </Tr>
        </Thead>
        <Tbody>
          {products.map((p) => (
            <Tr
              key={p.product_id || p.id}
              _hover={{ bg: 'orange.500', cursor: 'pointer', color: 'white' }}
              onClick={() => onSelect(p)}
              color="white"
              opacity={isDeactivated(p) ? 0.6 : 1}
            >
              <Td fontSize={{ base: 'xs', md: 'sm' }}>{p.artikelcode || '-'}</Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                <Text isTruncated maxW="120px">{p.groep} - {p.subgroep}</Text>
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }}>
                {p.naam}
              </Td>
              <Td fontSize={{ base: 'xs', md: 'sm' }}>€{p.prijs}</Td>
              {showStatusColumn && (
                <Td fontSize={{ base: 'xs', md: 'sm' }}>
                  {isDeactivated(p) ? (
                    <Badge colorScheme="red" variant="subtle">{t('management.inactive_badge')}</Badge>
                  ) : (
                    <Badge colorScheme="green" variant="subtle">Actief</Badge>
                  )}
                </Td>
              )}
              <Td fontSize={{ base: 'xs', md: 'sm' }}>
                <Text isTruncated maxW="100px" color="gray.400">
                  {((p as any)._sourceDisplay) || ((p as any).event_ids || []).map((id: string) => id === 'evt-webshop' ? 'Webshop' : id.slice(0, 8)).join(', ') || '-'}
                </Text>
              </Td>
              {renderActions && (
                <Td onClick={(e) => e.stopPropagation()}>
                  {renderActions(p)}
                </Td>
              )}
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
}
