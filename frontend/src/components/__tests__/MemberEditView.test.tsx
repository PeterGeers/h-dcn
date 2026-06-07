import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import MemberEditView from '../MemberEditView';

// Mock react-i18next (used by dependencies)
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

describe('MemberEditView', () => {
  it('renders without crashing', () => {
    const mockMember = {
      member_id: 'test-123',
      voornaam: 'Test',
      achternaam: 'User',
      status: 'Actief',
      lidnummer: '1234',
    };

    expect(() => {
      render(
        <ChakraProvider>
          <MemberEditView
            isOpen={true}
            onClose={jest.fn()}
            member={mockMember}
            userRole="System_User_Management"
            onSave={jest.fn()}
          />
        </ChakraProvider>
      );
    }).not.toThrow();
  });
});
