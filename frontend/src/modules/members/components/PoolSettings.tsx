import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Text, Badge, SimpleGrid, Card, CardBody,
  useToast, Spinner
} from '@chakra-ui/react';
import cognitoService from '../services/cognitoService';

interface PasswordPolicy {
  MinimumLength?: number;
  RequireUppercase?: boolean;
  RequireLowercase?: boolean;
  RequireNumbers?: boolean;
  RequireSymbols?: boolean;
  TemporaryPasswordValidityDays?: number;
}

interface SchemaAttribute {
  Name: string;
  Required?: boolean;
}

interface UserPoolInfo {
  Id: string;
  Name: string;
  Status: string;
  CreationDate?: string;
  LastModifiedDate?: string;
  EstimatedNumberOfUsers?: number;
  MfaConfiguration?: string;
  EnabledMfas?: string[];
  AutoVerifiedAttributes?: string[];
  AliasAttributes?: string[];
  Policies?: {
    PasswordPolicy?: PasswordPolicy;
  };
  Schema?: SchemaAttribute[];
}

interface PoolSettingsProps {
  user: any;
}

function PoolSettings({ user }: PoolSettingsProps) {
  const [poolInfo, setPoolInfo] = useState<UserPoolInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    loadPoolSettings();
  }, []);

  const loadPoolSettings = async () => {
    try {
      setLoading(true);
      const response = await cognitoService.getPoolSettings();
      setPoolInfo(response.UserPool);
    } catch (error: any) {
      toast({
        title: 'Fout bij laden pool instellingen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const formatPolicies = (policies: PasswordPolicy | undefined) => {
    if (!policies) return 'Geen beleid ingesteld';
    
    const parts = [];
    if (policies.MinimumLength) parts.push(`Min. lengte: ${policies.MinimumLength}`);
    if (policies.RequireUppercase) parts.push('Hoofdletters vereist');
    if (policies.RequireLowercase) parts.push('Kleine letters vereist');
    if (policies.RequireNumbers) parts.push('Cijfers vereist');
    if (policies.RequireSymbols) parts.push('Symbolen vereist');
    
    return parts.length > 0 ? parts.join(', ') : 'Standaard beleid';
  };

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Spinner size="xl" color="orange.400" />
        <Text mt={4} color="orange.400">Pool instellingen laden...</Text>
      </Box>
    );
  }

  if (!poolInfo) {
    return (
      <Box p={6} textAlign="center">
        <Text color="gray.400">Geen pool informatie beschikbaar</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      <Text color="orange.400" fontSize="xl" fontWeight="bold">
        User Pool Instellingen
      </Text>

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
        <Card bg="gray.800" border="1px" borderColor="orange.400">
          <CardBody>
            <VStack align="start" spacing={3}>
              <Text color="orange.300" fontWeight="bold">Algemene Informatie</Text>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Pool ID:</Text>
                <Text color="white" fontSize="sm">{poolInfo.Id}</Text>
              </HStack>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Pool Naam:</Text>
                <Text color="white">{poolInfo.Name}</Text>
              </HStack>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Status:</Text>
                <Badge colorScheme={poolInfo.Status === 'Enabled' ? 'green' : 'red'}>
                  {poolInfo.Status}
                </Badge>
              </HStack>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Aangemaakt:</Text>
                <Text color="white">
                  {poolInfo.CreationDate ? new Date(poolInfo.CreationDate).toLocaleDateString('nl-NL') : '-'}
                </Text>
              </HStack>
            </VStack>
          </CardBody>
        </Card>

        <Card bg="gray.800" border="1px" borderColor="orange.400">
          <CardBody>
            <VStack align="start" spacing={3}>
              <Text color="orange.300" fontWeight="bold">Wachtwoord Beleid</Text>
              <Text color="white" fontSize="sm">
                {formatPolicies(poolInfo.Policies?.PasswordPolicy)}
              </Text>
              {poolInfo.Policies?.PasswordPolicy?.TemporaryPasswordValidityDays && (
                <HStack justify="space-between" w="full">
                  <Text color="gray.300">Tijdelijk wachtwoord geldig:</Text>
                  <Text color="white">
                    {poolInfo.Policies.PasswordPolicy.TemporaryPasswordValidityDays} dagen
                  </Text>
                </HStack>
              )}
            </VStack>
          </CardBody>
        </Card>

        <Card bg="gray.800" border="1px" borderColor="orange.400">
          <CardBody>
            <VStack align="start" spacing={3}>
              <Text color="orange.300" fontWeight="bold">MFA Instellingen</Text>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">MFA Configuratie:</Text>
                <Badge colorScheme={poolInfo.MfaConfiguration === 'OFF' ? 'red' : 'green'}>
                  {poolInfo.MfaConfiguration || 'OFF'}
                </Badge>
              </HStack>
              {poolInfo.EnabledMfas && poolInfo.EnabledMfas.length > 0 && (
                <HStack justify="space-between" w="full">
                  <Text color="gray.300">Ingeschakelde MFA:</Text>
                  <Text color="white">{poolInfo.EnabledMfas.join(', ')}</Text>
                </HStack>
              )}
            </VStack>
          </CardBody>
        </Card>

        <Card bg="gray.800" border="1px" borderColor="orange.400">
          <CardBody>
            <VStack align="start" spacing={3}>
              <Text color="orange.300" fontWeight="bold">Gebruiker Attributen</Text>
              {poolInfo.Schema && poolInfo.Schema.length > 0 ? (
                <VStack align="start" spacing={1} w="full">
                  {poolInfo.Schema
                    .filter(attr => attr.Required)
                    .map((attr) => (
                      <HStack key={attr.Name} justify="space-between" w="full">
                        <Text color="gray.300" fontSize="sm">{attr.Name}:</Text>
                        <Badge size="sm" colorScheme="blue">Verplicht</Badge>
                      </HStack>
                    ))}
                </VStack>
              ) : (
                <Text color="gray.400" fontSize="sm">Geen schema informatie beschikbaar</Text>
              )}
            </VStack>
          </CardBody>
        </Card>

        <Card bg="gray.800" border="1px" borderColor="orange.400">
          <CardBody>
            <VStack align="start" spacing={3}>
              <Text color="orange.300" fontWeight="bold">Auto-verificatie</Text>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Auto-geverifieerde attributen:</Text>
                <Text color="white">
                  {poolInfo.AutoVerifiedAttributes?.join(', ') || 'Geen'}
                </Text>
              </HStack>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Alias attributen:</Text>
                <Text color="white">
                  {poolInfo.AliasAttributes?.join(', ') || 'Geen'}
                </Text>
              </HStack>
            </VStack>
          </CardBody>
        </Card>

        <Card bg="gray.800" border="1px" borderColor="orange.400">
          <CardBody>
            <VStack align="start" spacing={3}>
              <Text color="orange.300" fontWeight="bold">Geschatte Gebruikers</Text>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Geschat aantal:</Text>
                <Badge colorScheme="blue" fontSize="md">
                  {poolInfo.EstimatedNumberOfUsers || 0}
                </Badge>
              </HStack>
              <HStack justify="space-between" w="full">
                <Text color="gray.300">Laatst gewijzigd:</Text>
                <Text color="white">
                  {poolInfo.LastModifiedDate ? new Date(poolInfo.LastModifiedDate).toLocaleDateString('nl-NL') : '-'}
                </Text>
              </HStack>
            </VStack>
          </CardBody>
        </Card>
      </SimpleGrid>
    </VStack>
  );
}

export default PoolSettings;