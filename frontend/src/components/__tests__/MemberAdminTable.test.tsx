import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import MemberAdminTable from '../MemberAdminTable';

// Mock react-i18next (used by dependencies)
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

describe('MemberAdminTable', () => {
  it('renders without crashing', () => {
    expect(() => {
      render(
        <ChakraProvider>
          <MemberAdminTable
            members={[]}
            userRole="System_User_Management"
            onMemberView={jest.fn()}
            onMemberEdit={jest.fn()}
          />
        </ChakraProvider>
      );
    }).not.toThrow();
  });
});
