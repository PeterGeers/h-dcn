import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Button, Table, Thead, Tbody, Tr, Th, Td,
  Input, useToast, Text, IconButton, Badge, useDisclosure
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon, ViewIcon } from '@chakra-ui/icons';
import cognitoService from '../services/cognitoService';
import GroupModal from './GroupModal';
import GroupMembersModal from './GroupMembersModal';

interface CognitoGroup {
  GroupName: string;
  Description?: string;
  CreationDate?: string;
  memberCount: number;
}

interface GroupManagementProps {
  user: any;
}

function GroupManagement({ user }: GroupManagementProps) {
  const [groups, setGroups] = useState<CognitoGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState<CognitoGroup | null>(null);
  const [viewingMembers, setViewingMembers] = useState<CognitoGroup | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isMembersOpen, onOpen: onMembersOpen, onClose: onMembersClose } = useDisclosure();
  const toast = useToast();

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const response = await cognitoService.listGroups();
      
      // Load member count for each group
      const groupsWithCounts: CognitoGroup[] = [];
      
      for (const group of response.Groups || []) {
        try {
          const membersResponse = await cognitoService.getUsersInGroup(group.GroupName);
          groupsWithCounts.push({
            ...group,
            memberCount: membersResponse.Users?.length || 0
          });
        } catch (error) {
          console.error(`Error loading members for group ${group.GroupName}:`, error);
          groupsWithCounts.push({
            ...group,
            memberCount: 0
          });
        }
      }
      
      setGroups(groupsWithCounts);
    } catch (error: any) {
      toast({
        title: 'Fout bij laden groepen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteGroup = async (groupName: string) => {
    if (!window.confirm(`Weet je zeker dat je groep "${groupName}" wilt verwijderen?`)) return;
    
    try {
      await cognitoService.deleteGroup(groupName);
      loadGroups();
      toast({
        title: 'Groep verwijderd',
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

  const handleViewMembers = (group: CognitoGroup) => {
    setViewingMembers(group);
    onMembersOpen();
  };

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Text color="orange.400">Groepen laden...</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      <HStack justify="space-between">
        <Text color="orange.400" fontSize="lg" fontWeight="bold">
          Gebruikersgroepen ({groups.length})
        </Text>
        <Button
          leftIcon={<AddIcon />}
          colorScheme="orange"
          onClick={() => {
            setSelectedGroup(null);
            onOpen();
          }}
        >
          Nieuwe Groep
        </Button>
      </HStack>

      <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
        <Table variant="simple">
          <Thead bg="gray.700">
            <Tr>
              <Th color="orange.300">Groepsnaam</Th>
              <Th color="orange.300">Beschrijving</Th>
              <Th color="orange.300">Leden</Th>
              <Th color="orange.300">Aangemaakt</Th>
              <Th color="orange.300">Acties</Th>
            </Tr>
          </Thead>
          <Tbody>
            {groups.map((group) => (
              <Tr key={group.GroupName}>
                <Td color="white" fontWeight="bold">{group.GroupName}</Td>
                <Td color="white">{group.Description || '-'}</Td>
                <Td>
                  <Badge colorScheme="blue" variant="solid">
                    {group.memberCount} leden
                  </Badge>
                </Td>
                <Td color="white">
                  {group.CreationDate ? new Date(group.CreationDate).toLocaleDateString('nl-NL') : '-'}
                </Td>
                <Td>
                  <HStack spacing={2}>
                    <IconButton
                      icon={<ViewIcon />}
                      size="sm"
                      colorScheme="blue"
                      onClick={() => handleViewMembers(group)}
                      title="Bekijk leden"
                      aria-label="Bekijk leden"
                    />
                    <IconButton
                      icon={<EditIcon />}
                      size="sm"
                      colorScheme="green"
                      onClick={() => {
                        setSelectedGroup(group);
                        onOpen();
                      }}
                      title="Bewerken"
                      aria-label="Bewerken"
                    />
                    <IconButton
                      icon={<DeleteIcon />}
                      size="sm"
                      colorScheme="red"
                      onClick={() => handleDeleteGroup(group.GroupName)}
                      title="Verwijderen"
                      aria-label="Verwijderen"
                      isDisabled={group.memberCount > 0}
                    />
                  </HStack>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {groups.length === 0 && (
        <Text color="gray.400" textAlign="center" py={8}>
          Geen groepen gevonden
        </Text>
      )}

      <GroupModal
        isOpen={isOpen}
        onClose={onClose}
        group={selectedGroup}
        onSave={loadGroups}
      />

      <GroupMembersModal
        isOpen={isMembersOpen}
        onClose={onMembersClose}
        group={viewingMembers}
      />
    </VStack>
  );
}

export default GroupManagement;