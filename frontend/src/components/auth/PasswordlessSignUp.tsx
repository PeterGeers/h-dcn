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
import { useTranslation } from 'react-i18next';

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
  const { t, i18n } = useTranslation('auth');

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
      // Call backend API for passwordless signup
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          given_name: formData.given_name,
          family_name: formData.family_name,
          locale: i18n.language,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(t('signup.success'));
        if (onSuccess) onSuccess(formData.email);
      } else {
        // Handle specific backend errors
        let errorMessage = data.error || t('signup.generic_error');
        
        if (response.status === 409) {
          errorMessage = t('signup.existing_account');
        }
        
        setError(errorMessage);
        if (onError) onError(errorMessage);
      }
    } catch (err: any) {
      console.error('Sign up error:', err);
      
      // Handle network and other errors
      let errorMessage = t('signup.network_error');
      
      if (err.message) {
        errorMessage = err.message;
      }
      
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
          <Heading color="orange.400" size="md">{t('signup.title')}</Heading>
          <Text color="gray.400" mt={2}>
            {t('signup.description')}
          </Text>
          <Text color="orange.300" mt={1} fontSize="sm">
            {t('signup.passkey_hint')}
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
              <FormLabel color="gray.300">{t('signup.email_label')}</FormLabel>
              <Input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder={t('login.email_placeholder')}
                bg="gray.700"
                border="1px solid"
                borderColor="gray.600"
                color="white"
                _placeholder={{ color: 'gray.400' }}
                _focus={{ borderColor: 'orange.400' }}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel color="gray.300">{t('signup.first_name_label')}</FormLabel>
              <Input
                type="text"
                name="given_name"
                value={formData.given_name}
                onChange={handleInputChange}
                placeholder={t('signup.first_name_placeholder')}
                bg="gray.700"
                border="1px solid"
                borderColor="gray.600"
                color="white"
                _placeholder={{ color: 'gray.400' }}
                _focus={{ borderColor: 'orange.400' }}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel color="gray.300">{t('signup.last_name_label')}</FormLabel>
              <Input
                type="text"
                name="family_name"
                value={formData.family_name}
                onChange={handleInputChange}
                placeholder={t('signup.last_name_placeholder')}
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
              loadingText={t('signup.loading')}
            >
              {t('signup.submit_button')}
            </Button>
          </VStack>
        </form>

        <Box textAlign="center">
          <Text color="gray.400" fontSize="sm">
            {t('signup.after_registration')}
          </Text>
          <Text color="orange.300" fontSize="xs" mt={1}>
            {t('signup.already_have_account')}
          </Text>
        </Box>
      </VStack>
    </Box>
  );
}