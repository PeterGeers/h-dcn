import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Button, Table, Thead, Tbody, Tr, Th, Td,
  useToast, Text, Badge, useDisclosure
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import cognitoService from '../services/cognitoService';
import GroupModal from './GroupModal';
import GroupDetailModal from './GroupDetailModal';

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
  const { isOpen: isCreateOpen, onOpen: onCreateOpen, onClose: onCreateClose } = useDisclosure();
  const { isOpen: isDetailOpen, onOpen: onDetailOpen, onClose: onDetailClose } = useDisclosure();
  const toast = useToast();

  useEffect(() => {
    loadGroups();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      
      // Sort groups alphabetically by GroupName (ascending)
      groupsWithCounts.sort((a, b) => a.GroupName.localeCompare(b.GroupName));
      
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

  const openDetailModal = (group: CognitoGroup) => {
    setSelectedGroup(group);
    onDetailOpen();
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
          onClick={onCreateOpen}
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
            </Tr>
          </Thead>
          <Tbody>
            {groups.map((group) => (
              <Tr
                key={group.GroupName}
                onClick={() => openDetailModal(group)}
                _hover={{ bg: "gray.700", cursor: "pointer" }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter") openDetailModal(group); }}
              >
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
        isOpen={isCreateOpen}
        onClose={onCreateClose}
        group={null}
        onSave={loadGroups}
      />

      <GroupDetailModal
        isOpen={isDetailOpen}
        onClose={onDetailClose}
        group={selectedGroup}
        onGroupDeleted={loadGroups}
      />
    </VStack>
  );
}

export default GroupManagement;
