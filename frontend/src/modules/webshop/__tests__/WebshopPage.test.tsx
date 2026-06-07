import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';

// Mock react-i18next BEFORE importing WebshopPage (due to i18n init import chain)
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
  initReactI18next: { type: '3rdParty', init: jest.fn() },
}));

// Mock i18n initialization module
jest.mock('../../../i18n', () => ({}));
jest.mock('../../../i18n/index', () => ({}));

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
}));

import WebshopPage from '../WebshopPage';

// Mock apiService
jest.mock('../../../services/apiService', () => ({
  ApiService: {
    get: jest.fn().mockResolvedValue({ success: false }),
    post: jest.fn().mockResolvedValue({ success: true }),
  },
}));

// Mock webshop services
jest.mock('../services/api', () => ({
  productService: {
    scanProducts: jest.fn().mockResolvedValue({ data: [] }),
  },
  cartService: {
    getCart: jest.fn().mockResolvedValue({ data: { items: [] } }),
    createCart: jest.fn().mockResolvedValue({ data: { cartId: 'test-cart' } }),
    updateCartItems: jest.fn().mockResolvedValue({}),
    clearCart: jest.fn().mockResolvedValue({}),
  },
  memberService: {
    getMember: jest.fn().mockResolvedValue({ data: {} }),
  },
  orderService: {
    createOrder: jest.fn().mockResolvedValue({ success: true, data: { order_id: 'test' } }),
  },
}));

// Mock FunctionGuard to just render children
jest.mock('../../../components/common/FunctionGuard', () => ({
  FunctionGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('WebshopPage', () => {
  it('renders without crashing', () => {
    const mockUser = {
      username: 'test-user',
      attributes: {
        email: 'test@example.com',
      },
    };

    expect(() => {
      render(
        <ChakraProvider>
          <WebshopPage user={mockUser} />
        </ChakraProvider>
      );
    }).not.toThrow();
  });
});
