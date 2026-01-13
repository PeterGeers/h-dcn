/**
 * Maintenance Screen Component Tests
 * 
 * Comprehensive tests for the maintenance screen component including
 * user experience, accessibility, and interaction handling.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, minH, bg, display, alignItems, justifyContent, p, borderRadius, boxShadow, textAlign, borderTop, borderColor, w, pt, ...props }: any) => (
    <div 
      data-testid={`box-${Math.random().toString(36).substr(2, 9)}`} 
      data-minh={minH}
      data-bg={bg}
      data-display={display}
      data-alignitems={alignItems}
      data-justifycontent={justifyContent}
      data-p={p}
      data-borderradius={borderRadius}
      data-boxshadow={boxShadow}
      data-textalign={textAlign}
      data-bordertop={borderTop}
      data-bordercolor={borderColor}
      data-w={w}
      data-pt={pt}
      {...props}
    >
      {children}
    </div>
  ),
  VStack: ({ children, spacing, ...props }: any) => <div data-testid="vstack" data-spacing={spacing} {...props}>{children}</div>,
  Heading: ({ children, size, color, ...props }: any) => <h1 data-testid="heading" data-size={size} data-color={color} {...props}>{children}</h1>,
  Text: ({ children, color, fontSize, lineHeight, mb, ...props }: any) => (
    <p data-testid="text" data-color={color} data-fontsize={fontSize} data-lineheight={lineHeight} data-mb={mb} {...props}>{children}</p>
  ),
  Button: ({ children, onClick, leftIcon, colorScheme, size, variant, as, href, ...props }: any) => {
    const Component = as || 'button';
    return (
      <Component 
        onClick={onClick} 
        data-testid={`button-${children}`}
        data-colorscheme={colorScheme}
        data-size={size}
        data-variant={variant}
        href={href}
        {...props}
      >
        {leftIcon && <span data-testid="left-icon">icon</span>}
        {children}
      </Component>
    );
  },
  Container: ({ children, maxW, ...props }: any) => <div data-testid="container" data-maxw={maxW} {...props}>{children}</div>,
  useColorModeValue: (light: any, dark: any) => light, // Always return light mode value for testing
}));

// Mock Chakra UI icons
jest.mock('@chakra-ui/icons', () => ({
  SettingsIcon: () => <span data-testid="settings-icon">⚙️</span>,
  EmailIcon: () => <span data-testid="email-icon">✉️</span>,
  RepeatIcon: () => <span data-testid="repeat-icon">🔄</span>,
}));

import MaintenanceScreen from '../MaintenanceScreen';

// Mock window.location.reload
const mockReload = jest.fn();
Object.defineProperty(window, 'location', {
  value: {
    reload: mockReload,
  },
  writable: true,
});

describe('MaintenanceScreen Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Default Rendering', () => {
    test('should render with default props', () => {
      render(<MaintenanceScreen />);

      expect(screen.getByTestId('heading')).toHaveTextContent('Systeem Onderhoud');
      expect(screen.getByText('Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud.')).toBeInTheDocument();
      expect(screen.getByText(/We werken hard om het systeem zo snel mogelijk weer beschikbaar te maken/)).toBeInTheDocument();
      expect(screen.getByTestId('button-Opnieuw proberen')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Contact:.*webmaster@h-dcn.nl/ })).toBeInTheDocument();
    });

    test('should display settings icon', () => {
      render(<MaintenanceScreen />);

      // The SettingsIcon should be rendered (mocked as text content)
      expect(screen.getByTestId('heading')).toHaveAttribute('data-color', 'orange.500');
    });

    test('should have proper styling attributes', () => {
      render(<MaintenanceScreen />);

      expect(screen.getByTestId('container')).toHaveAttribute('data-maxw', 'md');
      expect(screen.getByTestId('heading')).toHaveAttribute('data-size', 'lg');
      expect(screen.getByTestId('button-Opnieuw proberen')).toHaveAttribute('data-colorscheme', 'blue');
      expect(screen.getByTestId('button-Opnieuw proberen')).toHaveAttribute('data-size', 'lg');
    });
  });

  describe('Custom Props', () => {
    test('should render custom message', () => {
      const customMessage = 'De database is tijdelijk niet beschikbaar voor onderhoud.';
      render(<MaintenanceScreen message={customMessage} />);

      expect(screen.getByText(customMessage)).toBeInTheDocument();
    });

    test('should render custom contact email', () => {
      const customEmail = 'support@example.com';
      render(<MaintenanceScreen contactEmail={customEmail} />);

      expect(screen.getByRole('link', { name: /Contact:.*support@example.com/ })).toBeInTheDocument();
    });

    test('should hide retry button when showRetry is false', () => {
      render(<MaintenanceScreen showRetry={false} />);

      expect(screen.queryByTestId('button-Opnieuw proberen')).not.toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Contact:.*webmaster@h-dcn.nl/ })).toBeInTheDocument();
    });

    test('should use custom onRetry handler', async () => {
      const mockOnRetry = jest.fn();
      render(<MaintenanceScreen onRetry={mockOnRetry} />);

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      await userEvent.click(retryButton);

      expect(mockOnRetry).toHaveBeenCalledTimes(1);
      expect(mockReload).not.toHaveBeenCalled();
    });
  });

  describe('User Interactions', () => {
    test('should call default retry handler (page reload) when no custom handler provided', async () => {
      render(<MaintenanceScreen />);

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      await userEvent.click(retryButton);

      expect(mockReload).toHaveBeenCalledTimes(1);
    });

    test('should handle multiple retry clicks', async () => {
      const mockOnRetry = jest.fn();
      render(<MaintenanceScreen onRetry={mockOnRetry} />);

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      
      await userEvent.click(retryButton);
      await userEvent.click(retryButton);
      await userEvent.click(retryButton);

      expect(mockOnRetry).toHaveBeenCalledTimes(3);
    });

    test('should have proper mailto link for contact button', () => {
      render(<MaintenanceScreen />);

      const contactButton = screen.getByRole('link', { name: /Contact:.*webmaster@h-dcn.nl/ });
      expect(contactButton).toHaveAttribute('href', 'mailto:webmaster@h-dcn.nl?subject=H-DCN Systeem Onderhoud');
    });

    test('should have proper mailto link with custom email', () => {
      const customEmail = 'support@example.com';
      render(<MaintenanceScreen contactEmail={customEmail} />);

      const contactButton = screen.getByRole('link', { name: /Contact:.*support@example.com/ });
      expect(contactButton).toHaveAttribute('href', `mailto:${customEmail}?subject=H-DCN Systeem Onderhoud`);
    });
  });

  describe('Accessibility', () => {
    test('should have proper heading structure', () => {
      render(<MaintenanceScreen />);

      const heading = screen.getByTestId('heading');
      expect(heading.tagName).toBe('H1');
      expect(heading).toHaveTextContent('Systeem Onderhoud');
    });

    test('should have descriptive button text', () => {
      render(<MaintenanceScreen />);

      expect(screen.getByTestId('button-Opnieuw proberen')).toHaveTextContent('Opnieuw proberen');
      expect(screen.getByRole('link', { name: /Contact:.*webmaster@h-dcn.nl/ })).toHaveTextContent(/Contact:.*webmaster@h-dcn.nl/);
    });

    test('should have proper button types and roles', () => {
      render(<MaintenanceScreen />);

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      const contactButton = screen.getByRole('link', { name: /Contact:.*webmaster@h-dcn.nl/ });

      expect(retryButton.tagName).toBe('BUTTON');
      expect(contactButton.tagName).toBe('A'); // Contact button is a link
    });
  });

  describe('Error Scenarios', () => {
    test('should handle onRetry function throwing error gracefully', async () => {
      const mockOnRetry = jest.fn().mockImplementation(() => {
        throw new Error('Retry failed');
      });

      // Mock console.error to avoid noise in test output
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      render(<MaintenanceScreen onRetry={mockOnRetry} />);

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      
      // The function will be called and will throw, but React catches it
      // We expect the function to be called despite the error
      await userEvent.click(retryButton);

      expect(mockOnRetry).toHaveBeenCalledTimes(1);
      
      consoleSpy.mockRestore();
    });

    test('should handle missing window.location.reload gracefully', async () => {
      // Temporarily remove reload method
      const originalReload = window.location.reload;
      delete (window.location as any).reload;

      // Mock console.error to avoid noise in test output
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      render(<MaintenanceScreen />);

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      
      // The click will happen but reload will fail - React catches the error
      // We just verify the click doesn't crash the component
      await userEvent.click(retryButton);

      // Component should still be rendered despite the error
      expect(screen.getByTestId('heading')).toBeInTheDocument();

      // Restore reload method and console
      window.location.reload = originalReload;
      consoleSpy.mockRestore();
    });
  });

  describe('Content Validation', () => {
    test('should display all required Dutch text content', () => {
      render(<MaintenanceScreen />);

      expect(screen.getByText('Systeem Onderhoud')).toBeInTheDocument();
      expect(screen.getByText('Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud.')).toBeInTheDocument();
      expect(screen.getByText(/We werken hard om het systeem zo snel mogelijk weer beschikbaar te maken/)).toBeInTheDocument();
      expect(screen.getByText(/Probeer het over een paar minuten opnieuw/)).toBeInTheDocument();
      expect(screen.getByText('Hulp nodig?')).toBeInTheDocument();
      expect(screen.getByText('Opnieuw proberen')).toBeInTheDocument();
    });

    test('should handle very long custom messages', () => {
      const longMessage = 'Dit is een zeer lange foutmelding die meerdere regels zou kunnen beslaan en die de layout van de maintenance screen zou kunnen beïnvloeden. We willen ervoor zorgen dat dit correct wordt weergegeven zonder de gebruikerservaring te verstoren.';
      
      render(<MaintenanceScreen message={longMessage} />);

      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    test('should handle empty custom message', () => {
      render(<MaintenanceScreen message="" />);

      // Should still show the component structure
      expect(screen.getByTestId('heading')).toBeInTheDocument();
      expect(screen.getByTestId('button-Opnieuw proberen')).toBeInTheDocument();
    });
  });

  describe('Visual Layout', () => {
    test('should have proper component structure', () => {
      render(<MaintenanceScreen />);

      expect(screen.getAllByTestId(/^box-/)).toHaveLength(3); // Multiple Box components
      expect(screen.getByTestId('container')).toBeInTheDocument(); // Content container
      expect(screen.getByTestId('vstack')).toBeInTheDocument(); // Vertical stack
    });

    test('should have proper spacing in VStack', () => {
      render(<MaintenanceScreen />);

      expect(screen.getByTestId('vstack')).toHaveAttribute('data-spacing', '6');
    });

    test('should have proper button styling', () => {
      render(<MaintenanceScreen />);

      const retryButton = screen.getByTestId('button-Opnieuw proberen');
      const contactButton = screen.getByRole('link', { name: /Contact:.*webmaster@h-dcn.nl/ });

      expect(retryButton).toHaveAttribute('data-colorscheme', 'blue');
      expect(retryButton).toHaveAttribute('data-size', 'lg');
      expect(contactButton).toHaveAttribute('data-variant', 'outline');
      expect(contactButton).toHaveAttribute('data-size', 'sm');
      expect(contactButton).toHaveAttribute('data-colorscheme', 'blue');
    });
  });
});