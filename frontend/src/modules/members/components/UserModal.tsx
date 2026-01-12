import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, FormControl, FormLabel, Input, SimpleGrid, useToast,
  Checkbox, CheckboxGroup, Stack
} from '@chakra-ui/react';
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
}

interface UserFormData {
  username: string;
  email: string;
  given_name: string;
  family_name: string;
  phone_number: string;
}

interface UserModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: CognitoUser | null;
  groups: CognitoGroup[];
  onSave: () => void;
}

function UserModal({ isOpen, onClose, user, groups, onSave }: UserModalProps) {
  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    email: '',
    given_name: '',
    family_name: '',
    phone_number: ''
  });
  const [userGroups, setUserGroups] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (user) {
      const getUserAttribute = (attributeName: string) => {
        return user.Attributes?.find(attr => attr.Name === attributeName)?.Value || '';
      };

      setFormData({
        username: user.Username || '',
        email: getUserAttribute('email'),
        given_name: getUserAttribute('given_name'),
        family_name: getUserAttribute('family_name'),
        phone_number: getUserAttribute('phone_number')
      });

      loadUserGroups(user.Username);
    } else {
      setFormData({
        username: '',
        email: '',
        given_name: '',
        family_name: '',
        phone_number: ''
      });
      setUserGroups([]);
    }
  }, [user]);

  const loadUserGroups = async (username: string) => {
    try {
      const response = await cognitoService.getUserGroups(username);
      setUserGroups(response.Groups?.map(g => g.GroupName) || []);
    } catch (error: any) {
      console.error('Error loading user groups:', error);
    }
  };

  const handleChange = (field: keyof UserFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleGroupChange = (selectedGroups: string[]) => {
    setUserGroups(selectedGroups);
  };

  const handleSubmit = async () => {
    if (!formData.username || !formData.email) {
      toast({
        title: 'Vereiste velden',
        description: 'Gebruikersnaam en email zijn verplicht',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    setIsLoading(true);
    try {
      if (user) {
        // Update existing user
        const attributes = {
          email: formData.email,
          given_name: formData.given_name,
          family_name: formData.family_name,
          phone_number: formData.phone_number
        };

        await cognitoService.updateUserAttributes(user.Username, attributes);

        // Update groups
        const currentGroups = await cognitoService.getUserGroups(user.Username);
        const currentGroupNames = currentGroups.Groups?.map(g => g.GroupName) || [];

        // Remove from old groups
        for (const groupName of currentGroupNames) {
          if (!userGroups.includes(groupName)) {
            await cognitoService.removeUserFromGroup(user.Username, groupName);
          }
        }

        // Add to new groups
        for (const groupName of userGroups) {
          if (!currentGroupNames.includes(groupName)) {
            await cognitoService.addUserToGroup(user.Username, groupName);
          }
        }
      } else {
        // Create new user - passwordless authentication
        const attributes = {
          given_name: formData.given_name,
          family_name: formData.family_name,
          phone_number: formData.phone_number
        };

        await cognitoService.createUser(formData.username, formData.email, attributes);

        // Add to groups
        for (const groupName of userGroups) {
          await cognitoService.addUserToGroup(formData.username, groupName);
        }
      }

      onSave();
      onClose();
      toast({
        title: user ? 'Gebruiker bijgewerkt' : 'Gebruiker aangemaakt',
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      toast({
        title: 'Fout bij opslaan',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          {user ? 'Gebruiker Bewerken' : 'Nieuwe Gebruiker'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <SimpleGrid columns={2} spacing={4} w="full">
              <FormControl isRequired>
                <FormLabel color="orange.300">Gebruikersnaam</FormLabel>
                <Input
                  value={formData.username}
                  onChange={(e) => handleChange('username', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                  isDisabled={!!user}
                />
              </FormControl>
              
              <FormControl isRequired>
                <FormLabel color="orange.300">Email</FormLabel>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Voornaam</FormLabel>
                <Input
                  value={formData.given_name}
                  onChange={(e) => handleChange('given_name', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Achternaam</FormLabel>
                <Input
                  value={formData.family_name}
                  onChange={(e) => handleChange('family_name', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Telefoonnummer</FormLabel>
                <Input
                  value={formData.phone_number}
                  onChange={(e) => handleChange('phone_number', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>
            </SimpleGrid>

            <FormControl>
              <FormLabel color="orange.300">Groepen</FormLabel>
              <CheckboxGroup value={userGroups} onChange={handleGroupChange}>
                <Stack direction="row" wrap="wrap">
                  {groups
                    .sort((a, b) => a.GroupName.localeCompare(b.GroupName))
                    .map((group) => (
                      <Checkbox
                        key={group.GroupName}
                        value={group.GroupName}
                        colorScheme="orange"
                      >
                        {group.GroupName}
                      </Checkbox>
                    ))}
                </Stack>
              </CheckboxGroup>
            </FormControl>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Annuleren
          </Button>
          <Button
            colorScheme="orange"
            onClick={handleSubmit}
            isLoading={isLoading}
          >
            {user ? 'Bijwerken' : 'Aanmaken'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default UserModal;