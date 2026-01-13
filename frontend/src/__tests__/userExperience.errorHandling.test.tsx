/**
 * User Experience Error Handling Integration Tests
 * 
 * End-to-end tests for error handling from the user's perspective,
 * including authentication failures, maintenance mode, and recovery flows.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => {
    const { minH, alignItems, justifyContent, borderTop, borderColor, borderRadius, boxShadow, textAlign, ...restProps } = props;
    return <div data-testid="box" {...restProps}>{children}</div>;
  },
  VStack: ({ children, spacing, ...props }: any) => <div data-testid="vstack" data-spacing={spacing} {...props}>{children}</div>,
  HStack: ({ children }: any) => <div data-testid="hstack">{children}</div>,
  Text: ({ children, color, fontSize, lineHeight, ...props }: any) => {
    const { mb, ...restProps } = props;
    return <span data-testid="text" {...restProps}>{children}</span>;
  },
  Button: ({ children, onClick, isDisabled, isLoading, leftIcon, colorScheme, size, variant, as, href, ...props }: any) => {
    const Component = as || 'button';
    return (
      <Component 
        onClick={onClick} 
        disabled={isDisabled || isLoading} 
        data-testid={`button-${children}`}
        href={href}
        {...props}
      >
        {leftIcon && <span data-testid="left-icon">icon</span>}
        {children}
      </Component>
    );
  },
  Heading: ({ children, size, color, ...props }: any) => <h1 data-testid="heading" {...props}>{children}</h1>,
  Alert: ({ children }: any) => <div role="alert" data-testid="alert">{children}</div>,
  AlertIcon: () => <span data-testid="alert-icon">!</span>,
  Container: ({ children, maxW, ...props }: any) => <div data-testid="container" {...props}>{children}</div>,
  useToast: () => jest.fn(),
  useColorModeValue: (light: any) => light,
}));

jest.mock('@chakra-ui/icons', () => ({
  SettingsIcon: () => <span data-testid="settings-icon">⚙️</span>,
  EmailIcon: () => <span data-testid="email-icon">✉️</span>,
  RepeatIcon: () => <span data-testid="repeat-icon">🔄</span>,
}));

// Mock API Service
jest.mock('../services/apiService', () => ({
  ApiService: {
    get: jest.fn(),
    post: jest.fn(),
    isAuthenticated: jest.fn(),
    getCurrentUserEmail: jest.fn(),
    getCurrentUserRoles: jest.fn(),
    clearAuth: jest.fn(),
  },
}));

// Mock Auth Headers
jest.mock('../utils/authHeaders', () => ({
  getAuthHeaders: jest.fn(),
  getAuthHeadersForGet: jest.fn(),
}));

// Mock Error Handler
jest.mock('../utils/errorHandler', () => ({
  showMaintenanceScreen: jest.fn(),
  hideMaintenanceScreen: jest.fn(),
  setMaintenanceScreenCallback: jest.fn(),
  parseApiError: jest.fn(),
  handleApiError: jest.fn(),
  ERROR_MESSAGES: {
    NETWORK: 'Netwerkfout - controleer je internetverbinding',
    UNAUTHORIZED: 'Je bent niet geautoriseerd voor deze actie',
    FORBIDDEN: 'Toegang geweigerd - onvoldoende rechten',
    NOT_FOUND: 'Gevraagde gegevens niet gevonden',
    SERVER_ERROR: 'Serverfout - probeer het later opnieuw',
    MAINTENANCE: 'Het systeem is tijdelijk niet beschikbaar voor onderhoud',
    VALIDATION: 'Invoergegevens zijn niet correct',
    TIMEOUT: 'Verzoek duurde te lang - probeer opnieuw',
    UNKNOWN: 'Er is een onbekende fout opgetreden'
  }
}));

// Mock fetch
global.fetch = jest.fn();

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// Mock window.location.reload
const mockReload = jest.fn();
Object.defineProperty(window, 'location', {
  value: { reload: mockReload },
  writable: true,
});

// Import components after mocking
import MaintenanceProvider from '../components/MaintenanceProvider';
import MaintenanceScreen from '../components/MaintenanceScreen';
import { ApiService } from '../services/apiService';
import { setMaintenanceScreenCallback } from '../utils/errorHandler';
import { getAuthHeaders } from '../utils/authHeaders';

// Get the mocked functions
const mockSetMaintenanceScreenCallback = setMaintenanceScreenCallback as jest.MockedFunction<typeof setMaintenanceScreenCallback>;
const mockApiService = ApiService as jest.Mocked<typeof ApiService>;
const mockGetAuthHeaders = getAuthHeaders as jest.MockedFunction<typeof getAuthHeaders>;

// Test App Component that simulates real usage
const TestApp: React.FC = () => {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await ApiService.get('/members');
      if (result.success) {
        setData(result.data);
      } else {
        setError(result.error || 'Unknown error');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setLoading(false);
    }
  };

  const clearData = () => {
    setData(null);
    setError(null);
  };

  return (
    <MaintenanceProvider>
      <div data-testid="app">
        <h1 data-testid="app-title">H-DCN Member Portal</h1>
        
        <div data-testid="controls">
          <button 
            data-testid="load-data-button" 
            onClick={loadData}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Load Member Data'}
          </button>
          
          <button 
            data-testid="clear-data-button" 
            onClick={clearData}
          >
            Clear Data
          </button>
        </div>

        {error && (
          <div data-testid="error-display" role="alert">
            Error: {error}
          </div>
        )}

        {data && (
          <div data-testid="data-display">
            Data loaded: {JSON.stringify(data)}
          </div>
        )}
      </div>
    </MaintenanceProvider>
  );
};

describe('User Experience Error Handling Integration', () => {
  let maintenanceCallback: (show: boolean, error?: any) => void;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Capture the maintenance callback
    mockSetMaintenanceScreenCallback.mockImplementation((callback) => {
      maintenanceCallback = callback;
    });

    // Set up default mocks
    mockApiService.isAuthenticated.mockReturnValue(true);
    mockApiService.getCurrentUserEmail.mockReturnValue('test@example.com');
    mockApiService.getCurrentUserRoles.mockReturnValue(['hdcnLeden']);
    
    mockGetAuthHeaders.mockResolvedValue({
      'Authorization': 'Bearer test-token',
      'Content-Type': 'application/json',
      'X-Enhanced-Groups': JSON.stringify(['hdcnLeden'])
    });
  });

  describe('Normal Operation', () => {
    test('should render app normally when no errors occur', async () => {
      mockApiService.get.mockResolvedValue({
        success: true,
        data: { members: ['John Doe', 'Jane Smith'] }
      });

      render(<TestApp />);

      expect(screen.getByTestId('app-title')).toHaveTextContent('H-DCN Member Portal');
      expect(screen.getByTestId('load-data-button')).toBeInTheDocument();
      expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
    });

    test('should load and display data successfully', async () => {
      const testData = { members: ['John Doe', 'Jane Smith'] };
      mockApiService.get.mockResolvedValue({
        success: true,
        data: testData
      });

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('data-display')).toHaveTextContent(
          `Data loaded: ${JSON.stringify(testData)}`
        );
      });

      expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
    });
  });

  describe('503 Maintenance Mode Experience', () => {
    test('should show maintenance screen when 503 error occurs', async () => {
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Het systeem is tijdelijk niet beschikbaar voor onderhoud'
      });

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      // Simulate the API service triggering maintenance mode
      act(() => {
        maintenanceCallback(true, {
          status: 503,
          message: 'Het systeem is tijdelijk niet beschikbaar voor onderhoud',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.queryByTestId('app')).not.toBeInTheDocument();
        expect(screen.getByText('Systeem Onderhoud')).toBeInTheDocument();
      });
    });

    test('should handle maintenance screen retry', async () => {
      render(<TestApp />);

      // Trigger maintenance mode
      act(() => {
        maintenanceCallback(true, {
          status: 503,
          message: 'System maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Systeem Onderhoud')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      await userEvent.click(retryButton);

      expect(mockReload).toHaveBeenCalledTimes(1);
    });

    test('should show user-friendly maintenance message', async () => {
      render(<TestApp />);

      act(() => {
        maintenanceCallback(true, {
          status: 503,
          message: 'Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud',
          details: 'AUTH_SYSTEM_FAILURE',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud')).toBeInTheDocument();
      });

      // Should not show technical details to user
      expect(screen.queryByText('AUTH_SYSTEM_FAILURE')).not.toBeInTheDocument();
    });
  });

  describe('Authentication Error Experience', () => {
    test('should handle authentication failure gracefully', async () => {
      mockGetAuthHeaders.mockRejectedValue(new Error('No user data found in localStorage'));
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Authentication required'
      });

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toHaveTextContent(
          'Error: Authentication required'
        );
      });

      // App should still be functional
      expect(screen.getByTestId('app')).toBeInTheDocument();
      expect(screen.getByTestId('clear-data-button')).toBeInTheDocument();
    });

    test('should handle 401 unauthorized errors', async () => {
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Je bent niet geautoriseerd voor deze actie'
      });

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toHaveTextContent(
          'Error: Je bent niet geautoriseerd voor deze actie'
        );
      });
    });

    test('should handle 403 forbidden errors', async () => {
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Toegang geweigerd - onvoldoende rechten'
      });

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toHaveTextContent(
          'Error: Toegang geweigerd - onvoldoende rechten'
        );
      });
    });
  });

  describe('Network Error Experience', () => {
    test('should handle network failures gracefully', async () => {
      mockApiService.get.mockRejectedValue(new Error('Failed to fetch'));

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toHaveTextContent(
          'Error: Failed to fetch'
        );
      });

      // User should be able to retry
      expect(screen.getByTestId('load-data-button')).not.toBeDisabled();
    });

    test('should handle timeout errors', async () => {
      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'AbortError';
      mockApiService.get.mockRejectedValue(timeoutError);

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toHaveTextContent(
          'Error: Request timeout'
        );
      });
    });
  });

  describe('Error Recovery Experience', () => {
    test('should allow user to retry after error', async () => {
      // First request fails
      mockApiService.get.mockResolvedValueOnce({
        success: false,
        error: 'Server error'
      });

      // Second request succeeds
      mockApiService.get.mockResolvedValueOnce({
        success: true,
        data: { members: ['Recovered Data'] }
      });

      render(<TestApp />);

      // First attempt
      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toHaveTextContent('Error: Server error');
      });

      // Retry
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('data-display')).toHaveTextContent(
          'Data loaded: {"members":["Recovered Data"]}'
        );
      });

      expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
    });

    test('should allow user to clear error state', async () => {
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Test error'
      });

      render(<TestApp />);

      // Trigger error
      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
      });

      // Clear error
      const clearButton = screen.getByTestId('clear-data-button');
      await userEvent.click(clearButton);

      expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
    });

    test('should handle recovery from maintenance mode', async () => {
      render(<TestApp />);

      // Enter maintenance mode
      act(() => {
        maintenanceCallback(true, {
          status: 503,
          message: 'Maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Systeem Onderhoud')).toBeInTheDocument();
        expect(screen.queryByTestId('app')).not.toBeInTheDocument();
      });

      // Exit maintenance mode
      act(() => {
        maintenanceCallback(false);
      });

      await waitFor(() => {
        expect(screen.queryByText('Systeem Onderhoud')).not.toBeInTheDocument();
        expect(screen.getByTestId('app')).toBeInTheDocument();
      });
    });
  });

  describe('Loading States', () => {
    test('should show loading state during API calls', async () => {
      // Create a promise that we can control
      let resolvePromise: (value: any) => void;
      const controlledPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      mockApiService.get.mockReturnValue(controlledPromise);

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      // Should show loading state
      expect(screen.getByTestId('load-data-button')).toHaveTextContent('Loading...');
      expect(screen.getByTestId('load-data-button')).toBeDisabled();

      // Resolve the promise
      resolvePromise!({
        success: true,
        data: { test: 'data' }
      });

      await waitFor(() => {
        expect(screen.getByTestId('load-data-button')).toHaveTextContent('Load Member Data');
        expect(screen.getByTestId('load-data-button')).not.toBeDisabled();
      });
    });

    test('should handle loading state during errors', async () => {
      let rejectPromise: (error: any) => void;
      const controlledPromise = new Promise((_, reject) => {
        rejectPromise = reject;
      });

      mockApiService.get.mockReturnValue(controlledPromise);

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      expect(screen.getByTestId('load-data-button')).toBeDisabled();

      // Reject the promise
      rejectPromise!(new Error('Network error'));

      await waitFor(() => {
        expect(screen.getByTestId('load-data-button')).not.toBeDisabled();
        expect(screen.getByTestId('error-display')).toHaveTextContent('Error: Network error');
      });
    });
  });

  describe('Accessibility', () => {
    test('should have proper ARIA attributes for errors', async () => {
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Test error'
      });

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      await userEvent.click(loadButton);

      await waitFor(() => {
        const errorDisplay = screen.getByTestId('error-display');
        expect(errorDisplay).toHaveAttribute('role', 'alert');
      });
    });

    test('should maintain focus management during errors', async () => {
      mockApiService.get.mockResolvedValue({
        success: false,
        error: 'Test error'
      });

      render(<TestApp />);

      const loadButton = screen.getByTestId('load-data-button');
      loadButton.focus();
      
      await userEvent.click(loadButton);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
      });

      // Button should still be focusable after error
      expect(loadButton).not.toBeDisabled();
    });
  });
});