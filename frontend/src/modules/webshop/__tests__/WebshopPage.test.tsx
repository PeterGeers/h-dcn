import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';

// Mock react-i18next BEFORE importing WebshopPage (due to i18n init import chain).
// IMPORTANT: `t` and the returned object must be STABLE across renders. WebshopPage
// memoizes loadProducts with useCallback([toast, t]) and runs it in a useEffect whose
// deps include that callback. If the mock returns a fresh `t` every render, the callback
// identity changes each render, the effect re-fires, setState re-renders, and the test
// hangs in an infinite loop. Returning a singleton keeps the callback stable.
jest.mock('react-i18next', () => {
  const stableT = (key: string) => key;
  const stableI18n = { language: 'nl', changeLanguage: jest.fn() };
  const stableUseTranslation = { t: stableT, i18n: stableI18n };
  return {
    useTranslation: () => stableUseTranslation,
    initReactI18next: { type: '3rdParty', init: jest.fn() },
  };
});

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

// Mock useAdminOrders hook (avoids axios ESM import issue in test environment)
jest.mock('../../webshop-management/hooks/useAdminOrders', () => ({
  useAdminOrders: () => ({
    orders: [],
    loading: false,
    error: null,
    refetch: jest.fn(),
  }),
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
