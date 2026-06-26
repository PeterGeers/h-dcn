import React from 'react';
import {
  Box, HStack, Button, Table, Thead, Tbody, Tr, Th, Td, Text
} from '@chakra-ui/react';
import { FunctionGuard } from '../../../components/common/FunctionGuard';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
  };
}

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
  user: User;
  memberships: Membership[];
  onEdit: (membership: Membership) => void;
  onDelete: (membership: Membership) => void;
}

export function MembershipTable({ user, memberships, onEdit, onDelete }: MembershipTableProps) {
  return (
    <>
      <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
        <Table variant="simple">
          <Thead bg="gray.700">
            <Tr>
              <Th color="orange.300">Naam</Th>
              <Th color="orange.300">Beschrijving</Th>
              <Th color="orange.300">Prijs</Th>
              <Th color="orange.300">Duur (maanden)</Th>
              <Th color="orange.300">Acties</Th>
            </Tr>
          </Thead>
          <Tbody>
            {memberships.map((membership) => (
              <Tr key={membership.membership_id || membership.id}>
                <Td color="white" fontWeight="bold">{membership.name}</Td>
                <Td color="white">{membership.description}</Td>
                <Td color="white">€{membership.price}</Td>
                <Td color="white">{membership.duration_months}</Td>
                <Td>
                  <HStack spacing={2}>
                    <FunctionGuard 
                      user={user} 
                      functionName="memberships" 
                      action="write"
                      requiredRoles={['Members_CRUD']}
                      fallback={
                        <Text color="gray.500" fontSize="sm">
                          Alleen lezen
                        </Text>
                      }
                    >
                      <Button
                        size="sm"
                        colorScheme="blue"
                        onClick={() => onEdit(membership)}
                      >
                        Bewerk
                      </Button>
                    </FunctionGuard>
                    <FunctionGuard 
                      user={user} 
                      functionName="memberships" 
                      action="write"
                      requiredRoles={['Members_CRUD']}
                      fallback={null}
                    >
                      <Button
                        size="sm"
                        colorScheme="red"
                        onClick={() => onDelete(membership)}
                      >
                        Verwijder
                      </Button>
                    </FunctionGuard>
                  </HStack>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {memberships.length === 0 && (
        <Text textAlign="center" color="gray.400" py={8}>
          Geen lidmaatschappen gevonden
        </Text>
      )}
    </>
  );
}
