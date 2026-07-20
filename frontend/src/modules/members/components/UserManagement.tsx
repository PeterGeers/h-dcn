import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, VStack, HStack, Button, Table, Thead, Tbody, Tr, Td,
  Badge, useToast, Text, useDisclosure
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import cognitoService from '../services/cognitoService';
import UserModal from './UserModal';
import { useFilterableTable } from '../../../hooks/useFilterableTable';
import { FilterableHeader } from '../../../components/filters';

interface CognitoAttribute {
  Name: string;
  Value: string;
}

interface CognitoUser {
  Username: string;
  Enabled: boolean;
  UserCreateDate?: string;
  Attributes?: CognitoAttribute[];
}

interface CognitoGroup {
  GroupName: string;
  Description?: string;
}

interface UserManagementProps {
  user: any;
}

function UserManagement({ user }: UserManagementProps) {
  const [users, setUsers] = useState<CognitoUser[]>([]);
  const [groups, setGroups] = useState<CognitoGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<CognitoUser | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getUserAttribute = (user: CognitoUser, attributeName: string) => {
    return user.Attributes?.find(attr => attr.Name === attributeName)?.Value || '';
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [usersResponse, groupsResponse] = await Promise.all([
        cognitoService.listUsers(),
        cognitoService.listGroups()
      ]);
      setUsers(usersResponse.Users || []);
      setGroups(groupsResponse.Groups || []);
    } catch (error: any) {
      toast({
        title: 'Fout bij laden gebruikers',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  // Transform Cognito users to flat records for the framework
  const tableData = useMemo(() => {
    return users.map(u => ({
      ...u,
      email: getUserAttribute(u, 'email'),
      fullName: `${getUserAttribute(u, 'given_name')} ${getUserAttribute(u, 'family_name')}`.trim(),
      status: u.Enabled ? 'Actief' : 'Uitgeschakeld',
      created: u.UserCreateDate || '',
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [users]);

  const INITIAL_FILTERS = { email: '', fullName: '', status: '', created: '' };

  const { filters, setFilter, handleSort, sortField, sortDirection, processedData } =
    useFilterableTable(tableData, {
      initialFilters: INITIAL_FILTERS,
      defaultSort: { field: 'email', direction: 'asc' },
    });

  const filteredUsers = processedData as (CognitoUser & Record<string, unknown>)[];

  const openModal = (userRecord: CognitoUser) => {
    setSelectedUser(userRecord);
    onOpen();
  };

  const handleDeleteUser = async (username: string) => {
    try {
      await cognitoService.deleteUser(username);
      loadData();
      toast({
        title: 'Gebruiker verwijderd',
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      toast({
        title: 'Fout bij verwijderen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleToggleUser = async (username: string, enabled: boolean) => {
    try {
      if (enabled) {
        await cognitoService.disableUser(username);
      } else {
        await cognitoService.enableUser(username);
      }
      loadData();
      toast({
        title: enabled ? 'Gebruiker uitgeschakeld' : 'Gebruiker ingeschakeld',
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      toast({
        title: 'Fout bij wijzigen status',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Text color="orange.400">Gebruikers laden...</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      <HStack justify="flex-end">
        <Text color="orange.400" fontWeight="bold">
          Totaal: {users.length} accounts
        </Text>
        <Button
          leftIcon={<AddIcon />}
          colorScheme="orange"
          onClick={() => {
            setSelectedUser(null);
            onOpen();
          }}
        >
          Nieuwe Gebruiker
        </Button>
      </HStack>

      <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
        <Table variant="simple">
          <Thead bg="gray.700">
            <Tr>
              <FilterableHeader
                label="Email"
                filterValue={filters.email}
                onFilterChange={(v) => setFilter('email', v)}
                sortable
                sortDirection={sortField === 'email' ? sortDirection : null}
                onSort={() => handleSort('email')}
                w="200px"
              />
              <FilterableHeader
                label="Naam"
                filterValue={filters.fullName}
                onFilterChange={(v) => setFilter('fullName', v)}
                sortable
                sortDirection={sortField === 'fullName' ? sortDirection : null}
                onSort={() => handleSort('fullName')}
                w="150px"
              />
              <FilterableHeader
                label="Status"
                filterValue={filters.status}
                onFilterChange={(v) => setFilter('status', v)}
                sortable
                sortDirection={sortField === 'status' ? sortDirection : null}
                onSort={() => handleSort('status')}
                w="100px"
              />
              <FilterableHeader
                label="Aangemaakt"
                filterValue={filters.created}
                onFilterChange={(v) => setFilter('created', v)}
                sortable
                sortDirection={sortField === 'created' ? sortDirection : null}
                onSort={() => handleSort('created')}
                w="120px"
              />
            </Tr>
          </Thead>
          <Tbody>
            {filteredUsers.map((user) => (
              <Tr
                key={user.Username}
                onClick={() => openModal(user)}
                _hover={{ bg: 'gray.700', cursor: 'pointer' }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') openModal(user);
                }}
              >
                <Td color="white">{user.email as string}</Td>
                <Td color="white">{user.fullName as string}</Td>
                <Td>
                  <Badge colorScheme={user.Enabled ? 'green' : 'red'}>
                    {user.status as string}
                  </Badge>
                </Td>
                <Td color="white">
                  {user.UserCreateDate ? new Date(user.UserCreateDate).toLocaleDateString('nl-NL') : '-'}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {filteredUsers.length === 0 && (
        <Text color="gray.400" textAlign="center" py={8}>
          Geen gebruikers gevonden
        </Text>
      )}

      <UserModal
        isOpen={isOpen}
        onClose={onClose}
        user={selectedUser}
        groups={groups}
        onSave={loadData}
        onDelete={handleDeleteUser}
        onToggleEnabled={handleToggleUser}
      />
    </VStack>
  );
}

export default UserManagement;