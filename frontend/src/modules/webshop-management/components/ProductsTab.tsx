/**
 * ProductsTab — Admin product list with variant management.
 *
 * Shows all products from getAdminProducts(tenant) API with:
 * - Product name, tenant badge, product_type, price, active status
 * - Expandable variant sub-table for multi-variant products
 * - Inline stock display for Default_Variant (single-variant) products
 * - Bulk variant creation and stock recording actions
 *
 * Validates: Requirements 2.1, 2.3, 3.1, 3.8
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Switch,
  Button,
  Spinner,
  Text,
  IconButton,
  Collapse,
  HStack,
  Tooltip,
  useToast,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon } from '@chakra-ui/icons';
import { AdminProduct, AdminVariant } from '../types/admin.types';
import { getAdminProducts, updateVariant } from '../services/adminApi';
import { VariantSubTable } from './VariantSubTable';
import { BulkVariantCreator } from './BulkVariantCreator';
import { AddStockForm } from './AddStockForm';
import { useAdminPermissions } from '../hooks/useAdminPermissions';

export interface ProductsTabProps {
  tenant: string;
}

/**
 * Checks if a product has only the Default_Variant (empty variant_attributes).
 */
function isDefaultVariantProduct(product: AdminProduct): boolean {
  if (!product.variants || product.variants.length !== 1) return false;
  const variant = product.variants[0];
  return (
    Object.keys(variant.variant_attributes || {}).length === 0
  );
}

export const ProductsTab: React.FC<ProductsTabProps> = ({ tenant }) => {
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProductIds, setExpandedProductIds] = useState<Set<string>>(new Set());
  const { canMutate } = useAdminPermissions();
  const toast = useToast();
  const disabledTooltip = 'Products_CRUD vereist';

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminProducts(tenant || undefined);
      // Normalize: ensure each product has a variants array and numeric price
      const normalized = (data || []).map((p: any) => ({
        ...p,
        variants: p.variants ?? [],
        price: parseFloat(p.price ?? p.prijs ?? '0') || 0,
      }));
      setProducts(normalized);
    } catch (err: any) {
      setError(err?.message || 'Fout bij het ophalen van producten');
    } finally {
      setLoading(false);
    }
  }, [tenant]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const toggleExpand = (productId: string) => {
    setExpandedProductIds((prev) => {
      const next = new Set(prev);
      if (next.has(productId)) {
        next.delete(productId);
      } else {
        next.add(productId);
      }
      return next;
    });
  };

  const handleInlineOversellToggle = async (
    product: AdminProduct,
    variant: AdminVariant,
    newValue: boolean
  ) => {
    try {
      await updateVariant(variant.parent_id, variant.product_id, {
        allow_oversell: newValue,
      });
      toast({
        title: 'Bijgewerkt',
        description: `Oversell ${newValue ? 'ingeschakeld' : 'uitgeschakeld'}`,
        status: 'success',
        duration: 2000,
      });
      fetchProducts();
    } catch (err: any) {
      toast({
        title: 'Fout',
        description: err?.message || 'Kon niet bijwerken',
        status: 'error',
        duration: 3000,
      });
    }
  };

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.400">Producten laden...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={4} bg="red.900" borderRadius="md">
        <Text color="red.200">{error}</Text>
        <Button mt={2} size="sm" onClick={fetchProducts}>
          Opnieuw proberen
        </Button>
      </Box>
    );
  }

  if (products.length === 0) {
    return (
      <Box p={4} bg="gray.800" borderRadius="md">
        <Text color="gray.400">Geen producten gevonden.</Text>
      </Box>
    );
  }

  return (
    <Box overflowX="auto">
      <Table variant="simple" size="sm">
        <Thead>
          <Tr>
            <Th w="40px"></Th>
            <Th>Naam</Th>
            <Th>Tenant</Th>
            <Th>Type</Th>
            <Th isNumeric>Prijs</Th>
            <Th>Actief</Th>
            <Th>Voorraad</Th>
            <Th>Verkocht</Th>
            <Th>Oversell</Th>
            <Th>Acties</Th>
          </Tr>
        </Thead>
        <Tbody>
          {products.map((product) => {
            const isDefault = isDefaultVariantProduct(product);
            const isExpanded = expandedProductIds.has(product.product_id);
            const defaultVariant = isDefault ? product.variants[0] : null;

            return (
              <React.Fragment key={product.product_id}>
                {/* Product row */}
                <Tr _hover={{ bg: 'gray.700' }}>
                  {/* Expand toggle */}
                  <Td>
                    {!isDefault && (product.variants?.length ?? 0) > 0 && (
                      <IconButton
                        aria-label="Varianten tonen"
                        icon={isExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
                        size="xs"
                        variant="ghost"
                        onClick={() => toggleExpand(product.product_id)}
                      />
                    )}
                  </Td>

                  {/* Product name */}
                  <Td fontWeight="medium">{product.name}</Td>

                  {/* Tenant badge */}
                  <Td>
                    <Badge
                      colorScheme={product.tenant === 'presmeet' ? 'purple' : 'blue'}
                      size="sm"
                    >
                      {product.tenant}
                    </Badge>
                  </Td>

                  {/* Product type */}
                  <Td>
                    {product.product_type ? (
                      <Badge variant="outline" colorScheme="gray">
                        {product.product_type}
                      </Badge>
                    ) : (
                      <Text color="gray.500" fontSize="xs">—</Text>
                    )}
                  </Td>

                  {/* Price */}
                  <Td isNumeric>€{(product.price ?? 0).toFixed(2)}</Td>

                  {/* Active status */}
                  <Td>
                    <Badge colorScheme={product.active ? 'green' : 'red'}>
                      {product.active ? 'Actief' : 'Inactief'}
                    </Badge>
                  </Td>

                  {/* Inline stock for Default_Variant products (Task 15.4) */}
                  <Td isNumeric>
                    {isDefault && defaultVariant ? (
                      <Text>{defaultVariant.stock}</Text>
                    ) : (
                      <Text color="gray.500" fontSize="xs">—</Text>
                    )}
                  </Td>

                  <Td isNumeric>
                    {isDefault && defaultVariant ? (
                      <Text>{defaultVariant.sold_count}</Text>
                    ) : (
                      <Text color="gray.500" fontSize="xs">—</Text>
                    )}
                  </Td>

                  <Td>
                    {isDefault && defaultVariant ? (
                      <Tooltip label={!canMutate ? disabledTooltip : ''} isDisabled={canMutate} hasArrow>
                        <Box display="inline-block">
                          <Switch
                            size="sm"
                            isChecked={defaultVariant.allow_oversell}
                            isDisabled={!canMutate}
                            onChange={(e) =>
                              handleInlineOversellToggle(product, defaultVariant, e.target.checked)
                            }
                            colorScheme="orange"
                          />
                        </Box>
                      </Tooltip>
                    ) : (
                      <Text color="gray.500" fontSize="xs">—</Text>
                    )}
                  </Td>

                  {/* Actions */}
                  <Td>
                    <HStack spacing={1}>
                      {product.required_attributes && (
                        <Tooltip label={!canMutate ? disabledTooltip : ''} isDisabled={canMutate} hasArrow>
                          <Box display="inline-block">
                            <BulkVariantCreator
                              productId={product.product_id}
                              productName={product.name}
                              onSuccess={fetchProducts}
                              isDisabled={!canMutate}
                            />
                          </Box>
                        </Tooltip>
                      )}
                      {isDefault && defaultVariant && (
                        <Tooltip label={!canMutate ? disabledTooltip : ''} isDisabled={canMutate} hasArrow>
                          <Box display="inline-block">
                            <AddStockForm
                              productId={product.product_id}
                              variantId={defaultVariant.product_id}
                              variantLabel={product.name}
                              onSuccess={fetchProducts}
                              isDisabled={!canMutate}
                            />
                          </Box>
                        </Tooltip>
                      )}
                    </HStack>
                  </Td>
                </Tr>

                {/* Variant sub-table (Task 15.2) */}
                {!isDefault && (product.variants?.length ?? 0) > 0 && (
                  <Tr>
                    <Td colSpan={10} p={0} border="none">
                      <Collapse in={isExpanded} animateOpacity>
                        <Box pl={10} pr={4} py={2} bg="gray.750">
                          <VariantSubTable
                            product={product}
                            variants={product.variants}
                            onUpdate={fetchProducts}
                          />
                        </Box>
                      </Collapse>
                    </Td>
                  </Tr>
                )}
              </React.Fragment>
            );
          })}
        </Tbody>
      </Table>
    </Box>
  );
};

export default ProductsTab;
