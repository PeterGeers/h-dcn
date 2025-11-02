import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, Table, Thead, Tbody, Tr, Th, Td, Text, IconButton, useToast
} from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import cognitoService from '../services/cognitoService';

interface CognitoAttribute {
  Name: string;
  Value: string;
}

interface CognitoUser {
  Username: string;
  Attributes?: CognitoAttribute[];
}

interface CognitoGroup {
  GroupName: string;
  Description?: string;
  CreationDate?: string;
  memberCount?: number;
}

interface GroupMembersModalProps {
  isOpen: boolean;
  onClose: () => void;
  group: CognitoGroup | null;
}

function GroupMembersModal({ isOpen, onClose, group }: GroupMembersModalProps) {
  const [members, setMembers] = useState<CognitoUser[]>([]);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (group && isOpen) {
      loadMembers();
    }
  }, [group, isOpen]);

  const loadMembers = async () => {
    if (!group) return;
    
    try {
      setLoading(true);
      const response = await cognitoService.getUsersInGroup(group.GroupName);
      setMembers(response.Users || []);
    } catch (error: any) {
      toast({
        title: 'Fout bij laden leden',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const getUserAttribute = (user: CognitoUser, attributeName: string) => {
    return user.Attributes?.find(attr => attr.Name === attributeName)?.Value || '';
  };

  const handleRemoveFromGroup = async (username: string) => {
    if (!window.confirm(`Weet je zeker dat je ${username} uit groep "${group.GroupName}" wilt verwijderen?`)) return;
    
    try {
      await cognitoService.removeUserFromGroup(username, group.GroupName);
      loadMembers();
      toast({
        title: 'Gebruiker verwijderd uit groep',
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

  if (!group) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          Leden van groep: {group.GroupName}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {loading ? (
            <Text color="orange.400" textAlign="center">Leden laden...</Text>
          ) : (
            <VStack spacing={4} align="stretch">
              {members.length > 0 ? (
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th color="orange.300">Gebruikersnaam</Th>
                      <Th color="orange.300">Email</Th>
                      <Th color="orange.300">Naam</Th>
                      <Th color="orange.300">Acties</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {members.map((member) => (
                      <Tr key={member.Username}>
                        <Td color="white">{member.Username}</Td>
                        <Td color="white">{getUserAttribute(member, 'email')}</Td>
                        <Td color="white">
                          {`${getUserAttribute(member, 'given_name')} ${getUserAttribute(member, 'family_name')}`.trim() || '-'}
                        </Td>
                        <Td>
                          <IconButton
                            icon={<DeleteIcon />}
                            size="sm"
                            colorScheme="red"
                            onClick={() => handleRemoveFromGroup(member.Username)}
                            title="Verwijder uit groep"
                            aria-label="Verwijder uit groep"
                          />
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              ) : (
                <Text color="gray.400" textAlign="center" py={8}>
                  Geen leden in deze groep
                </Text>
              )}
            </VStack>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" onClick={onClose}>
            Sluiten
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default GroupMembersModal;