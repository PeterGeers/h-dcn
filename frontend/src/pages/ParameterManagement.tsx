import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, VStack, HStack, Heading, Button, Table, Thead, Tbody, Tr, Th, Td,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  useDisclosure, useToast, IconButton, Select, Text, Alert, AlertIcon, AlertTitle, AlertDescription,
  FormControl, FormLabel, Input, Textarea
} from '@chakra-ui/react';
import { getUserRoles } from '../utils/functionPermissions';
import { ParameterService, ParameterItem } from '../services/parameterService';
import { useParameterManagement } from '../hooks/useParameterManagement';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
  };
}

interface ParameterManagementProps {
  user: User;
}

function ParameterManagement({ user }: ParameterManagementProps) {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState('Regio');
  const [editingItem, setEditingItem] = useState<ParameterItem | null>(null);
  const [originalItemId, setOriginalItemId] = useState<string | null>(null);
  const [hasAccess, setHasAccess] = useState<boolean>(false);
  const [accessLoading, setAccessLoading] = useState<boolean>(true);
  const [userRoles, setUserRoles] = useState<string[]>([]);
  const [newCategoryName, setNewCategoryName] = useState<string>('');
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { 
    isOpen: isCategoryModalOpen, 
    onOpen: onCategoryModalOpen, 
    onClose: onCategoryModalClose 
  } = useDisclosure();
  const toast = useToast();

  // Check access permissions
  React.useEffect(() => {
    const checkAccess = () => {
      try {
        setAccessLoading(true);
        
        // Extract user roles from Cognito JWT token
        const roles = getUserRoles(user);
        setUserRoles(roles);
        
        // Check for administrative roles - NEW ROLE STRUCTURE
        const hasAdminRole = roles.some(role => 
          role === 'System_User_Management' ||
          role === 'System_CRUD' ||
          role === 'Members_CRUD' ||
          role === 'National_Chairman' ||
          role === 'National_Secretary'
        );
        
        setHasAccess(hasAdminRole);
      } catch (error) {
        console.error('❌ ParameterManagement - Permission check failed:', error);
        setHasAccess(false);
      } finally {
        setAccessLoading(false);
      }
    };

    if (user) {
      checkAccess();
    } else {
      setAccessLoading(false);
      setHasAccess(false);
    }
  }, [user]);

  // Use parameter management hook
  const { parameters, dataSource, hasUnsavedChanges, loadParameters, updateParametersLocally, saveParameters } = useParameterManagement(hasAccess, accessLoading);

  // Enhanced role-based access checks for parameter management
  const hasFullMemberAccess = userRoles.includes('Members_CRUD') || userRoles.includes('System_User_Management');
  const hasSystemUserManagementRole = userRoles.includes('System_User_Management');
  const hasNationalChairmanRole = userRoles.includes('National_Chairman');
  const hasNationalSecretaryRole = userRoles.includes('National_Secretary');

  // Handle adding new category
  const handleAddNewCategory = useCallback(() => {
    if (newCategoryName && newCategoryName.trim()) {
      // Add new empty category
      const updatedParameters = { ...parameters };
      updatedParameters[newCategoryName.trim()] = [];
      updateParametersLocally(updatedParameters);
      setSelectedCategory(newCategoryName.trim());
      setNewCategoryName('');
      onCategoryModalClose();
      
      toast({
        title: 'Categorie toegevoegd',
        description: `Categorie "${newCategoryName.trim()}" is succesvol toegevoegd`,
        status: 'success',
        duration: 2000,
        isClosable: true
      });
    }
  }, [newCategoryName, parameters, updateParametersLocally, onCategoryModalClose, toast]);

  const categories = ParameterService.getCategories(parameters);
  const currentParameters = ParameterService.getCurrentParameters(parameters, selectedCategory);
  const parentItems = currentParameters.filter(p => !p.parent);
  const getChildren = useCallback((parentId: string) => currentParameters.filter(p => p.parent === parentId), [currentParameters]);

  // Handle saving edited parameter
  const handleSaveParameter = useCallback(async () => {
    if (!editingItem || !editingItem.value) return;
    
    // For categories that don't use IDs, generate a simple one for internal tracking
    if (!editingItem.id && selectedCategory !== 'Regio') {
      editingItem.id = Date.now().toString();
    }

    try {
      // Update the parameter in the current parameters array
      const updatedParameters = { ...parameters };
      let categoryParams = [...currentParameters];
      
      // Use originalItemId to find the existing item, not the current editingItem.id
      const existingItemIndex = originalItemId 
        ? categoryParams.findIndex(p => p.id === originalItemId)
        : -1;
      
      if (existingItemIndex >= 0) {
        // Update existing item
        categoryParams[existingItemIndex] = { ...editingItem };
      } else {
        // Add new item
        categoryParams.push({ ...editingItem });
      }
      
      updatedParameters[selectedCategory] = categoryParams;
      
      // Update parameters locally (in memory only)
      updateParametersLocally(updatedParameters);
      
      toast({
        title: 'Parameter toegevoegd',
        description: `Parameter "${editingItem.value}" is succesvol toegevoegd`,
        status: 'success',
        duration: 2000,
        isClosable: true
      });
      
      onClose();
      setEditingItem(null);
      setOriginalItemId(null);
    } catch (error: any) {
      console.error('❌ Error saving parameter:', error);
      toast({
        title: 'Fout bij opslaan',
        description: error?.message || 'Onbekende fout bij opslaan parameter',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    }
  }, [editingItem, originalItemId, parameters, currentParameters, selectedCategory, saveParameters, toast, onClose]);

  // Handle deleting parameter
  const handleDeleteParameter = useCallback(async (itemToDelete: ParameterItem) => {
    if (!itemToDelete.id) return;

    try {
      const updatedParameters = { ...parameters };
      let categoryParams = [...currentParameters];
      
      // Remove the item
      categoryParams = categoryParams.filter(p => p.id !== itemToDelete.id);
      updatedParameters[selectedCategory] = categoryParams;
      
      // Update parameters locally (in memory only)
      updateParametersLocally(updatedParameters);
      
      toast({
        title: 'Parameter verwijderd',
        description: `Parameter "${itemToDelete.value}" is succesvol verwijderd`,
        status: 'success',
        duration: 3000,
        isClosable: true
      });
    } catch (error: any) {
      console.error('❌ Error deleting parameter:', error);
      toast({
        title: 'Fout bij verwijderen',
        description: error?.message || 'Onbekende fout bij verwijderen parameter',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    }
  }, [parameters, currentParameters, selectedCategory, saveParameters, toast]);

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
                <strong>Vereiste rollen:</strong> System_User_Management, System_CRUD, Members_CRUD (met regionale toewijzing), National_Chairman, of National_Secretary
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
          <Text fontSize="sm" color="gray.400">
            Data bron: {dataSource}
          </Text>
        </HStack>

        {/* Show error state if parameters can't be loaded */}
        {dataSource === 'Niet beschikbaar' && (
          <Alert status="error" bg="red.900" borderColor="red.500">
            <AlertIcon />
            <Box>
              <AlertTitle>Parameters niet beschikbaar!</AlertTitle>
              <AlertDescription>
                De parameters kunnen momenteel niet worden geladen van de S3 bucket. 
                Controleer uw toegangsrechten of probeer het later opnieuw.
              </AlertDescription>
            </Box>
          </Alert>
        )}

        {/* Only show parameter management interface if data is available */}
        {dataSource !== 'Niet beschikbaar' && dataSource !== 'loading' && (
          <>
            {/* Category Selection and Management */}
            <VStack spacing={4} align="stretch">
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
              colorScheme={hasUnsavedChanges ? "orange" : "gray"}
              size="sm"
              onClick={() => saveParameters()}
              isDisabled={!hasUnsavedChanges}
            >
              💾 {hasUnsavedChanges ? 'Wijzigingen Opslaan' : 'Alles Opgeslagen'}
            </Button>

            <Button
              colorScheme="blue"
              size="sm"
              onClick={onCategoryModalOpen}
            >
              ➕ Nieuwe Categorie
            </Button>

            <Button
              colorScheme="red"
              size="sm"
              onClick={() => {
                if (confirm(`Weet je zeker dat je categorie "${selectedCategory}" wilt verwijderen?`)) {
                  const updatedParameters = { ...parameters };
                  delete updatedParameters[selectedCategory];
                  updateParametersLocally(updatedParameters);
                  setSelectedCategory(categories[0] || 'Regio');
                }
              }}
              isDisabled={['Regio', 'Lidmaatschap', 'Motormerk'].includes(selectedCategory)}
            >
              🗑️ Verwijder Categorie
            </Button>
          </HStack>

          {/* Add new value button for current category */}
          <HStack spacing={4}>
            <Button
              colorScheme="green"
              size="sm"
              onClick={() => {
                setEditingItem({
                  id: '',
                  value: '',
                  parent: null
                });
                setOriginalItemId(null);
                onOpen();
              }}
            >
              ➕ Nieuwe Waarde in {selectedCategory}
            </Button>
            
            {(['Productgroepen'].includes(selectedCategory)) && (
              <Text fontSize="sm" color="gray.400">
                💡 Tip: Gebruik de ➕ knop naast een item om een subitem toe te voegen
              </Text>
            )}
          </HStack>
        </VStack>

        {/* Parameters Table */}
        <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="auto">
          <Table variant="simple">
            <Thead bg="gray.700">
              <Tr>
                {/* Only show ID column for Regio (needed for Cognito) and Function_permissions */}
                {(['Regio', 'Function_permissions'].includes(selectedCategory)) && (
                  <Th color="orange.300">ID</Th>
                )}
                <Th color="orange.300">
                  {selectedCategory === 'Leveropties' ? 'Naam' : 'Waarde'}
                </Th>
                {selectedCategory === 'Leveropties' && (
                  <Th color="orange.300">Kosten</Th>
                )}
                {(['Function_permissions'].includes(selectedCategory)) && (
                  <Th color="orange.300">Parent</Th>
                )}
                <Th color="orange.300" minW="150px">Acties</Th>
              </Tr>
            </Thead>
            <Tbody>
              {parentItems.map((item, index) => (
                <React.Fragment key={item.id || index}>
                  <Tr>
                    {/* Only show ID for Regio (Cognito needs it) and Function_permissions */}
                    {(['Regio', 'Function_permissions'].includes(selectedCategory)) && (
                      <Td color="white">{item.id}</Td>
                    )}
                    <Td color="white" maxW="300px" isTruncated>
                      {selectedCategory === 'Leveropties' 
                        ? (item.name || item.displayValue || item.value)
                        : (item.displayValue || item.value)
                      }
                    </Td>
                    {selectedCategory === 'Leveropties' && (
                      <Td color="white">€{item.cost || '0'}</Td>
                    )}
                    {(['Function_permissions'].includes(selectedCategory)) && (
                      <Td color="gray.400">-</Td>
                    )}
                    <Td>
                      <HStack spacing={2}>
                        <IconButton
                          size="sm"
                          colorScheme="blue"
                          icon={<span>✏️</span>}
                          onClick={() => {
                            setEditingItem(item);
                            setOriginalItemId(item.id); // Store original ID for updates
                            onOpen();
                          }}
                          aria-label="Bewerk"
                        />
                        {/* Add subitem button for categories that support nesting */}
                        {(['Productgroepen'].includes(selectedCategory)) && (
                          <IconButton
                            size="sm"
                            colorScheme="green"
                            icon={<span>➕</span>}
                            onClick={() => {
                              setEditingItem({
                                id: '',
                                value: '',
                                parent: item.id || item.value
                              });
                              setOriginalItemId(null);
                              onOpen();
                            }}
                            aria-label="Subitem toevoegen"
                            title="Subitem toevoegen"
                          />
                        )}
                        <IconButton
                          size="sm"
                          colorScheme="red"
                          icon={<span>🗑️</span>}
                          onClick={() => handleDeleteParameter(item)}
                          aria-label="Verwijder"
                        />
                      </HStack>
                    </Td>
                  </Tr>
                  {getChildren(item.id || index.toString()).map((child, childIndex) => (
                    <Tr key={`${item.id}-${child.id || childIndex}`} bg="gray.700">
                      {/* Only show ID for categories that actually use meaningful IDs */}
                      {(['Regio', 'Function_permissions'].includes(selectedCategory)) && (
                        <Td color="gray.300" pl={8}>
                          ↳ {child.id}
                        </Td>
                      )}
                      <Td color="gray.300" maxW="300px" isTruncated>
                        {child.displayValue || child.value}
                      </Td>
                      {(['Function_permissions'].includes(selectedCategory)) ? (
                        <Td color="gray.400">{item.id}</Td>
                      ) : (
                        <Td color="gray.400">-</Td>
                      )}
                      <Td>
                        <HStack spacing={2}>
                          <IconButton
                            size="sm"
                            colorScheme="blue"
                            icon={<span>✏️</span>}
                            onClick={() => {
                              setEditingItem(child);
                              setOriginalItemId(child.id); // Store original ID for updates
                              onOpen();
                            }}
                            aria-label="Bewerk"
                          />
                          <IconButton
                            size="sm"
                            colorScheme="red"
                            icon={<span>🗑️</span>}
                            onClick={() => handleDeleteParameter(child)}
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

        <Button 
          colorScheme="orange" 
          onClick={() => navigate('/dashboard')}
          alignSelf="flex-start"
        >
          Terug naar Dashboard
        </Button>
          </>
        )}
      </VStack>

      {/* Add New Category Modal */}
      <Modal isOpen={isCategoryModalOpen} onClose={onCategoryModalClose}>
        <ModalOverlay />
        <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
          <ModalHeader color="orange.400">
            Nieuwe Categorie Toevoegen
          </ModalHeader>
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel color="orange.300">Categorie Naam</FormLabel>
                <Input
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  placeholder="Bijv. Leveropties, Kleuren, etc."
                  bg="gray.700"
                  borderColor="orange.400"
                  _focus={{ borderColor: 'orange.500' }}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && newCategoryName.trim()) {
                      handleAddNewCategory();
                    }
                  }}
                />
              </FormControl>
              <Text fontSize="sm" color="gray.400">
                💡 Tip: Gebruik een duidelijke naam die de inhoud van de categorie beschrijft
              </Text>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button 
              variant="ghost" 
              mr={3} 
              onClick={() => {
                setNewCategoryName('');
                onCategoryModalClose();
              }}
            >
              Annuleren
            </Button>
            <Button
              colorScheme="orange"
              onClick={handleAddNewCategory}
              isDisabled={!newCategoryName.trim()}
            >
              Categorie Toevoegen
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Edit Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
          <ModalHeader color="orange.400">
            {editingItem?.id ? 'Parameter Bewerken' : 'Nieuw Parameter Toevoegen'}
          </ModalHeader>
          <ModalBody>
            <VStack spacing={4}>
              {/* Only show ID field for Regio (needed for Cognito access control) */}
              {selectedCategory === 'Regio' && (
                <FormControl>
                  <FormLabel color="orange.300">ID (voor Cognito toegang)</FormLabel>
                  <Input
                    value={editingItem?.id || ''}
                    onChange={(e) => {
                      if (editingItem) {
                        setEditingItem({
                          ...editingItem,
                          id: e.target.value
                        });
                      }
                    }}
                    placeholder="Region ID (1-9)"
                    bg="gray.700"
                    borderColor="orange.400"
                  />
                </FormControl>
              )}
              <FormControl>
                <FormLabel color="orange.300">
                  {selectedCategory === 'Leveropties' ? 'Naam' : 'Waarde'}
                </FormLabel>
                <Input
                  value={selectedCategory === 'Leveropties' ? (editingItem?.name || '') : (editingItem?.value || '')}
                  onChange={(e) => {
                    if (editingItem) {
                      if (selectedCategory === 'Leveropties') {
                        setEditingItem({
                          ...editingItem,
                          name: e.target.value
                        });
                      } else {
                        setEditingItem({
                          ...editingItem,
                          value: e.target.value
                        });
                      }
                    }
                  }}
                  placeholder={selectedCategory === 'Leveropties' ? 'Leveroptie naam' : 'Parameter waarde'}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>
              
              {/* Special field for Leveropties cost */}
              {selectedCategory === 'Leveropties' && (
                <FormControl>
                  <FormLabel color="orange.300">Kosten</FormLabel>
                  <Input
                    value={editingItem?.cost || ''}
                    onChange={(e) => {
                      if (editingItem) {
                        setEditingItem({
                          ...editingItem,
                          cost: e.target.value
                        });
                      }
                    }}
                    placeholder="Kosten (bijv. 5.0)"
                    bg="gray.700"
                    borderColor="orange.400"
                  />
                </FormControl>
              )}
              {(selectedCategory === 'Productgroepen') && (
                <FormControl>
                  <FormLabel color="orange.300">Parent (optioneel)</FormLabel>
                  <Select
                    value={editingItem?.parent || ''}
                    onChange={(e) => {
                      if (editingItem) {
                        setEditingItem({
                          ...editingItem,
                          parent: e.target.value || null
                        });
                      }
                    }}
                    bg="gray.700"
                    borderColor="orange.400"
                    color="white"
                    _focus={{ borderColor: 'orange.500' }}
                  >
                    <option value="" style={{ backgroundColor: '#2D3748', color: 'white' }}>
                      Geen parent (hoofditem)
                    </option>
                    {parentItems.map((parent) => (
                      <option 
                        key={parent.id || parent.value} 
                        value={parent.id || parent.value}
                        style={{ backgroundColor: '#2D3748', color: 'white' }}
                      >
                        {parent.value}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Annuleren
            </Button>
            <Button
              colorScheme="orange"
              onClick={handleSaveParameter}
              isDisabled={
                selectedCategory === 'Leveropties' 
                  ? (!editingItem?.name || !editingItem?.cost)
                  : selectedCategory === 'Regio' 
                    ? (!editingItem?.value || !editingItem?.id)
                    : !editingItem?.value
              }
            >
              {originalItemId ? 'Bijwerken' : 'Toevoegen'}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}

export default ParameterManagement;