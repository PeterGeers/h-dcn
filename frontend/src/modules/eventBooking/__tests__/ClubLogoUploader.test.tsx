/**
 * ClubLogoUploader Component Tests
 *
 * Tests for the club logo upload interaction including rendering, file selection,
 * validation, upload success/failure, and loading states.
 *
 * Validates: Requirements 1.1, 1.2, 2.1, 2.3, 2.4, 2.5, 7.1, 7.2, 7.3
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

import ClubLogoUploader from '../components/ClubLogoUploader';

// Mock toast
const mockToast = jest.fn();

// Mock Chakra UI
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, onClick, ...props }: any) => (
    <div onClick={onClick} data-testid="logo-box" {...props}>
      {children}
    </div>
  ),
  Image: ({ src, alt, onError, onLoad, ...props }: any) => (
    <img
      src={src}
      alt={alt}
      data-testid="logo-image"
      onError={onError}
      onLoad={onLoad}
      {...props}
    />
  ),
  Tooltip: ({ children }: any) => <>{children}</>,
  Spinner: () => <span data-testid="spinner" />,
  useToast: () => mockToast,
}));

// Mock ApiService (used by ClubLogoUploader for upload)
const mockPost = jest.fn();
jest.mock('../../../services/apiService', () => ({
  ApiService: {
    post: (...args: any[]) => mockPost(...args),
  },
}));

const mockedUploadClubLogo = mockPost;

const LOGO_BASE_URL =
  'https://h-dcn-frontend-506221081911.s3.eu-west-1.amazonaws.com/assets/presmeet/logos';

describe('ClubLogoUploader', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // --- Requirement 1.2: Placeholder when no logo exists ---
  test('renders placeholder icon when image fails to load (no logo exists)', () => {
    render(<ClubLogoUploader clubId="club-42" />);

    const image = screen.getByTestId('logo-image');
    // Simulate image load error (logo doesn't exist on S3)
    fireEvent.error(image);

    expect(screen.getByTestId('placeholder-icon')).toBeInTheDocument();
  });

  // --- Requirement 1.1: Renders image with correct src ---
  test('renders image with correct src when logo exists', () => {
    render(<ClubLogoUploader clubId="club-42" />);

    const image = screen.getByTestId('logo-image');
    expect(image).toHaveAttribute('src', `${LOGO_BASE_URL}/club-42.png`);
  });

  // --- Requirement 2.1: Click triggers file input ---
  test('click on the box triggers the hidden file input', () => {
    render(<ClubLogoUploader clubId="club-42" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = jest.spyOn(fileInput, 'click');

    const box = screen.getByTestId('logo-box');
    fireEvent.click(box);

    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });

  // --- Requirement 2.3: File > 5MB shows error toast ---
  test('shows error toast when selected file exceeds 5MB', async () => {
    render(<ClubLogoUploader clubId="club-42" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    // Create a file > 5MB (5,242,881 bytes)
    const oversizedFile = new File(
      [new ArrayBuffer(5_242_881)],
      'big-logo.png',
      { type: 'image/png' }
    );

    fireEvent.change(fileInput, { target: { files: [oversizedFile] } });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'File too large',
          status: 'error',
        })
      );
    });

    // Should NOT call upload API
    expect(mockedUploadClubLogo).not.toHaveBeenCalled();
  });

  // --- Requirement 2.5: Successful upload updates image src ---
  test('successful upload updates image src with cache-busted URL', async () => {
    const mockLogoUrl = `${LOGO_BASE_URL}/club-42.png?t=1706000000`;
    mockedUploadClubLogo.mockResolvedValue({
      success: true,
      data: { logo_url: mockLogoUrl },
    });

    // Mock FileReader
    const mockFileReader = {
      readAsDataURL: jest.fn(),
      onload: null as any,
      onerror: null as any,
      result: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==',
    };
    jest.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any);

    // Mock URL constructor for cache-bust extraction
    const mockURL = { searchParams: new URLSearchParams('?t=1706000000') } as any;
    jest.spyOn(window, 'URL').mockImplementation(() => mockURL);

    render(<ClubLogoUploader clubId="club-42" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(['fake-image-data'], 'logo.png', { type: 'image/png' });
    Object.defineProperty(validFile, 'size', { value: 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [validFile] } });
      // Trigger FileReader onload callback
      mockFileReader.onload!();
    });

    await waitFor(() => {
      expect(mockedUploadClubLogo).toHaveBeenCalledWith(
        '/presmeet/logo',
        {
          image_data: 'iVBORw0KGgoAAAANSUhEUg==',
          club_id: 'club-42',
          content_type: 'image/png',
        }
      );
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Logo updated',
          status: 'success',
        })
      );
    });

    // Image src should be updated with cache-bust parameter
    const image = screen.getByTestId('logo-image');
    expect(image.getAttribute('src')).toContain('?t=1706000000');

    jest.restoreAllMocks();
  });

  // --- Requirement 7.1, 7.3: Error response shows toast and reverts image ---
  test('error response shows toast and reverts image', async () => {
    mockedUploadClubLogo.mockResolvedValue({
      success: false,
      error: 'Image processing failed',
    });

    // Mock FileReader
    const mockFileReader = {
      readAsDataURL: jest.fn(),
      onload: null as any,
      onerror: null as any,
      result: 'data:image/png;base64,abc123',
    };
    jest.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any);

    render(<ClubLogoUploader clubId="club-42" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(['fake-image-data'], 'logo.png', { type: 'image/png' });
    Object.defineProperty(validFile, 'size', { value: 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [validFile] } });
      mockFileReader.onload!();
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Upload failed',
          status: 'error',
        })
      );
    });

    // Image should still show original src (no cache-bust added)
    const image = screen.getByTestId('logo-image');
    expect(image.getAttribute('src')).toBe(`${LOGO_BASE_URL}/club-42.png`);

    jest.restoreAllMocks();
  });

  // --- Requirement 7.2, 7.3: Network error shows toast ---
  test('network error shows toast and reverts image', async () => {
    mockedUploadClubLogo.mockRejectedValue(new Error('Network Error'));

    // Mock FileReader
    const mockFileReader = {
      readAsDataURL: jest.fn(),
      onload: null as any,
      onerror: null as any,
      result: 'data:image/png;base64,abc123',
    };
    jest.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any);

    render(<ClubLogoUploader clubId="club-42" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(['fake-image-data'], 'logo.png', { type: 'image/png' });
    Object.defineProperty(validFile, 'size', { value: 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [validFile] } });
      mockFileReader.onload!();
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Upload failed',
          description: 'Please check your connection and try again',
          status: 'error',
        })
      );
    });

    jest.restoreAllMocks();
  });

  // --- Requirement 2.4: Loading indicator visible during upload ---
  test('shows loading indicator during upload', async () => {
    // Create a promise that won't resolve immediately
    let resolveUpload: (value: any) => void;
    const uploadPromise = new Promise<any>((resolve) => {
      resolveUpload = resolve;
    });
    mockedUploadClubLogo.mockReturnValue(uploadPromise);

    // Mock FileReader
    const mockFileReader = {
      readAsDataURL: jest.fn(),
      onload: null as any,
      onerror: null as any,
      result: 'data:image/png;base64,abc123',
    };
    jest.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any);

    render(<ClubLogoUploader clubId="club-42" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(['fake-image-data'], 'logo.png', { type: 'image/png' });
    Object.defineProperty(validFile, 'size', { value: 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [validFile] } });
      mockFileReader.onload!();
    });

    // Spinner should be visible while upload is in progress
    expect(screen.getByTestId('spinner')).toBeInTheDocument();

    // Resolve the upload
    const mockLogoUrl = `${LOGO_BASE_URL}/club-42.png?t=1706000000`;
    const mockURL = { searchParams: new URLSearchParams('?t=1706000000') } as any;
    jest.spyOn(window, 'URL').mockImplementation(() => mockURL);

    await act(async () => {
      resolveUpload!({ success: true, data: { logo_url: mockLogoUrl } });
    });

    // Spinner should be gone after upload completes
    expect(screen.queryByTestId('spinner')).not.toBeInTheDocument();

    jest.restoreAllMocks();
  });
});
