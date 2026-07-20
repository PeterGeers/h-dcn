import React from 'react';
import {
  Box, Table, Thead, Tbody, Tr, Th, Td, Text
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';

interface Membership {
  membership_id?: string;
  membership_type_id?: string;
  id?: string;
  name?: string;
  membership_name?: string;
  description?: string;
  price?: number;
  duration_months?: number;
  status?: string;
  membership_status?: string;
}

interface MembershipTableProps {
  memberships: Membership[];
  onRowClick: (membership: Membership) => void;
}

export function MembershipTable({ memberships, onRowClick }: MembershipTableProps) {
  const { t } = useTranslation('common');

  return (
    <>
      <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
        <Table variant="simple">
          <Thead bg="gray.700">
            <Tr>
              <Th color="orange.300">{t('name', { defaultValue: 'Naam' })}</Th>
              <Th color="orange.300">{t('description', { defaultValue: 'Beschrijving' })}</Th>
              <Th color="orange.300">{t('price', { defaultValue: 'Prijs' })}</Th>
              <Th color="orange.300">{t('durationMonths', { defaultValue: 'Duur (maanden)' })}</Th>
            </Tr>
          </Thead>
          <Tbody>
            {memberships.map((membership) => (
              <Tr
                key={membership.membership_id || membership.id}
                onClick={() => onRowClick(membership)}
                _hover={{ bg: 'gray.700', cursor: 'pointer' }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onRowClick(membership);
                }}
              >
                <Td color="white" fontWeight="bold">{membership.name}</Td>
                <Td color="white">{membership.description}</Td>
                <Td color="white">€{membership.price}</Td>
                <Td color="white">{membership.duration_months}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {memberships.length === 0 && (
        <Text textAlign="center" color="gray.400" py={8}>
          {t('noMembershipsFound', { defaultValue: 'Geen lidmaatschappen gevonden' })}
        </Text>
      )}
    </>
  );
}
