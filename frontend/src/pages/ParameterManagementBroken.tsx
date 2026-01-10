import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, VStack, HStack, Heading, Button, Table, Thead, Tbody, Tr, Th, Td,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  useDisclosure, useToast, IconButton, Select, Text, Alert, AlertIcon, AlertTitle, AlertDescription
} from '@chakra-ui/react';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { FormControl, FormLabel, Input } from '@chakra-ui/react';
import { parameterStore } from '../utils/parameterStore';
import { FunctionPermissionManager, getUserRoles } from '../utils/functionPermissions';
import { ParameterService, ParameterItem } from '../services/parameterService';
import { useParameterManagement } from '../hooks/useParameterManagement';
import { useAccessControl } from '../hooks/useAccessControl';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
  };
  signInUserSession?: {
    accessToken?: {
      jwtToken?: string;
    };
  };
}

interface ParameterManagementProps {
  user: User;
}

function ParameterManagement({ user }: ParameterManagementProps) {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState('Regio');
  const [selectedParent, setSelectedParent] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<ParameterItem | null>(null);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryDescription, setNewCategoryDescription] = useState('');
  const [editingCategory, setEditingCategory] = useState<string | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isCategoryOpen, onOpen: onCategoryOpen, onClose: onCategoryClose } = useDisclosure();
  const toast = useToast();

  // Use custom hooks
  const { hasAccess, accessLoading, userRoles } = useAccessControl(user);
  const { parameters, dataSource, loadParameters } = useParameterManagement(hasAccess, accessLoading);

  // Enhanced role-based access checks for parameter management
  const hasFullMemberAccess = userRoles.includes('System_User_Management') || userRoles.includes('Members_CRUD');
  const hasSystemUserManagementRole = userRoles.includes('System_User_Management');
  const hasNationalChairmanRole = false; // This role doesn't exist in the new system
  const hasNationalSecretaryRole = userRoles.includes('National_Secretary');

  // Get categories and current parameters using service functions
  const categories = ParameterService.getCategories(parameters);
  const currentParameters = ParameterService.getCurrentParameters(parameters, selectedCategory);
  const parentItems = currentParameters.filter(p => !p.parent);
  const getChildren = useCallback((parentId: string) => currentParameters.filter(p => p.parent === parentId), [currentParameters]);

  // Show loading state while checking access
  if (accessLoading) {
    return (
      <Box maxW="6xl" mx="auto" p={6} bg="gray.900" minH="100vh">
        <VStack spacing={6} align="center" justify="center" minH="50vh">
          <Heading color="orange.400">Parameter Beheer</Heading>
          <Text color="gray.300">Toegangsrechten controleren...</Text>
        </VStack>
      </Box>
    );
  }

  // Show access denied message if user doesn't have permission
  if (!hasAccess) {
    return (
      <Box maxW="6xl" mx="auto" p={6} bg="gray.900" minH="100vh">
        <VStack spacing={6} align="stretch">
          <Heading color="orange.400">Parameter Beheer</Heading>
          
          <Alert status="error" bg="red.800" borderColor="red.600" border="1px">
            <AlertIcon color="red.300" />
            <Box>
              <AlertTitle color="red.300">Toegang geweigerd!</AlertTitle>
              <AlertDescription color="red.200">
                Je hebt geen toestemming om parameters te beheren. Deze functionaliteit is alleen beschikbaar voor beheerders.
                <br /><br />
                <strong>Je huidige rollen:</strong> {userRoles.length > 0 ? userRoles.join(', ') : 'Geen rollen toegewezen'}
                <br /><br />
                <strong>Vereiste rollen:</strong> System_User_Management, System_CRUD, Webmaster, Members_CRUD, National_Chairman, National_Secretary, hdcnWebmaster, of hdcnLedenadministratie
                <br /><br />
                Neem contact op met een systeembeheerder als je denkt dat je toegang zou moeten hebben.
              </AlertDescription>
            </Box>
          </Alert>

          <Button 
            colorScheme="orange" 
            onClick={() => navigate('/dashboard')}
            alignSelf="flex-start"
          >
            Terug naar Dashboard
          </Button>
        </VStack>
      </Box>
    );
  }

  return (
    <Box maxW="6xl" mx="auto" p={6} bg="gray.900" minH="100vh">
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between">
          <Heading color="orange.400">Parameter Beheer</Heading>
          <HStack spacing={4}>
            {/* Enhanced role indicator for different admin levels */}
            <Box 
              bg={hasFullMemberAccess ? 'green.600' : hasSystemUserManagementRole ? 'blue.600' : 'yellow.600'} 
              px={3} 
              py={1} 
              borderRadius="md"
              color="white"
              fontSize="sm"
            >
              {hasFullMemberAccess ? '🔧 Volledige Toegang' : 
               hasSystemUserManagementRole ? '👥 Gebruikersbeheer' : 
               hasNationalChairmanRole ? '👑 Voorzitter' :
               hasNationalSecretaryRole ? '📝 Secretaris' : '📋 Beperkte Toegang'}
            </Box>
            
            <Text fontSize="sm" color="gray.400">
              Data bron: {dataSource}
            </Text>
          </HStack>
        </HStack>

        {/* Category Selection */}
        <HStack spacing={4}>
          <Text color="orange.300" fontWeight="bold">Categorie:</Text>
          <Select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            bg="gray.800"
            color="orange.400"
            borderColor="orange.400"
            maxW="300px"
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </Select>
          
          <Button
            colorScheme="orange"
            size="sm"
            onClick={loadParameters}
          >
            🔄 Vernieuwen
          </Button>
        </HStack>

        {/* Parameters Table */}
        <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="auto">
          <Table variant="simple">
            <Thead bg="gray.700">
              <Tr>
                <Th color="orange.300">ID</Th>
                <Th color="orange.300">Waarde</Th>
                <Th color="orange.300">Parent</Th>
                <Th color="orange.300">Acties</Th>
              </Tr>
            </Thead>
            <Tbody>
              {parentItems.map((item, index) => (
                <React.Fragment key={item.id || index}>
                  <Tr>
                    <Td color="white">{item.id}</Td>
                    <Td color="white" maxW="300px" isTruncated>
                      {item.displayValue || item.value}
                    </Td>
                    <Td color="gray.400">-</Td>
                    <Td>
                      <HStack spacing={2}>
                        <IconButton
                          size="sm"
                          colorScheme="blue"
                          icon={<span>✏️</span>}
                          onClick={() => {
                            setEditingItem(item);
                            onOpen();
                          }}
                          aria-label="Bewerk"
                        />
                        <IconButton
                          size="sm"
                          colorScheme="red"
                          icon={<span>🗑️</span>}
                          onClick={() => {
                            // Delete functionality would go here
                            toast({
                              title: 'Verwijderen',
                              description: 'Verwijder functionaliteit nog niet geïmplementeerd',
                              status: 'info'
                            });
                          }}
                          aria-label="Verwijder"
                        />
                      </HStack>
                    </Td>
                  </Tr>
                  {getChildren(item.id || index.toString()).map((child, childIndex) => (
                    <Tr key={`${item.id}-${child.id || childIndex}`} bg="gray.700">
                      <Td color="gray.300" pl={8}>
                        ↳ {child.id}
                      </Td>
                      <Td color="gray.300" maxW="300px" isTruncated>
                        {child.displayValue || child.value}
                      </Td>
                      <Td color="gray.400">{item.id}</Td>
                      <Td>
                        <HStack spacing={2}>
                          <IconButton
                            size="sm"
                            colorScheme="blue"
                            icon={<span>✏️</span>}
                            onClick={() => {
                              setEditingItem(child);
                              onOpen();
                            }}
                            aria-label="Bewerk"
                          />
                          <IconButton
                            size="sm"
                            colorScheme="red"
                            icon={<span>🗑️</span>}
                            onClick={() => {
                              // Delete functionality would go here
                              toast({
                                title: 'Verwijderen',
                                description: 'Verwijder functionaliteit nog niet geïmplementeerd',
                                status: 'info'
                              });
                            }}
                            aria-label="Verwijder"
                          />
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </React.Fragment>
              ))}
            </Tbody>
          </Table>
        </Box>

        {currentParameters.length === 0 && (
          <Text textAlign="center" color="gray.400" py={8}>
            Geen parameters gevonden voor categorie "{selectedCategory}".
          </Text>
        )}
      </VStack>

      {/* Edit Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
          <ModalHeader color="orange.400">Parameter Bewerken</ModalHeader>
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel color="orange.300">ID</FormLabel>
                <Input
                  value={editingItem?.id || ''}
                  isReadOnly
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>
              <FormControl>
                <FormLabel color="orange.300">Waarde</FormLabel>
                <Input
                  value={editingItem?.value || ''}
                  onChange={(e) => {
                    if (editingItem) {
                      setEditingItem({
                        ...editingItem,
                        value: e.target.value
                      });
                    }
                  }}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Annuleren
            </Button>
            <Button
              colorScheme="orange"
              onClick={() => {
                // Save functionality would go here
                toast({
                  title: 'Opslaan',
                  description: 'Opslaan functionaliteit nog niet geïmplementeerd',
                  status: 'info'
                });
                onClose();
              }}
            >
              Opslaan
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}

export default ParameterManagement;