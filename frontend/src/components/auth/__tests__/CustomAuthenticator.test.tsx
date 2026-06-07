import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { CustomAuthenticator } from '../CustomAuthenticator';

// Mock aws-amplify/auth
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn().mockResolvedValue({ tokens: undefined }),
  signOut: jest.fn().mockResolvedValue(undefined),
  signIn: jest.fn(),
  confirmSignIn: jest.fn(),
}));

// Mock aws-amplify/utils
jest.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: jest.fn().mockReturnValue(() => {}),
  },
}));

// Mock useAuth hook (used by CustomAuthenticator)
jest.mock('../../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    error: null,
    signOut: jest.fn(),
  }),
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

describe('CustomAuthenticator', () => {
  it('renders without crashing', () => {
    expect(() => {
      render(
        <ChakraProvider>
          <CustomAuthenticator>
            {({ signOut, user }) => <div>Authenticated</div>}
          </CustomAuthenticator>
        </ChakraProvider>
      );
    }).not.toThrow();
  });
});
