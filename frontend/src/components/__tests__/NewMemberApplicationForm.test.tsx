import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import NewMemberApplicationForm from '../NewMemberApplicationForm';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock apiService (used for checking existing application)
jest.mock('../../services/apiService', () => ({
  ApiService: {
    get: jest.fn().mockResolvedValue({ success: false }),
    post: jest.fn().mockResolvedValue({ success: true }),
  },
}));

describe('NewMemberApplicationForm', () => {
  it('renders without crashing', () => {
    expect(() => {
      render(
        <ChakraProvider>
          <NewMemberApplicationForm
            userEmail="test@example.com"
            onSubmit={jest.fn()}
          />
        </ChakraProvider>
      );
    }).not.toThrow();
  });
});
