/**
 * ProductsTab — Wraps the existing ProductManagementPage inside the Webshop Beheer tab.
 *
 * This embeds the full existing product management UI (with group/subgroup filters,
 * edit modal, create/delete functionality) inside the Webshop Beheer tab.
 *
 * Validates: Requirements 2.1, 2.3, 10.5, 12.6
 */

import React, { useMemo } from 'react';
import { Box } from '@chakra-ui/react';
import { useAuth } from '../../../hooks/useAuth';
import ProductManagementPage from '../../products/ProductManagementPage';

export interface ProductsTabProps {
  eventFilter?: string;
}

export const ProductsTab: React.FC<ProductsTabProps> = ({ eventFilter = '' }) => {
  const { user } = useAuth();

  // Build the user object that ProductManagementPage expects
  const productPageUser = useMemo(() => {
    if (!user) return null;
    return {
      groups: user.groups || [],
      attributes: {
        given_name: user.givenName,
        family_name: user.familyName,
        email: user.email,
      },
      signInUserSession: {
        accessToken: {
          payload: {
            'cognito:groups': user.groups || [],
          },
          jwtToken: user.accessToken,
        },
      },
    };
  }, [user]);

  if (!productPageUser) return null;

  return (
    <Box>
      <ProductManagementPage user={productPageUser} eventFilter={eventFilter || undefined} />
    </Box>
  );
};

export default ProductsTab;
