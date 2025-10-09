import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, FormControl, FormLabel, Input, Textarea, useToast
} from '@chakra-ui/react';
import cognitoService from '../services/cognitoService';

function GroupModal({ isOpen, onClose, group, onSave }) {
  const [formData, setFormData] = useState({
    groupName: '',
    description: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (group) {
      setFormData({
        groupName: group.GroupName || '',
        description: group.Description || ''
      });
    } else {
      setFormData({
        groupName: '',
        description: ''
      });
    }
  }, [group]);

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async () => {
    if (!formData.groupName) {
      toast({
        title: 'Vereiste velden',
        description: 'Groepsnaam is verplicht',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    setIsLoading(true);
    try {
      if (!group) {
        // Create new group
        await cognitoService.createGroup(formData.groupName, formData.description);
        toast({
          title: 'Groep aangemaakt',
          status: 'success',
          duration: 3000,
        });
      } else {
        // Note: Cognito doesn't support updating group description after creation
        toast({
          title: 'Groep kan niet worden bijgewerkt',
          description: 'Cognito ondersteunt geen wijziging van groepsbeschrijving na aanmaak',
          status: 'warning',
          duration: 5000,
        });
      }

      onSave();
      onClose();
    } catch (error) {
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
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          {group ? 'Groep Bekijken' : 'Nieuwe Groep'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel color="orange.300">Groepsnaam</FormLabel>
              <Input
                value={formData.groupName}
                onChange={(e) => handleChange('groupName', e.target.value)}
                bg="gray.700"
                borderColor="orange.400"
                isDisabled={!!group}
              />
            </FormControl>
            
            <FormControl>
              <FormLabel color="orange.300">Beschrijving</FormLabel>
              <Textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                bg="gray.700"
                borderColor="orange.400"
                rows={3}
                isDisabled={!!group}
              />
            </FormControl>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            {group ? 'Sluiten' : 'Annuleren'}
          </Button>
          {!group && (
            <Button
              colorScheme="orange"
              onClick={handleSubmit}
              isLoading={isLoading}
            >
              Aanmaken
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default GroupModal;