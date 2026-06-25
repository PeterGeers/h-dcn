/**
 * RegistryRowLogo Component Unit Tests
 *
 * Tests for the registry row logo display and placeholder behavior.
 *
 * Validates: Requirements 3.3, 3.4
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import RegistryRowLogo from '../components/RegistryRowLogo';

// Mock Chakra UI
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, onClick, ...props }: any) => (
    <div onClick={onClick} {...props}>
      {children}
    </div>
  ),
  Image: ({ src, alt, onError, onLoad, ...props }: any) => (
    <img
      src={src}
      alt={alt}
      onError={onError}
      onLoad={onLoad}
      {...props}
    />
  ),
  Tooltip: ({ children }: any) => <>{children}</>,
  Spinner: () => <span data-testid="spinner" />,
  useToast: () => jest.fn(),
}));

// Mock resizeImage utility
jest.mock('../../../utils/imageResize', () => ({
  resizeImage: jest.fn(),
}));

describe('RegistryRowLogo', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // --- Requirement 3.3: Displays 48×48 rounded image when URL provided ---

  it('renders an image element when logoUrl is a non-empty string', () => {
    render(<RegistryRowLogo logoUrl="https://example.com/logo.png" />);

    const image = screen.getByTestId('logo-image');
    expect(image).toBeInTheDocument();
    expect(image).toHaveAttribute('src', 'https://example.com/logo.png');
  });

  it('renders logo container with 48px dimensions', () => {
    render(<RegistryRowLogo logoUrl="https://example.com/logo.png" />);

    const container = screen.getByTestId('registry-row-logo');
    expect(container).toBeInTheDocument();
    // Verify the container has the correct size props
    expect(container).toHaveAttribute('w', '48px');
    expect(container).toHaveAttribute('h', '48px');
  });

  it('renders image with alt text including label when provided', () => {
    render(<RegistryRowLogo logoUrl="https://example.com/logo.png" label="Team Alpha" />);

    const image = screen.getByTestId('logo-image');
    expect(image).toHaveAttribute('alt', 'Team Alpha logo');
  });

  it('renders image with generic alt text when label is not provided', () => {
    render(<RegistryRowLogo logoUrl="https://example.com/logo.png" />);

    const image = screen.getByTestId('logo-image');
    expect(image).toHaveAttribute('alt', 'Registry row logo');
  });

  // --- Requirement 3.4: Camera placeholder when URL absent/null/empty ---

  it('renders camera placeholder when logoUrl is null', () => {
    render(<RegistryRowLogo logoUrl={null} />);

    expect(screen.getByTestId('logo-placeholder')).toBeInTheDocument();
    expect(screen.getByTestId('placeholder-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('logo-image')).not.toBeInTheDocument();
  });

  it('renders camera placeholder when logoUrl is undefined', () => {
    render(<RegistryRowLogo logoUrl={undefined} />);

    expect(screen.getByTestId('logo-placeholder')).toBeInTheDocument();
    expect(screen.getByTestId('placeholder-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('logo-image')).not.toBeInTheDocument();
  });

  it('renders camera placeholder when logoUrl is an empty string', () => {
    render(<RegistryRowLogo logoUrl="" />);

    expect(screen.getByTestId('logo-placeholder')).toBeInTheDocument();
    expect(screen.getByTestId('placeholder-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('logo-image')).not.toBeInTheDocument();
  });

  it('renders camera placeholder when logoUrl is whitespace only', () => {
    render(<RegistryRowLogo logoUrl="   " />);

    expect(screen.getByTestId('logo-placeholder')).toBeInTheDocument();
    expect(screen.getByTestId('placeholder-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('logo-image')).not.toBeInTheDocument();
  });

  it('does not render image when logoUrl is absent', () => {
    render(<RegistryRowLogo logoUrl={null} />);

    expect(screen.queryByTestId('logo-image')).not.toBeInTheDocument();
  });
});
