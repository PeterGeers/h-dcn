import React from 'react';
import { Box, Flex, Button, HStack } from '@chakra-ui/react';
import { ArrowBackIcon, ViewIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FunctionGuard } from '../../../components/common/FunctionGuard';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
    family_name?: string;
    phone_number?: string;
    'custom:member_id'?: string;
  };
  username?: string;
}

interface WebshopHeaderProps {
  user: User;
  cartItemCount: number;
  showOrdersAdmin: boolean;
  showMyOrders: boolean;
  onToggleOrdersAdmin: () => void;
  onToggleMyOrders: () => void;
  onOpenCart: () => void;
}

function WebshopHeader({ user, cartItemCount, showOrdersAdmin, showMyOrders, onToggleOrdersAdmin, onToggleMyOrders, onOpenCart }: WebshopHeaderProps) {
  const navigate = useNavigate();
  const { t } = useTranslation('webshop');
  const { t: tCommon } = useTranslation('common');

  return (
    <Flex justify="space-between" align="center" p={4} bg="black" color="orange.400">
      <Button onClick={() => navigate('/')} variant="ghost" color="orange.300" leftIcon={<ArrowBackIcon />}>
        {tCommon('nav.back_to_dashboard')}
      </Button>
      <Box fontSize="xl" fontWeight="bold">{t('title')}</Box>
      <HStack>
        <Button
          onClick={onToggleMyOrders}
          colorScheme="orange"
          variant={showMyOrders ? 'solid' : 'ghost'}
          size="sm"
        >
          {t('my_orders.title', { defaultValue: 'Mijn bestellingen' })}
        </Button>
        <FunctionGuard
          user={user}
          functionName="orders"
          action="read"
          requiredRoles={['Products_CRUD', 'System_User_Management']}
          fallback={null}
        >
          <Button
            onClick={onToggleOrdersAdmin}
            colorScheme="orange"
            variant="ghost"
            size="sm"
          >
            Orders
          </Button>
        </FunctionGuard>
        <Button
          onClick={onOpenCart}
          colorScheme="orange"
          variant="outline"
          leftIcon={<ViewIcon />}
        >
          {t('cart.item_count', { count: cartItemCount })}
        </Button>
      </HStack>
    </Flex>
  );
}

export default WebshopHeader;
