import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Heading
} from '@chakra-ui/react';
import { Auth } from 'aws-amplify';

interface PasswordlessSignUpProps {
  onSuccess?: (email: string) => void;
  onError?: (error: string) => void;
}

export function PasswordlessSignUp({ onSuccess, onError }: PasswordlessSignUpProps) {
  const [formData, setFormData] = useState({
    email: '',
    given_name: '',
    family_name: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      // Create user account without password using Cognito Admin API
      // This will create the user in "FORCE_CHANGE_PASSWORD" state
      // which allows for passwordless authentication setup
      
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/cognito/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          given_name: formData.given_name,
          family_name: formData.family_name,
          passwordless: true
        })
      });

      if (response.ok) {
        setMessage(
          'Account aangemaakt! Controleer je e-mail voor verificatie-instructies. ' +
          'Na verificatie kun je een passkey instellen voor veilig inloggen.'
        );
        if (onSuccess) onSuccess(formData.email);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Registratie mislukt');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Er is een fout opgetreden bij het aanmaken van je account';
      setError(errorMessage);
      if (onError) onError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box maxW="md" mx="auto" p={6}>
      <VStack spacing={6}>
        <Box textAlign="center">
          <Heading color="orange.400" size="md">Account Aanmaken</Heading>
          <Text color="gray.400" mt={2}>
            Maak een account aan met alleen je e-mailadres. 
          </Text>
          <Text color="orange.300" mt={1} fontSize="sm">
            Na registratie ontvang je instructies voor passwordless authenticatie.
          </Text>
        </Box>

        {error && (
          <Alert status="error" bg="red.900" borderColor="red.500" border="1px solid">
            <AlertIcon color="red.300" />
            <Text color="red.100">{error}</Text>
          </Alert>
        )}

        {message && (
          <Alert status="success" bg="green.900" borderColor="green.500" border="1px solid">
            <AlertIcon color="green.300" />
            <Text color="green.100">{message}</Text>
          </Alert>
        )}

        <form onSubmit={handleSubmit} style={{ width: '100%' }}>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel color="gray.300">E-mailadres</FormLabel>
              <Input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="Voer je e-mailadres in"
                bg="gray.700"
                border="1px solid"
                borderColor="gray.600"
                color="white"
                _placeholder={{ color: 'gray.400' }}
                _focus={{ borderColor: 'orange.400' }}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel color="gray.300">Voornaam</FormLabel>
              <Input
                type="text"
                name="given_name"
                value={formData.given_name}
                onChange={handleInputChange}
                placeholder="Voer je voornaam in"
                bg="gray.700"
                border="1px solid"
                borderColor="gray.600"
                color="white"
                _placeholder={{ color: 'gray.400' }}
                _focus={{ borderColor: 'orange.400' }}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel color="gray.300">Achternaam</FormLabel>
              <Input
                type="text"
                name="family_name"
                value={formData.family_name}
                onChange={handleInputChange}
                placeholder="Voer je achternaam in"
                bg="gray.700"
                border="1px solid"
                borderColor="gray.600"
                color="white"
                _placeholder={{ color: 'gray.400' }}
                _focus={{ borderColor: 'orange.400' }}
              />
            </FormControl>

            <Button
              type="submit"
              colorScheme="orange"
              size="lg"
              width="full"
              isLoading={loading}
              loadingText="Account aanmaken..."
            >
              Account Aanmaken
            </Button>
          </VStack>
        </form>

        <Box textAlign="center">
          <Text color="gray.400" fontSize="sm">
            Na registratie ontvang je een verificatie-e-mail met verdere instructies.
          </Text>
          <Text color="orange.300" fontSize="xs" mt={1}>
            Let op: Backend deployment vereist voor volledige functionaliteit.
          </Text>
        </Box>
      </VStack>
    </Box>
  );
}