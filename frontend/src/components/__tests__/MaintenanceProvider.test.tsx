/**
 * Maintenance Provider Component Tests
 * 
 * Comprehensive tests for the maintenance provider component including
 * global error handling integration, callback management, and user experience.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock the errorHandler module
jest.mock('../../utils/errorHandler', () => ({
  setMaintenanceScreenCallback: jest.fn(),
  ApiError: class MockApiError {
    constructor(mockStatus, mockMessage, mockIsMaintenanceMode) {
      this.status = mockStatus;
      this.message = mockMessage;
      this.isMaintenanceMode = mockIsMaintenanceMode;
    }
  }
}));

// Mock MaintenanceScreen component
jest.mock('../MaintenanceScreen', () => {
  return function MockMaintenanceScreen({ message, onRetry, showRetry }: any) {
    return (
      <div data-testid="maintenance-screen">
        <div data-testid="maintenance-message">{message}</div>
        {showRetry && (
          <button data-testid="maintenance-retry" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    );
  };
});

import MaintenanceProvider from '../MaintenanceProvider';
import { setMaintenanceScreenCallback } from '../../utils/errorHandler';

// Get the mocked function
const mockSetMaintenanceScreenCallback = setMaintenanceScreenCallback as jest.MockedFunction<typeof setMaintenanceScreenCallback>;

// Mock window.location.reload
const mockReload = jest.fn();
Object.defineProperty(window, 'location', {
  value: {
    reload: mockReload,
  },
  writable: true,
});

describe('MaintenanceProvider Component', () => {
  let mockCallback: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockCallback = jest.fn();
    
    // Capture the callback that gets set
    mockSetMaintenanceScreenCallback.mockImplementation((callback) => {
      mockCallback = callback;
    });
  });

  describe('Initialization', () => {
    test('should set up maintenance screen callback on mount', () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      expect(mockSetMaintenanceScreenCallback).toHaveBeenCalledWith(expect.any(Function));
    });

    test('should render children by default', () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      expect(screen.getByTestId('child-content')).toBeInTheDocument();
      expect(screen.getByText('Normal Content')).toBeInTheDocument();
      expect(screen.queryByTestId('maintenance-screen')).not.toBeInTheDocument();
    });

    test('should clean up callback on unmount', () => {
      const { unmount } = render(
        <MaintenanceProvider>
          <div>Content</div>
        </MaintenanceProvider>
      );

      // Clear the mock to see the cleanup call
      mockSetMaintenanceScreenCallback.mockClear();

      unmount();

      expect(mockSetMaintenanceScreenCallback).toHaveBeenCalledWith(expect.any(Function));
    });
  });

  describe('Maintenance Mode Activation', () => {
    test('should show maintenance screen when callback is triggered', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Trigger maintenance mode
      const testError: ApiError = {
        status: 503,
        message: 'System maintenance in progress',
        isMaintenanceMode: true
      };

      act(() => {
        mockCallback(true, testError);
      });

      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('maintenance-message')).toHaveTextContent('System maintenance in progress');
      expect(screen.queryByTestId('child-content')).not.toBeInTheDocument();
    });

    test('should hide children when maintenance mode is active', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Initially children should be visible
      expect(screen.getByTestId('child-content')).toBeInTheDocument();

      // Trigger maintenance mode
      act(() => {
        mockCallback(true, {
          status: 503,
          message: 'Maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.queryByTestId('child-content')).not.toBeInTheDocument();
      });
      
      expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
    });

    test('should handle maintenance mode without error object', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Trigger maintenance mode without error
      act(() => {
        mockCallback(true);
      });

      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('maintenance-message')).toHaveTextContent(''); // No message
    });
  });

  describe('Maintenance Mode Deactivation', () => {
    test('should hide maintenance screen when callback is triggered with false', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // First activate maintenance mode
      act(() => {
        mockCallback(true, {
          status: 503,
          message: 'Maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });

      // Then deactivate
      act(() => {
        mockCallback(false);
      });

      await waitFor(() => {
        expect(screen.queryByTestId('maintenance-screen')).not.toBeInTheDocument();
      });
      
      expect(screen.getByTestId('child-content')).toBeInTheDocument();
    });

    test('should restore children when maintenance mode is deactivated', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Activate and deactivate maintenance mode
      act(() => {
        mockCallback(true, { status: 503, message: 'Maintenance', isMaintenanceMode: true });
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });
      
      act(() => {
        mockCallback(false);
      });

      await waitFor(() => {
        expect(screen.getByTestId('child-content')).toBeInTheDocument();
      });
      
      expect(screen.getByText('Normal Content')).toBeInTheDocument();
    });
  });

  describe('Retry Functionality', () => {
    test('should handle retry button click', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Activate maintenance mode
      act(() => {
        mockCallback(true, {
          status: 503,
          message: 'System maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('maintenance-retry');
      await userEvent.click(retryButton);

      expect(mockReload).toHaveBeenCalledTimes(1);
    });

    test('should reset maintenance state on retry', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Activate maintenance mode
      act(() => {
        mockCallback(true, {
          status: 503,
          message: 'System maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('maintenance-retry');
      await userEvent.click(retryButton);

      // Should reset state (though page reload will happen)
      expect(mockReload).toHaveBeenCalled();
    });

    test('should handle retry when window.location.reload is not available', async () => {
      // Temporarily remove reload method
      const originalReload = window.location.reload;
      delete (window.location as any).reload;

      // Mock console.error to avoid noise in test output
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // First activate maintenance mode
      act(() => {
        mockCallback(true, {
          status: 503,
          message: 'System maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('maintenance-retry');
      
      // The click will happen but reload will fail - React catches the error
      // We just verify the click doesn't crash the component
      await userEvent.click(retryButton);

      // After retry, the maintenance screen should still be there (since reload failed)
      // but the component should handle the error gracefully
      expect(screen.queryByTestId('maintenance-screen')).toBeInTheDocument();

      // Restore reload method and console
      window.location.reload = originalReload;
      consoleSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    test('should handle different error types', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Test with different error statuses
      const errors = [
        { status: 503, message: 'Service Unavailable', isMaintenanceMode: true },
        { status: 502, message: 'Bad Gateway', isMaintenanceMode: true },
        { status: 500, message: 'Internal Server Error', isMaintenanceMode: true }
      ];

      for (let i = 0; i < errors.length; i++) {
        const error = errors[i];
        
        act(() => {
          mockCallback(true, error);
        });
        
        await waitFor(() => {
          expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
        });
        
        expect(screen.getByTestId('maintenance-message')).toHaveTextContent(error.message);
        
        // Reset for next test
        act(() => {
          mockCallback(false);
        });
        
        await waitFor(() => {
          expect(screen.queryByTestId('maintenance-screen')).not.toBeInTheDocument();
        });
      }
    });

    test('should handle malformed error objects', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Test with malformed error
      const malformedError = { status: 503 } as ApiError; // Missing message

      expect(() => {
        act(() => {
          mockCallback(true, malformedError);
        });
      }).not.toThrow();

      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });
    });

    test('should handle callback errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Should not crash if callback throws
      expect(() => {
        act(() => {
          mockCallback(true, {
            status: 503,
            message: 'Test error',
            isMaintenanceMode: true
          });
        });
      }).not.toThrow();

      consoleSpy.mockRestore();
    });
  });

  describe('Multiple Children', () => {
    test('should handle multiple children correctly', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-1">Child 1</div>
          <div data-testid="child-2">Child 2</div>
          <span data-testid="child-3">Child 3</span>
        </MaintenanceProvider>
      );

      expect(screen.getByTestId('child-1')).toBeInTheDocument();
      expect(screen.getByTestId('child-2')).toBeInTheDocument();
      expect(screen.getByTestId('child-3')).toBeInTheDocument();

      // Activate maintenance mode
      act(() => {
        mockCallback(true, {
          status: 503,
          message: 'Maintenance',
          isMaintenanceMode: true
        });
      });

      await waitFor(() => {
        expect(screen.queryByTestId('child-1')).not.toBeInTheDocument();
        expect(screen.queryByTestId('child-2')).not.toBeInTheDocument();
        expect(screen.queryByTestId('child-3')).not.toBeInTheDocument();
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });
    });

    test('should restore all children after maintenance', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-1">Child 1</div>
          <div data-testid="child-2">Child 2</div>
        </MaintenanceProvider>
      );

      // Activate and deactivate maintenance
      act(() => {
        mockCallback(true, { status: 503, message: 'Maintenance', isMaintenanceMode: true });
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });
      
      act(() => {
        mockCallback(false);
      });

      await waitFor(() => {
        expect(screen.getByTestId('child-1')).toBeInTheDocument();
        expect(screen.getByTestId('child-2')).toBeInTheDocument();
      });
    });
  });

  describe('State Management', () => {
    test('should maintain separate error state', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      const error1 = { status: 503, message: 'Error 1', isMaintenanceMode: true };
      const error2 = { status: 502, message: 'Error 2', isMaintenanceMode: true };

      // Set first error
      act(() => {
        mockCallback(true, error1);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('maintenance-message')).toHaveTextContent('Error 1');
      });

      // Set second error
      act(() => {
        mockCallback(true, error2);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('maintenance-message')).toHaveTextContent('Error 2');
      });

      // Clear maintenance
      act(() => {
        mockCallback(false);
      });
      
      await waitFor(() => {
        expect(screen.queryByTestId('maintenance-screen')).not.toBeInTheDocument();
      });
    });

    test('should handle rapid state changes', async () => {
      render(
        <MaintenanceProvider>
          <div data-testid="child-content">Normal Content</div>
        </MaintenanceProvider>
      );

      // Rapid state changes
      act(() => {
        mockCallback(true, { status: 503, message: 'Error', isMaintenanceMode: true });
      });
      
      act(() => {
        mockCallback(false);
      });
      
      act(() => {
        mockCallback(true, { status: 503, message: 'Error 2', isMaintenanceMode: true });
      });
      
      act(() => {
        mockCallback(false);
      });

      await waitFor(() => {
        expect(screen.getByTestId('child-content')).toBeInTheDocument();
        expect(screen.queryByTestId('maintenance-screen')).not.toBeInTheDocument();
      });
    });
  });

  describe('Integration Scenarios', () => {
    test('should work with complex child components', async () => {
      const ComplexChild = () => (
        <div data-testid="complex-child">
          <button data-testid="child-button">Click me</button>
          <input data-testid="child-input" placeholder="Type here" />
        </div>
      );

      render(
        <MaintenanceProvider>
          <ComplexChild />
        </MaintenanceProvider>
      );

      expect(screen.getByTestId('complex-child')).toBeInTheDocument();
      expect(screen.getByTestId('child-button')).toBeInTheDocument();
      expect(screen.getByTestId('child-input')).toBeInTheDocument();

      // Activate maintenance
      act(() => {
        mockCallback(true, { status: 503, message: 'Maintenance', isMaintenanceMode: true });
      });

      await waitFor(() => {
        expect(screen.queryByTestId('complex-child')).not.toBeInTheDocument();
        expect(screen.getByTestId('maintenance-screen')).toBeInTheDocument();
      });
    });

    test('should handle nested providers', () => {
      render(
        <MaintenanceProvider>
          <MaintenanceProvider>
            <div data-testid="nested-content">Nested Content</div>
          </MaintenanceProvider>
        </MaintenanceProvider>
      );

      expect(screen.getByTestId('nested-content')).toBeInTheDocument();
      
      // Both providers should set up callbacks
      expect(mockSetMaintenanceScreenCallback).toHaveBeenCalledTimes(2);
    });
  });
});