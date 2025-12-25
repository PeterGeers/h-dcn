import React, { useState, useEffect } from 'react';
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
import { ApiService } from '../utils/apiService';
import { FunctionPermissionManager, getUserRoles } from '../utils/functionPermissions';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
  };
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
    };
  };
}

interface ParameterManagementProps {
  user: User;
}

interface ParameterItem {
  id: string;
  value: any;
  parent?: string | null;
  displayValue?: string;
}

interface Parameters {
  [category: string]: ParameterItem[] | any;
  _metadata?: Record<string, any>;
}

interface FormValues {
  value: string;
  parent?: string;
}

// Convert hierarchical back to flat for saving
const convertToFlatForSave = (data: Parameters): Parameters => {
  const flat = { ...data };
  if (flat.Productgroepen) {
    flat.Productgroepen = flat.Productgroepen.map(item => {
      try {
        const parsed = JSON.parse(item.value);
        return {
          id: item.id,
          value: parsed.value,
          parent: parsed.parent
        };
      } catch {
        return item;
      }
    });
  }
  return flat;
};

const validationSchema = Yup.object({
  value: Yup.string().required('Waarde is verplicht'),
  parent: Yup.string()
});

function ParameterManagement({ user }: ParameterManagementProps) {
  const navigate = useNavigate();
  const [parameters, setParameters] = useState<Parameters>({});
  const [selectedCategory, setSelectedCategory] = useState('Regio');
  const [selectedParent, setSelectedParent] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<ParameterItem | null>(null);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryDescription, setNewCategoryDescription] = useState('');
  const [editingCategory, setEditingCategory] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState('loading');
  const [hasAccess, setHasAccess] = useState<boolean>(false);
  const [accessLoading, setAccessLoading] = useState<boolean>(true);
  const [userRoles, setUserRoles] = useState<string[]>([]);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isCategoryOpen, onOpen: onCategoryOpen, onClose: onCategoryClose } = useDisclosure();
  const toast = useToast();

  // Check user access permissions on component mount
  useEffect(() => {
    const checkAccess = async () => {
      try {
        setAccessLoading(true);
        
        // Extract user roles from Cognito JWT token
        const roles = getUserRoles(user);
        setUserRoles(roles);
        console.log('🔍 ParameterManagement - User roles:', roles);
        
        // Create permission manager and check access
        const permissions = await FunctionPermissionManager.create(user);
        const canAccessParameters = permissions.hasAccess('parameters', 'read');
        
        console.log('🔍 ParameterManagement - Can access parameters:', canAccessParameters);
        
        // Additional check for administrative roles
        const hasAdminRole = roles.some(role => 
          role === 'hdcnAdmins' ||
          role === 'System_User_Management' ||
          role === 'System_CRUD_All' ||
          role === 'Webmaster' ||
          role === 'Members_CRUD_All' ||
          role === 'hdcnWebmaster' ||
          role === 'hdcnLedenadministratie'
        );
        
        console.log('🔍 ParameterManagement - Has admin role:', hasAdminRole);
        
        // Grant access if user has parameter permissions OR administrative roles
        const finalAccess = canAccessParameters || hasAdminRole;
        setHasAccess(finalAccess);
        
        if (!finalAccess) {
          console.log('❌ ParameterManagement - Access denied. User roles:', roles);
          toast({
            title: 'Toegang geweigerd',
            description: 'Je hebt geen toestemming om parameters te beheren. Neem contact op met een beheerder.',
            status: 'error',
            duration: 5000,
            isClosable: true
          });
        }
      } catch (error) {
        console.error('❌ ParameterManagement - Permission check failed:', error);
        setHasAccess(false);
        toast({
          title: 'Fout bij toegangscontrole',
          description: 'Er is een fout opgetreden bij het controleren van je toegangsrechten.',
          status: 'error',
          duration: 5000,
          isClosable: true
        });
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
  }, [user, toast]);

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
                <strong>Vereiste rollen:</strong> hdcnAdmins, System_User_Management, System_CRUD_All, Webmaster, Members_CRUD_All, hdcnWebmaster, of hdcnLedenadministratie
                <br /><br />
                Neem contact op met een systeembeheerder als je denkt dat je toegang zou moeten hebben.
              </AlertDescription>
            </Box>
          </Alert>
          
          <Button 
            colorScheme="orange" 
            onClick={() => navigate('/')}
            alignSelf="flex-start"
          >
            Terug naar Dashboard
          </Button>
        </VStack>
      </Box>
    );
  }

  const getCategories = (): string[] => {
    if (Object.keys(parameters).length > 0) {
      return Object.keys(parameters)
        .filter(key => key !== '_metadata')
        .sort((a, b) => a.localeCompare(b));
    }
    return ['Regio', 'Lidmaatschap', 'Motormerk', 'Clubblad', 'WieWatWaar', 'Productgroepen', 'function_permissions'].sort();
  };

  useEffect(() => {
    // Only load parameters if user has access
    if (hasAccess && !accessLoading) {
      loadParameters();
      // Force create function_permissions if missing
      const initFunctionPermissions = async () => {
        try {
          const params = await parameterStore.getParameters();
          if (!params.Function_permissions || params.Function_permissions.length === 0) {
            console.log('Creating function_permissions category...');
            const updatedParams = {
              ...params,
              Function_permissions: [{
                id: 'default',
                value: {
                  members: { read: ['hdcnAdmins', 'hdcnRegio_*'], write: ['hdcnAdmins'] },
                  events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
                  products: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
                  webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden', 'hdcnAdmins'] },
                  parameters: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
                  memberships: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
                }
              }]
            };
            await parameterStore.saveParameters(updatedParams);
            await loadParameters(); // Reload to show new category
            toast({ title: 'Function permissions aangemaakt', status: 'success' });
          }
        } catch (error) {
          console.error('Failed to create function_permissions:', error);
        }
      };
      setTimeout(initFunctionPermissions, 1000); // Wait for initial load
    }
  }, [hasAccess, accessLoading]); // Only run when access is determined

  const loadParameters = async () => {
    try {
      // Load ALL parameters directly from API for Parameter Management
      const apiData = await ApiService.getAllParameters();
      const allParameters = await convertAllApiToFormStructure(apiData);
      setParameters(allParameters);
      setDataSource('DynamoDB API');
      console.log('All parameters loaded:', Object.keys(allParameters));
    } catch (error) {
      toast({ title: 'Fout bij laden parameters', description: error.message, status: 'error' });
      setDataSource('Error');
    }
  };

  // Convert ALL API parameters to form structure (for Parameter Management)
  const convertAllApiToFormStructure = async (apiData: any[]): Promise<Parameters> => {
    const formStructure: any = {};
    const categoryMetadata: any = {};

    if (Array.isArray(apiData)) {
      apiData.forEach(param => {
        try {
          const name = param.name?.toLowerCase();
          const categoryName = getCategoryName(name);
          
          if (name === 'productgroepen') {
            // Special handling for nested Productgroepen
            const nestedData = JSON.parse(param.value);
            const flatArray = [];
            Object.entries(nestedData).forEach(([key, item]: [string, any]) => {
              flatArray.push({
                id: item.id,
                value: item.value,
                parent: null
              });
              if (item.children) {
                Object.entries(item.children).forEach(([childKey, child]: [string, any]) => {
                  flatArray.push({
                    id: child.id,
                    value: child.value,
                    parent: item.id
                  });
                });
              }
            });
            formStructure.Productgroepen = flatArray;
            
            categoryMetadata.Productgroepen = {
              description: param.description,
              created_at: param.created_at,
              parameter_id: param.parameter_id
            };
          } else if (name === 'api_base_url') {
            // Special handling for API base URL
            if (!formStructure.Configuratie) formStructure.Configuratie = [];
            formStructure.Configuratie.push({
              id: param.parameter_id || 'api_base_url',
              value: param.value
            });
            
            categoryMetadata.Configuratie = {
              description: param.description,
              created_at: param.created_at,
              parameter_id: param.parameter_id
            };
          } else if (categoryName) {
            // Handle all other categories dynamically
            try {
              const items = JSON.parse(param.value);
              formStructure[categoryName] = Array.isArray(items) ? items : [];
            } catch {
              // If not JSON, treat as single value
              formStructure[categoryName] = [{ id: param.parameter_id, value: param.value }];
            }
            
            categoryMetadata[categoryName] = {
              description: param.description,
              created_at: param.created_at,
              parameter_id: param.parameter_id
            };
          }
        } catch (error) {
          console.log(`Error parsing ${param.name}:`, error);
        }
      });
    }

    formStructure._metadata = categoryMetadata;
    return formStructure;
  };

  // Helper function for category name mapping
  const getCategoryName = (apiName: string): string | null => {
    const mapping = {
      'regio': 'Regio',
      'lidmaatschap': 'Lidmaatschap',
      'statuslidmaatschap': 'Statuslidmaatschap',
      'motormerk': 'Motormerk',
      'clubblad': 'Clubblad',
      'wiewatwaar': 'WieWatWaar',
      'productgroepen': 'Productgroepen',
      'leveropties': 'Leveropties'
    };
    
    if (mapping[apiName]) {
      return mapping[apiName];
    }
    
    if (apiName && apiName !== 'api_base_url') {
      return apiName.charAt(0).toUpperCase() + apiName.slice(1);
    }
    
    return null;
  };

  const handleSave = async (values: FormValues) => {
    // Double-check write permissions before saving
    if (!hasAccess) {
      toast({ 
        title: 'Toegang geweigerd', 
        description: 'Je hebt geen toestemming om parameters te wijzigen.',
        status: 'error' 
      });
      return;
    }

    try {
      // Additional permission check for write operations
      const permissions = await FunctionPermissionManager.create(user);
      const canWrite = permissions.hasAccess('parameters', 'write');
      
      if (!canWrite) {
        const hasWriteRole = userRoles.some(role => 
          role === 'hdcnAdmins' ||
          role === 'System_CRUD_All' ||
          role === 'Webmaster' ||
          role === 'hdcnWebmaster'
        );
        
        if (!hasWriteRole) {
          toast({ 
            title: 'Schrijftoegang geweigerd', 
            description: 'Je hebt alleen leestoegang tot parameters. Schrijftoegang vereist hogere rechten.',
            status: 'error' 
          });
          return;
        }
      }

      const currentData = { ...parameters };
      
      if (!currentData[selectedCategory]) {
        currentData[selectedCategory] = [];
      }
      
      if (editingItem?.id) {
        // Update existing
        const index = currentData[selectedCategory].findIndex(item => item.id === editingItem.id);
        if (index !== -1) {
          currentData[selectedCategory][index] = {
            id: editingItem.id,
            value: values.value,
            parent: values.parent || null
          };
        }
      } else {
        // Add new
        const newId = Date.now().toString();
        currentData[selectedCategory].push({
          id: newId,
          value: values.value,
          parent: values.parent || null
        });
      }
      
      // Save via parameter store
      await parameterStore.saveParameters(currentData);
      setParameters(currentData);
      
      onClose();
      setEditingItem(null);
      setSelectedParent(null);
      toast({ title: 'Parameter opgeslagen', status: 'success' });
    } catch (error) {
      toast({ title: 'Fout bij opslaan', description: error.message, status: 'error' });
    }
  };

  const handleDelete = async (id: string) => {
    // Double-check write permissions before deleting
    if (!hasAccess) {
      toast({ 
        title: 'Toegang geweigerd', 
        description: 'Je hebt geen toestemming om parameters te verwijderen.',
        status: 'error' 
      });
      return;
    }

    if (window.confirm('Weet je zeker dat je deze parameter wilt verwijderen?')) {
      try {
        // Additional permission check for write operations
        const permissions = await FunctionPermissionManager.create(user);
        const canWrite = permissions.hasAccess('parameters', 'write');
        
        if (!canWrite) {
          const hasWriteRole = userRoles.some(role => 
            role === 'hdcnAdmins' ||
            role === 'System_CRUD_All' ||
            role === 'Webmaster' ||
            role === 'hdcnWebmaster'
          );
          
          if (!hasWriteRole) {
            toast({ 
              title: 'Verwijdertoegang geweigerd', 
              description: 'Je hebt geen toestemming om parameters te verwijderen.',
              status: 'error' 
            });
            return;
          }
        }

        const currentData = { ...parameters };
        if (currentData[selectedCategory]) {
          currentData[selectedCategory] = currentData[selectedCategory].filter(item => item.id !== id);
        }
        await parameterStore.saveParameters(currentData);
        setParameters(currentData);
        toast({ title: 'Parameter verwijderd', status: 'success' });
      } catch (error) {
        toast({ title: 'Fout bij verwijderen', description: error.message, status: 'error' });
      }
    }
  };

  const openModal = (item: ParameterItem | null = null, parent: string | null = null) => {
    setEditingItem(item);
    setSelectedParent(parent);
    onOpen();
  };

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) return;
    
    // Double-check write permissions before adding category
    if (!hasAccess) {
      toast({ 
        title: 'Toegang geweigerd', 
        description: 'Je hebt geen toestemming om categorieën toe te voegen.',
        status: 'error' 
      });
      return;
    }
    
    try {
      // Additional permission check for write operations
      const permissions = await FunctionPermissionManager.create(user);
      const canWrite = permissions.hasAccess('parameters', 'write');
      
      if (!canWrite) {
        const hasWriteRole = userRoles.some(role => 
          role === 'hdcnAdmins' ||
          role === 'System_CRUD_All' ||
          role === 'Webmaster' ||
          role === 'hdcnWebmaster'
        );
        
        if (!hasWriteRole) {
          toast({ 
            title: 'Categorie toevoegen geweigerd', 
            description: 'Je hebt geen toestemming om categorieën toe te voegen of te wijzigen.',
            status: 'error' 
          });
          return;
        }
      }

      if (editingCategory) {
        // Rename existing category
        const currentData = await parameterStore.getParameters();
        const updatedData = { ...currentData };
        
        // Copy content to new category name
        updatedData[newCategoryName] = updatedData[editingCategory] || [];
        // Remove old category
        delete updatedData[editingCategory];
        
        await parameterStore.saveParameters(updatedData);
        
        // Refresh data to get updated metadata
        await parameterStore.refresh();
        await loadParameters();
        
        setSelectedCategory(newCategoryName);
        toast({ title: 'Categorie hernoemd', status: 'success' });
      } else {
        // Add new category
        const currentData = await parameterStore.getParameters();
        const description = newCategoryDescription || `Configuration data for ${newCategoryName}`;
        const createdAt = new Date().toISOString();
        
        // Special handling for function_permissions
        if (newCategoryName.toLowerCase() === 'function_permissions') {
          currentData[newCategoryName] = [{
            id: 'default',
            value: {
              members: { read: ['hdcnAdmins', 'hdcnRegio_*'], write: ['hdcnAdmins'] },
              events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
              products: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
              webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden', 'hdcnAdmins'] },
              parameters: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
            }
          }];
        } else {
          // Initialize empty array for other categories
          currentData[newCategoryName] = [];
        }
        
        // Create new parameter in DynamoDB
        try {
          const paramValue = newCategoryName.toLowerCase() === 'function_permissions' 
            ? JSON.stringify(currentData[newCategoryName])
            : JSON.stringify([]);
            
          const newParamData = {
            name: newCategoryName.toLowerCase(),
            value: paramValue,
            description: description,
            created_at: createdAt
          };
          await ApiService.createParameter(newParamData);
          console.log('Category created in DynamoDB with metadata');
        } catch (apiError) {
          console.log('API create failed, saving locally only');
        }
        
        await parameterStore.saveParameters(currentData);
        
        // Refresh data to get metadata from DynamoDB
        await parameterStore.refresh();
        await loadParameters();
        
        setSelectedCategory(newCategoryName);
        toast({ title: 'Categorie toegevoegd', status: 'success' });
      }
      
      await loadParameters();
      setNewCategoryName('');
      setNewCategoryDescription('');
      setEditingCategory(null);
      onCategoryClose();
    } catch (error) {
      toast({ title: 'Fout bij categorie bewerking', description: error.message, status: 'error' });
    }
  };

  const openCategoryModal = (categoryToEdit = null) => {
    setEditingCategory(categoryToEdit);
    setNewCategoryName(categoryToEdit || '');
    setNewCategoryDescription('');
    onCategoryOpen();
  };

  const handleDeleteCategory = async () => {
    if (window.confirm(`Weet je zeker dat je de categorie "${selectedCategory}" wilt verwijderen? Alle parameters in deze categorie worden ook verwijderd.`)) {
      // Double-check write permissions before deleting category
      if (!hasAccess) {
        toast({ 
          title: 'Toegang geweigerd', 
          description: 'Je hebt geen toestemming om categorieën te verwijderen.',
          status: 'error' 
        });
        return;
      }

      try {
        // Additional permission check for write operations
        const permissions = await FunctionPermissionManager.create(user);
        const canWrite = permissions.hasAccess('parameters', 'write');
        
        if (!canWrite) {
          const hasWriteRole = userRoles.some(role => 
            role === 'hdcnAdmins' ||
            role === 'System_CRUD_All' ||
            role === 'Webmaster' ||
            role === 'hdcnWebmaster'
          );
          
          if (!hasWriteRole) {
            toast({ 
              title: 'Categorie verwijderen geweigerd', 
              description: 'Je hebt geen toestemming om categorieën te verwijderen.',
              status: 'error' 
            });
            return;
          }
        }

        // Get the parameter ID for this category
        const categoryMetadata = parameters._metadata?.[selectedCategory];
        if (categoryMetadata?.parameter_id) {
          // Delete from DynamoDB
          await ApiService.deleteParameter(categoryMetadata.parameter_id);
        }
        
        // Reload all parameters to reflect the deletion
        await loadParameters();
        
        // Select a different category
        const remainingCategories = Object.keys(parameters).filter(key => key !== '_metadata' && key !== selectedCategory);
        setSelectedCategory(remainingCategories[0] || 'Regio');
        
        toast({ title: 'Categorie verwijderd uit DynamoDB', status: 'success' });
      } catch (error) {
        toast({ title: 'Fout bij verwijderen categorie', description: error.message, status: 'error' });
      }
    }
  };

  const getCurrentParameters = () => {
    const params = parameters[selectedCategory];
    if (!params) return [];
    
    // Handle both array and object formats
    if (Array.isArray(params)) {
      return params.map(param => ({
        ...param,
        displayValue: typeof param.value === 'object' 
          ? JSON.stringify(param.value, null, 2)
          : param.value,
        parent: param.parent || null,
        children: []
      }));
    }
    
    // Handle nested object format (like the old Productgroepen structure)
    if (typeof params === 'object') {
      const result = [];
      Object.entries(params).forEach(([key, item]: [string, any]) => {
        result.push({
          id: item.id,
          displayValue: item.value,
          parent: null,
          children: []
        });
        if (item.children) {
          Object.entries(item.children).forEach(([childKey, child]: [string, any]) => {
            result.push({
              id: child.id,
              displayValue: child.value,
              parent: item.id,
              children: []
            });
          });
        }
      });
      return result;
    }
    
    return [];
  };

  const currentParameters = getCurrentParameters();
  const categories = getCategories();
  const parentItems = currentParameters.filter(p => !p.parent);
  const getChildren = (parentId: string) => currentParameters.filter(p => p.parent === parentId);

  return (
    <Box maxW="6xl" mx="auto" p={6} bg="gray.900" minH="100vh">
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between">
          <Heading color="orange.400">Parameter Beheer</Heading>
          <HStack spacing={4}>
            {/* User role indicator */}
            <Box 
              bg="green.600" 
              px={3} 
              py={1} 
              borderRadius="md"
              color="white"
              fontSize="sm"
            >
              👤 Rollen: {userRoles.length > 0 ? userRoles.slice(0, 2).join(', ') : 'Geen'}{userRoles.length > 2 ? ` +${userRoles.length - 2}` : ''}
            </Box>
            <Box 
              bg={dataSource === 'S3 via API' ? 'green.600' : dataSource === 'LocalStorage/Public' ? 'blue.600' : 'yellow.600'} 
              px={3} 
              py={1} 
              borderRadius="md"
              color="white"
              fontSize="sm"
            >
              📊 Data bron: {dataSource}
            </Box>
          </HStack>
        </HStack>
        
        <VStack align="stretch" spacing={4}>
          <HStack>
            <Select 
              value={selectedCategory} 
              onChange={(e) => setSelectedCategory(e.target.value)}
              bg="gray.200" 
              color="black"
              maxW="300px"
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </Select>
            
            {/* Category metadata display */}
            {parameters._metadata?.[selectedCategory] && (
              <Box bg="gray.700" p={3} borderRadius="md" border="1px" borderColor="gray.600">
                <Text color="orange.300" fontSize="sm" fontWeight="bold">Categorie Info:</Text>
                <Text color="gray.300" fontSize="xs">
                  {parameters._metadata[selectedCategory].description || 'Geen beschrijving'}
                </Text>
                <Text color="gray.400" fontSize="xs">
                  Aangemaakt: {parameters._metadata[selectedCategory].created_at ? 
                    new Date(parameters._metadata[selectedCategory].created_at).toLocaleDateString('nl-NL') : 
                    'Onbekend'
                  }
                </Text>
              </Box>
            )}
          </HStack>
          
          <HStack>
          <Button colorScheme="green" onClick={() => openCategoryModal()}>
            + Categorie
          </Button>
          <Button colorScheme="blue" onClick={() => openCategoryModal(selectedCategory)}>
            ✏️ Categorie
          </Button>
          <Button colorScheme="red" onClick={handleDeleteCategory}>
            🗑️ Categorie
          </Button>
          <Button colorScheme="orange" onClick={() => openModal()}>
            + Parameter
          </Button>
          <Button 
            colorScheme="purple" 
            onClick={async () => {
              // Clear all caches
              localStorage.removeItem('hdcn-parameters');
              await parameterStore.refresh();
              await loadParameters();
              toast({ title: 'Cache geleegd en data vernieuwd', status: 'info' });
              // Force page reload to pick up new permissions
              setTimeout(() => window.location.reload(), 1000);
            }}
          >
            🔄 Ververs & Herlaad
          </Button>

          <Button 
            colorScheme="teal" 
            onClick={() => {
              // Try all possible data sources
              let dataToExport = null;
              let source = '';
              
              if (parameters && Object.keys(parameters).length > 0) {
                dataToExport = parameters;
                source = 'parameters-state';
              } else {
                const stored = localStorage.getItem('hdcn-parameters');
                if (stored) {
                  dataToExport = JSON.parse(stored);
                  source = 'localStorage';
                }
              }
              
              if (dataToExport) {
                const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `hdcn-parameters-${source}.json`;
                a.click();
                URL.revokeObjectURL(url);
                toast({ title: `Exported from ${source}`, status: 'success' });
              } else {
                toast({ title: 'No data found anywhere', status: 'error' });
              }
            }}
          >
            📥 Export Data
          </Button>
          </HStack>
        </VStack>

        <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="orange.400">
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th color="orange.300">Waarde</Th>
                <Th color="orange.300">Acties</Th>
              </Tr>
            </Thead>
            <Tbody>
              {parentItems.map((item, index) => (
                <React.Fragment key={item.id || index}>
                  <Tr>
                    <Td color="white" fontWeight="bold">
                      {typeof item.displayValue === 'string' 
                        ? item.displayValue 
                        : JSON.stringify(item.displayValue, null, 2)
                      }
                    </Td>
                    <Td>
                      <HStack>
                        <Button
                          size="sm"
                          colorScheme="green"
                          onClick={() => openModal(null, item.id || index)}
                        >
                          + Sub
                        </Button>
                        <Button
                          size="sm"
                          colorScheme="blue"
                          onClick={() => openModal(item)}
                        >
                          ✏️
                        </Button>
                        <Button
                          size="sm"
                          colorScheme="red"
                          onClick={() => handleDelete(item.id || index)}
                        >
                          🗑️
                        </Button>
                      </HStack>
                    </Td>
                  </Tr>
                  {getChildren(item.id || index).map((child, childIndex) => (
                    <Tr key={`${item.id}-${child.id || childIndex}`} bg="gray.700">
                      <Td color="gray.300" pl={8}>
                        ↳ {typeof child.displayValue === 'string' 
                          ? child.displayValue 
                          : JSON.stringify(child.displayValue, null, 2)
                        }
                      </Td>
                      <Td>
                        <HStack>
                          <Button
                            size="sm"
                            colorScheme="blue"
                            onClick={() => openModal(child)}
                          >
                            ✏️
                          </Button>
                          <Button
                            size="sm"
                            colorScheme="red"
                            onClick={() => handleDelete(child.id || childIndex)}
                          >
                            🗑️
                          </Button>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </React.Fragment>
              ))}
              {currentParameters.length === 0 && (
                <Tr>
                  <Td colSpan={2} textAlign="center" color="gray.400">
                    Geen parameters gevonden
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </Box>
      </VStack>

      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent bg="gray.800" borderColor="orange.400" border="1px">
          <ModalHeader color="orange.400">
            {editingItem ? 'Parameter Bewerken' : 'Parameter Toevoegen'}
          </ModalHeader>
          <Formik
            initialValues={{ 
              value: editingItem?.displayValue || '', 
              parent: selectedParent || editingItem?.parent || '' 
            }}
            validationSchema={validationSchema}
            onSubmit={handleSave}
          >
            {({ errors, touched, isSubmitting, values, setFieldValue }) => (
              <Form>
                <ModalBody>
                  <VStack spacing={4}>
                    <Field name="value">
                      {({ field }) => (
                        <FormControl isInvalid={errors.value && touched.value}>
                          <FormLabel color="orange.300">Waarde</FormLabel>
                          <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                          {errors.value && touched.value && (
                            <Text color="red.400" fontSize="sm">{errors.value}</Text>
                          )}
                        </FormControl>
                      )}
                    </Field>
                    
                    <Field name="parent">
                      {({ field }) => (
                        <FormControl>
                          <FormLabel color="orange.300">Parent (optioneel)</FormLabel>
                          <Select 
                            {...field} 
                            bg="gray.200" 
                            color="black" 
                            focusBorderColor="orange.400"
                            placeholder="Geen parent (hoofditem)"
                          >
                            {parentItems.map(parent => (
                              <option key={parent.id} value={parent.id}>
                                {parent.displayValue}
                              </option>
                            ))}
                          </Select>
                        </FormControl>
                      )}
                    </Field>
                  </VStack>
                </ModalBody>
                <ModalFooter>
                  <Button variant="ghost" mr={3} onClick={onClose}>
                    Annuleren
                  </Button>
                  <Button 
                    type="submit" 
                    colorScheme="orange" 
                    isLoading={isSubmitting}
                  >
                    Opslaan
                  </Button>
                </ModalFooter>
              </Form>
            )}
          </Formik>
        </ModalContent>
      </Modal>

      <Modal isOpen={isCategoryOpen} onClose={onCategoryClose}>
        <ModalOverlay />
        <ModalContent bg="gray.800" borderColor="orange.400" border="1px">
          <ModalHeader color="orange.400">
            {editingCategory ? 'Categorie Hernoemen' : 'Nieuwe Categorie Toevoegen'}
          </ModalHeader>
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel color="orange.300">Categorie Naam</FormLabel>
                <Input 
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  bg="gray.200" 
                  color="black" 
                  focusBorderColor="orange.400"
                  placeholder="Bijv. Evenementen, Sponsors, etc."
                />
              </FormControl>
              
              {!editingCategory && (
                <FormControl>
                  <FormLabel color="orange.300">Beschrijving</FormLabel>
                  <Input 
                    value={newCategoryDescription}
                    onChange={(e) => setNewCategoryDescription(e.target.value)}
                    bg="gray.200" 
                    color="black" 
                    focusBorderColor="orange.400"
                    placeholder="Korte uitleg over deze categorie"
                  />
                </FormControl>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCategoryClose}>
              Annuleren
            </Button>
            <Button 
              colorScheme={editingCategory ? 'blue' : 'green'}
              onClick={handleAddCategory}
              isDisabled={!newCategoryName.trim()}
            >
              {editingCategory ? 'Hernoemen' : 'Toevoegen'}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}

export default ParameterManagement;