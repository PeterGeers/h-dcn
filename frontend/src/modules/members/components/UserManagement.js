import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Button, Table, Thead, Tbody, Tr, Th, Td,
  Input, Badge, useToast, Text, IconButton, Select, useDisclosure
} from '@chakra-ui/react';
import {
  Menu, MenuButton, MenuList, MenuItem
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon, SearchIcon, ChevronDownIcon } from '@chakra-ui/icons';
import cognitoService from '../services/cognitoService';
import UserModal from './UserModal';


function UserManagement({ user }) {
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [usersResponse, groupsResponse] = await Promise.all([
        cognitoService.listUsers(),
        cognitoService.listGroups()
      ]);
      setUsers(usersResponse.Users || []);
      setGroups(groupsResponse.Groups || []);
    } catch (error) {
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

  const filteredUsers = users.filter(user =>
    user.Username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.Attributes?.find(attr => attr.Name === 'email')?.Value?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getUserAttribute = (user, attributeName) => {
    return user.Attributes?.find(attr => attr.Name === attributeName)?.Value || '';
  };

  const handleDeleteUser = async (username) => {
    if (!window.confirm(`Weet je zeker dat je gebruiker "${username}" wilt verwijderen?`)) return;
    
    try {
      await cognitoService.deleteUser(username);
      loadData();
      toast({
        title: 'Gebruiker verwijderd',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: 'Fout bij verwijderen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleToggleUser = async (username, enabled) => {
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
    } catch (error) {
      toast({
        title: 'Fout bij wijzigen status',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleAddToGroup = async (username, groupName) => {
    try {
      await cognitoService.addUserToGroup(username, groupName);
      loadData();
      toast({
        title: 'Gebruiker toegevoegd aan groep',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: 'Fout bij toevoegen aan groep',
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
      <HStack justify="space-between">
        <HStack flex={1}>
          <SearchIcon color="orange.400" />
          <Input
            placeholder="Zoek gebruikers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            bg="gray.800"
            color="white"
            borderColor="orange.400"
          />
        </HStack>
        <HStack spacing={4}>
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
      </HStack>

      <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
        <Table variant="simple">
          <Thead bg="gray.700">
            <Tr>
              <Th color="orange.300">Cognito ID</Th>
              <Th color="orange.300">Email</Th>
              <Th color="orange.300">Status</Th>
              <Th color="orange.300">Aangemaakt</Th>
              <Th color="orange.300">Acties</Th>
            </Tr>
          </Thead>
          <Tbody>
            {filteredUsers.map((user) => (
              <Tr key={user.Username}>
                <Td color="white">{user.Username}</Td>
                <Td color="white">{getUserAttribute(user, 'email')}</Td>
                <Td>
                  <Badge colorScheme={user.Enabled ? 'green' : 'red'}>
                    {user.Enabled ? 'Actief' : 'Uitgeschakeld'}
                  </Badge>
                </Td>
                <Td color="white">
                  {user.UserCreateDate ? new Date(user.UserCreateDate).toLocaleDateString('nl-NL') : '-'}
                </Td>
                <Td>
                  <HStack spacing={2}>
                    <IconButton
                      icon={<EditIcon />}
                      size="sm"
                      colorScheme="blue"
                      onClick={() => {
                        setSelectedUser(user);
                        onOpen();
                      }}
                      title="Bewerken"
                    />
                    <Menu>
                      <MenuButton
                        as={IconButton}
                        icon={<ChevronDownIcon />}
                        size="sm"
                        colorScheme="green"
                        title="Groep toevoegen"
                      />
                      <MenuList bg="gray.700">
                        {groups.map((group) => (
                          <MenuItem
                            key={group.GroupName}
                            onClick={() => handleAddToGroup(user.Username, group.GroupName)}
                            bg="gray.700"
                            color="white"
                            _hover={{ bg: 'gray.600' }}
                          >
                            {group.GroupName}
                          </MenuItem>
                        ))}
                      </MenuList>
                    </Menu>
                    <Button
                      size="sm"
                      colorScheme={user.Enabled ? 'yellow' : 'green'}
                      onClick={() => handleToggleUser(user.Username, user.Enabled)}
                    >
                      {user.Enabled ? 'Uitschakelen' : 'Inschakelen'}
                    </Button>
                    <IconButton
                      icon={<DeleteIcon />}
                      size="sm"
                      colorScheme="red"
                      onClick={() => handleDeleteUser(user.Username)}
                      title="Verwijderen"
                    />
                  </HStack>
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
      />
    </VStack>
  );
}

export default UserManagement;