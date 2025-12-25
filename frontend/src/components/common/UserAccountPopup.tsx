import React from 'react';
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
  Box
} from '@chakra-ui/react';

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
  hdcnLeden: 'Basis lid - Toegang tot persoonlijke gegevens en webshop',
  Members_CRUD_All: 'Ledenadministratie - Volledig beheer van alle leden',
  Members_Read_All: 'Ledenadministratie - Inzage in alle ledengegevens',
  Members_Status_Approve: 'Ledenadministratie - Goedkeuring lidmaatschapsstatus',
  Events_Read_All: 'Evenementen - Inzage in alle evenementen',
  Events_CRUD_All: 'Evenementen - Volledig beheer van evenementen',
  Products_Read_All: 'Producten - Inzage in alle producten',
  Products_CRUD_All: 'Producten - Volledig beheer van producten',
  System_User_Management: 'Systeem - Gebruikersbeheer',
  System_CRUD_All: 'Systeem - Volledig systeembeheer',
  System_Logs_Read: 'Systeem - Inzage in logbestanden',
  National_Chairman: 'Landelijk Voorzitter',
  National_Secretary: 'Landelijk Secretaris',
  National_Treasurer: 'Landelijk Penningmeester',
  Webmaster: 'Webmaster - Volledig systeembeheer',
  Tour_Commissioner: 'Tourcommissaris',
  Club_Magazine_Editorial: 'Clubblad Redactie',
  Webshop_Management: 'Webshop Beheer',
  hdcnAdmins: 'Beheerder (legacy)'
};

// Get role category for better organization
const getRoleCategory = (role: string): string => {
  if (role === 'hdcnLeden') return 'Basis Lid';
  if (role.startsWith('Members_')) return 'Ledenadministratie';
  if (role.startsWith('Events_')) return 'Evenementen';
  if (role.startsWith('Products_')) return 'Producten';
  if (role.startsWith('System_')) return 'Systeem';
  if (role.startsWith('National_')) return 'Landelijk Bestuur';
  if (role.startsWith('Regional_')) return 'Regionaal Bestuur';
  if (role.includes('Webmaster') || role.includes('Tour_') || role.includes('Club_') || role.includes('Webshop_')) return 'Ondersteunende Functies';
  if (role === 'hdcnAdmins') return 'Beheer';
  return 'Overig';
};

// Get role color based on category
const getRoleColor = (role: string): string => {
  if (role === 'hdcnLeden') return 'green';
  if (role.startsWith('Members_')) return 'blue';
  if (role.startsWith('Events_')) return 'purple';
  if (role.startsWith('Products_')) return 'orange';
  if (role.startsWith('System_') || role === 'hdcnAdmins' || role.includes('Webmaster')) return 'red';
  if (role.startsWith('National_')) return 'teal';
  if (role.startsWith('Regional_')) return 'cyan';
  return 'gray';
};

export function UserAccountPopup({ user, signOut }: UserAccountPopupProps) {
  const userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
  const userEmail = user.attributes?.email || 'Onbekend';
  const userName = user.attributes?.given_name || user.attributes?.family_name ? 
    `${user.attributes.given_name || ''} ${user.attributes.family_name || ''}`.trim() : 
    'Gebruiker';

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
    <Popover placement="bottom-end">
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
        >
          <Text fontSize={{ base: 'xs', md: 'sm' }} isTruncated maxW="200px">
            {userEmail}
          </Text>
        </Button>
      </PopoverTrigger>
      <PopoverContent bg="white" borderColor="orange.200" shadow="lg" maxW="400px">
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

            {/* Roles */}
            <Box>
              <Text fontWeight="semibold" color="black" fontSize="sm" mb={2}>
                Toegewezen Rollen ({userGroups.length})
              </Text>
              
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
                          <HStack key={role} justify="space-between" align="flex-start">
                            <Badge 
                              colorScheme={getRoleColor(role)} 
                              size="sm"
                              fontSize="xs"
                              px={2}
                              py={1}
                            >
                              {role}
                            </Badge>
                          </HStack>
                        ))}
                      </VStack>
                    </Box>
                  ))}
                </VStack>
              )}
            </Box>

            <Divider />

            {/* Permissions Summary */}
            <Box>
              <Text fontWeight="semibold" color="black" fontSize="sm" mb={2}>
                Toegangsniveau
              </Text>
              {userGroups.includes('hdcnLeden') && userGroups.length === 1 ? (
                <Text color="green.600" fontSize="xs">
                  ✓ Basis lid - Toegang tot persoonlijke gegevens en webshop
                </Text>
              ) : userGroups.some(role => 
                role.includes('System_') || 
                role.includes('Webmaster') || 
                role === 'hdcnAdmins'
              ) ? (
                <Text color="red.600" fontSize="xs">
                  ⚡ Beheerder - Uitgebreide systeemtoegang
                </Text>
              ) : userGroups.some(role => 
                role.includes('Members_') || 
                role.includes('Events_') || 
                role.includes('Products_') ||
                role.includes('National_') ||
                role.includes('Regional_')
              ) ? (
                <Text color="blue.600" fontSize="xs">
                  🔧 Functionaris - Toegang tot beheerfuncties
                </Text>
              ) : (
                <Text color="gray.600" fontSize="xs">
                  ℹ️ Beperkte toegang
                </Text>
              )}
            </Box>

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