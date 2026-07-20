import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, Table, Thead, Tbody, Tr, Th, Td, Text, Badge, IconButton, useToast,
  FormControl, FormLabel, Input, Textarea, Divider, HStack
} from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
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
  memberCount: number;
}

interface GroupDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  group: CognitoGroup | null;
  onGroupDeleted: () => void;
}

function GroupDetailModal({ isOpen, onClose, group, onGroupDeleted }: GroupDetailModalProps) {
  const [members, setMembers] = useState<CognitoUser[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const toast = useToast();
  const { t } = useTranslation('members');

  useEffect(() => {
    if (group && isOpen) {
      loadMembers();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [group, isOpen]);

  const loadMembers = async () => {
    if (!group) return;

    try {
      setLoadingMembers(true);
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
      setLoadingMembers(false);
    }
  };

  const getUserAttribute = (user: CognitoUser, attributeName: string) => {
    return user.Attributes?.find(attr => attr.Name === attributeName)?.Value || '';
  };

  const handleRemoveFromGroup = async (username: string) => {
    if (!group) return;
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

  const handleDeleteGroup = async () => {
    if (!group) return;
    if (!window.confirm(`Weet je zeker dat je groep "${group.GroupName}" wilt verwijderen?`)) return;

    try {
      setIsDeleting(true);
      await cognitoService.deleteGroup(group.GroupName);
      toast({
        title: 'Groep verwijderd',
        status: 'success',
        duration: 3000,
      });
      onClose();
      onGroupDeleted();
    } catch (error: any) {
      toast({
        title: 'Fout bij verwijderen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsDeleting(false);
    }
  };

  if (!group) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          {group.GroupName}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <FormControl>
              <FormLabel color="orange.300">{t('form.group_name')}</FormLabel>
              <Input
                value={group.GroupName}
                bg="gray.700"
                borderColor="orange.400"
                isReadOnly
              />
            </FormControl>

            <FormControl>
              <FormLabel color="orange.300">{t('form.description')}</FormLabel>
              <Textarea
                value={group.Description || '-'}
                bg="gray.700"
                borderColor="orange.400"
                rows={2}
                isReadOnly
              />
            </FormControl>

            <HStack spacing={4}>
              <Badge colorScheme="blue" variant="solid" px={2} py={1}>
                {group.memberCount} leden
              </Badge>
              {group.CreationDate && (
                <Text color="gray.400" fontSize="sm">
                  Aangemaakt: {new Date(group.CreationDate).toLocaleDateString('nl-NL')}
                </Text>
              )}
            </HStack>

            <Divider borderColor="gray.600" />

            <Text color="orange.300" fontWeight="bold" fontSize="sm">
              Leden van deze groep
            </Text>

            {loadingMembers ? (
              <Text color="orange.400" textAlign="center">Leden laden...</Text>
            ) : members.length > 0 ? (
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
              <Text color="gray.400" textAlign="center" py={4}>
                Geen leden in deze groep
              </Text>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <HStack spacing={3} w="100%" justify="space-between">
            <Button
              colorScheme="red"
              variant="outline"
              leftIcon={<DeleteIcon />}
              onClick={handleDeleteGroup}
              isLoading={isDeleting}
              isDisabled={group.memberCount > 0}
              title={group.memberCount > 0 ? 'Groep kan niet worden verwijderd zolang er leden zijn' : undefined}
            >
              Groep verwijderen
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Sluiten
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default GroupDetailModal;
