import React, { useState } from 'react';
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverHeader,
  PopoverBody,
  PopoverCloseButton,
  Button,
  VStack,
  Text,
  Badge,
  HStack,
  Divider,
  Box,
  useBreakpointValue,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  List,
  ListItem,
  ListIcon
} from '@chakra-ui/react';
import { CheckCircleIcon } from '@chakra-ui/icons';
import {
  getCombinedPermissions,
  getPermissionDescription,
  groupPermissionsByCategory,
  getAccessLevelSummary,
  isAdministrator
} from '../../utils/permissions';

interface User {
  attributes?: {
    given_name?: string;
    family_name?: string;
    email?: string;
  };
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
    };
  };
}

interface UserAccountPopupProps {
  user: User;
  signOut: () => void;
}

// Role descriptions for better user understanding
const ROLE_DESCRIPTIONS: { [key: string]: string } = {
  // Basic member role
  hdcnLeden: 'Basis lid - Toegang tot persoonlijke gegevens en webshop',
  
  // Member management roles
  Members_CRUD_All: 'Ledenadministratie - Volledig beheer van alle leden',
  Members_Read_All: 'Ledenadministratie - Inzage in alle ledengegevens',
  Members_Status_Approve: 'Ledenadministratie - Goedkeuring lidmaatschapsstatus',
  Members_Export_All: 'Ledenadministratie - Export van alle ledengegevens',
  
  // Event management roles
  Events_Read_All: 'Evenementen - Inzage in alle evenementen',
  Events_CRUD_All: 'Evenementen - Volledig beheer van evenementen',
  Events_Export_All: 'Evenementen - Export van evenementengegevens',
  
  // Product management roles
  Products_Read_All: 'Producten - Inzage in alle producten',
  Products_CRUD_All: 'Producten - Volledig beheer van producten',
  Products_Export_All: 'Producten - Export van productgegevens',
  
  // Communication roles
  Communication_Read_All: 'Communicatie - Inzage in alle communicatie',
  Communication_Export_All: 'Communicatie - Export van communicatiegegevens',
  Communication_CRUD_All: 'Communicatie - Volledig beheer van communicatie',
  
  // System administration roles
  System_User_Management: 'Systeem - Gebruikersbeheer en rolbeheer',
  System_CRUD_All: 'Systeem - Volledig systeembeheer',
  System_Logs_Read: 'Systeem - Inzage in logbestanden en audit',
  
  // Organizational roles
  National_Chairman: 'Landelijk Voorzitter - Bestuurlijke bevoegdheden',
  National_Secretary: 'Landelijk Secretaris - Secretariële taken',
  National_Treasurer: 'Landelijk Penningmeester - Financiële inzage',
  Webmaster: 'Webmaster - Volledig systeembeheer',
  Tour_Commissioner: 'Tourcommissaris - Evenementenbeheer',
  Club_Magazine_Editorial: 'Clubblad Redactie - Communicatiebeheer',
  Webshop_Management: 'Webshop Beheer - Productbeheer',
  
  // Regional roles (examples - can be extended)
  Regional_Chairman: 'Regionaal Voorzitter - Regionale bestuurstaken',
  Regional_Secretary: 'Regionaal Secretaris - Regionale secretariële taken',
  Regional_Treasurer: 'Regionaal Penningmeester - Regionale financiën',
  Regional_Volunteer: 'Regionaal Vrijwilliger - Regionale ondersteuning',
  
  // Legacy roles
  hdcnAdmins: 'Beheerder (legacy) - Oude beheerdersrol'
};

// Get role category for better organization
const getRoleCategory = (role: string): string => {
  if (role === 'hdcnLeden') return 'Basis Lid';
  if (role.startsWith('Members_')) return 'Ledenadministratie';
  if (role.startsWith('Events_')) return 'Evenementen';
  if (role.startsWith('Products_')) return 'Producten';
  if (role.startsWith('Communication_')) return 'Communicatie';
  if (role.startsWith('System_')) return 'Systeem';
  if (role.startsWith('National_')) return 'Landelijk Bestuur';
  if (role.startsWith('Regional_')) return 'Regionaal Bestuur';
  if (role.includes('Webmaster') || role.includes('Tour_') || role.includes('Club_') || role.includes('Webshop_')) return 'Ondersteunende Functies';
  if (role === 'hdcnAdmins') return 'Beheer (Legacy)';
  return 'Overig';
};

// Get role color based on category
const getRoleColor = (role: string): string => {
  if (role === 'hdcnLeden') return 'green';
  if (role.startsWith('Members_')) return 'blue';
  if (role.startsWith('Events_')) return 'purple';
  if (role.startsWith('Products_')) return 'orange';
  if (role.startsWith('Communication_')) return 'pink';
  if (role.startsWith('System_') || role === 'hdcnAdmins' || role.includes('Webmaster')) return 'red';
  if (role.startsWith('National_')) return 'teal';
  if (role.startsWith('Regional_')) return 'cyan';
  if (role.includes('Tour_') || role.includes('Club_') || role.includes('Webshop_')) return 'yellow';
  return 'gray';
};

export function UserAccountPopup({ user, signOut }: UserAccountPopupProps) {
  const userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
  const userEmail = user.attributes?.email || 'Onbekend';
  const userName = user.attributes?.given_name || user.attributes?.family_name ? 
    `${user.attributes.given_name || ''} ${user.attributes.family_name || ''}`.trim() : 
    'Gebruiker';

  // Responsive placement for mobile vs desktop
  const placement = useBreakpointValue({ 
    base: 'bottom', 
    md: 'bottom-end' 
  }) as 'bottom' | 'bottom-end';

  // Check if user has administrative roles
  const isAdmin = isAdministrator(userGroups);

  // Get user permissions and access level
  const userPermissions = getCombinedPermissions(userGroups);
  const permissionsByCategory = groupPermissionsByCategory(userPermissions);
  const accessLevel = getAccessLevelSummary(userGroups);

  // Group roles by category
  const rolesByCategory: { [category: string]: string[] } = {};
  userGroups.forEach(role => {
    const category = getRoleCategory(role);
    if (!rolesByCategory[category]) {
      rolesByCategory[category] = [];
    }
    rolesByCategory[category].push(role);
  });

  return (
    <Popover 
      placement={placement}
      closeOnEsc={true}
      closeOnBlur={true}
      strategy="fixed"
    >
      <PopoverTrigger>
        <Button
          variant="ghost"
          colorScheme="orange"
          size={{ base: 'sm', md: 'sm' }}
          w={{ base: 'full', sm: 'auto' }}
          textAlign="left"
          justifyContent="flex-start"
          fontWeight="normal"
          _hover={{ bg: 'orange.100', color: 'black' }}
          position="relative"
        >
          <HStack spacing={2} align="center">
            <Text fontSize={{ base: 'xs', md: 'sm' }} isTruncated maxW="200px">
              {userEmail}
            </Text>
            {isAdmin && (
              <Badge 
                colorScheme="red" 
                size="sm" 
                fontSize="xs"
                px={1}
                py={0.5}
                borderRadius="full"
              >
                Admin
              </Badge>
            )}
          </HStack>
        </Button>
      </PopoverTrigger>
      <PopoverContent 
        bg="white" 
        borderColor="orange.200" 
        shadow="lg" 
        maxW={{ base: "95vw", sm: "500px" }}
        w={{ base: "95vw", sm: "500px" }}
        mx={{ base: 2, sm: 0 }}
        zIndex={1500}
      >
        <PopoverCloseButton />
        <PopoverHeader borderBottomColor="orange.200">
          <Text fontWeight="bold" color="black">Account Informatie</Text>
        </PopoverHeader>
        <PopoverBody>
          <VStack align="stretch" spacing={4}>
            {/* User Info */}
            <Box>
              <Text fontWeight="semibold" color="black" fontSize="sm">
                {userName}
              </Text>
              <Text color="gray.600" fontSize="xs">
                {userEmail}
              </Text>
            </Box>

            <Divider />

            {/* Access Level Summary */}
            <Box>
              <Text fontWeight="semibold" color="black" fontSize="sm" mb={2}>
                Toegangsniveau
              </Text>
              <HStack spacing={2} align="center">
                <Text fontSize="md">{accessLevel.icon}</Text>
                <Text 
                  color={
                    accessLevel.level === 'system' ? 'red.600' :
                    accessLevel.level === 'administrative' ? 'blue.600' :
                    accessLevel.level === 'functional' ? 'purple.600' :
                    'green.600'
                  } 
                  fontSize="sm" 
                  fontWeight="medium"
                >
                  {accessLevel.description}
                </Text>
              </HStack>
            </Box>

            <Divider />

            {/* Tabs for Roles and Permissions */}
            <Tabs size="sm" variant="enclosed" colorScheme="orange">
              <TabList>
                <Tab fontSize="xs">Rollen ({userGroups.length})</Tab>
                <Tab fontSize="xs">Bevoegdheden ({userPermissions.length})</Tab>
              </TabList>
              <TabPanels>
                {/* Roles Tab */}
                <TabPanel px={0} py={3}>
                  {userGroups.length === 0 ? (
                    <Text color="gray.500" fontSize="xs">
                      Geen rollen toegewezen
                    </Text>
                  ) : (
                    <VStack align="stretch" spacing={3}>
                      {Object.entries(rolesByCategory).map(([category, roles]) => (
                        <Box key={category}>
                          <Text fontWeight="medium" color="gray.700" fontSize="xs" mb={1}>
                            {category}
                          </Text>
                          <VStack align="stretch" spacing={1}>
                            {roles.map(role => (
                              <Box key={role}>
                                <HStack justify="space-between" align="flex-start" spacing={2}>
                                  <Badge 
                                    colorScheme={getRoleColor(role)} 
                                    size="sm"
                                    fontSize="xs"
                                    px={2}
                                    py={1}
                                    minW="fit-content"
                                  >
                                    {role}
                                  </Badge>
                                </HStack>
                                {ROLE_DESCRIPTIONS[role] && (
                                  <Text fontSize="xs" color="gray.600" mt={1} pl={2}>
                                    {ROLE_DESCRIPTIONS[role]}
                                  </Text>
                                )}
                              </Box>
                            ))}
                          </VStack>
                        </Box>
                      ))}
                    </VStack>
                  )}
                </TabPanel>

                {/* Permissions Tab */}
                <TabPanel px={0} py={3}>
                  {userPermissions.length === 0 ? (
                    <Text color="gray.500" fontSize="xs">
                      Geen bevoegdheden toegewezen
                    </Text>
                  ) : (
                    <Accordion allowMultiple size="sm">
                      {Object.entries(permissionsByCategory).map(([category, permissions]) => (
                        <AccordionItem key={category} border="none">
                          <AccordionButton px={0} py={2}>
                            <Box flex="1" textAlign="left">
                              <Text fontWeight="medium" color="gray.700" fontSize="xs">
                                {category} ({permissions.length})
                              </Text>
                            </Box>
                            <AccordionIcon />
                          </AccordionButton>
                          <AccordionPanel px={0} py={2}>
                            <List spacing={1}>
                              {permissions.map(permission => (
                                <ListItem key={permission} fontSize="xs">
                                  <ListIcon as={CheckCircleIcon} color="green.500" />
                                  <Text as="span" color="gray.700">
                                    {getPermissionDescription(permission)}
                                  </Text>
                                </ListItem>
                              ))}
                            </List>
                          </AccordionPanel>
                        </AccordionItem>
                      ))}
                    </Accordion>
                  )}
                </TabPanel>
              </TabPanels>
            </Tabs>

            <Divider />

            {/* Logout Button */}
            <Button 
              onClick={signOut} 
              colorScheme="orange" 
              size="sm"
              w="full"
            >
              Uitloggen
            </Button>
          </VStack>
        </PopoverBody>
      </PopoverContent>
    </Popover>
  );
}