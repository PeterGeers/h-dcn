/**
 * LanguageSelector - Chakra UI Menu for switching display language.
 *
 * Displays all 8 supported locales with flag emoji and native language name.
 * Active locale is highlighted (bold + checkmark) in the expanded menu.
 * Persists preference via PUT /members/me; on failure shows a non-blocking toast.
 *
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 2.6, 2.7, 2.8
 */

import React, { useCallback } from 'react';
import {
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Button,
  Text,
  HStack,
  useToast,
} from '@chakra-ui/react';
import { ChevronDownIcon, CheckIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import {
  SUPPORTED_LOCALES,
  LOCALE_NAMES,
  LOCALE_FLAGS,
  SupportedLocale,
} from '../../i18n/constants';
import { useAuth } from '../../context/AuthProvider';
import { ApiService } from '../../services/apiService';

/**
 * LanguageSelector component.
 *
 * Reads the active locale from i18n context and the auth state from AuthProvider.
 * No external props required.
 */
export function LanguageSelector() {
  const { i18n } = useTranslation();
  const { isAuthenticated } = useAuth();
  const toast = useToast();

  const activeLocale = i18n.language as SupportedLocale;

  const handleLanguageChange = useCallback(
    async (locale: SupportedLocale) => {
      if (locale === activeLocale) return;

      // Apply immediately for instant UI feedback (requirement 2.8 / 3.4)
      await i18n.changeLanguage(locale);

      // Persist to backend if authenticated (requirement 2.6)
      if (isAuthenticated) {
        try {
          const response = await ApiService.put('/members/me', {
            preferred_language: locale,
          });

          if (!response.success) {
            throw new Error(response.error || 'Failed to save language preference');
          }
        } catch {
          // On failure: keep local locale active, show non-blocking toast (requirement 2.7 / 3.6)
          toast({
            title: locale === 'nl'
              ? 'Voorkeur kon niet worden opgeslagen'
              : 'Language preference could not be saved',
            status: 'warning',
            duration: 4000,
            isClosable: true,
            position: 'bottom',
          });
        }
      }
    },
    [activeLocale, i18n, isAuthenticated, toast]
  );

  return (
    <Menu>
      <MenuButton
        as={Button}
        variant="ghost"
        colorScheme="orange"
        size="sm"
        rightIcon={<ChevronDownIcon />}
        aria-label="Select language"
        fontWeight="normal"
      >
        <HStack spacing={1}>
          <Text as="span" fontSize="md" aria-hidden="true">
            {LOCALE_FLAGS[activeLocale] ?? LOCALE_FLAGS.nl}
          </Text>
          <Text as="span" fontSize="sm" color="orange.400">
            {LOCALE_NAMES[activeLocale] ?? LOCALE_NAMES.nl}
          </Text>
        </HStack>
      </MenuButton>

      <MenuList zIndex={1500} minW="180px" bg="gray.800" borderColor="orange.400">
        {SUPPORTED_LOCALES.map((locale) => {
          const isActive = locale === activeLocale;
          return (
            <MenuItem
              key={locale}
              onClick={() => handleLanguageChange(locale)}
              fontWeight={isActive ? 'bold' : 'normal'}
              bg="gray.800"
              color="white"
              _hover={{ bg: 'gray.700' }}
              aria-current={isActive ? 'true' : undefined}
              icon={
                isActive ? (
                  <CheckIcon boxSize={3} color="green.400" />
                ) : undefined
              }
            >
              <HStack spacing={2}>
                <Text as="span" fontSize="md" aria-hidden="true">
                  {LOCALE_FLAGS[locale]}
                </Text>
                <Text as="span" fontSize="sm">
                  {LOCALE_NAMES[locale]}
                </Text>
              </HStack>
            </MenuItem>
          );
        })}
      </MenuList>
    </Menu>
  );
}

export default LanguageSelector;
