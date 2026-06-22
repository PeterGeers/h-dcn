/**
 * ClubLogoUploader — Clickable club logo with upload functionality.
 *
 * Renders the club logo (or a placeholder) as a 48×48 rounded image.
 * Clicking opens a file dialog for selecting a new logo image.
 * The selected image is validated, base64-encoded, and sent to the backend.
 *
 * Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5,
 *            3.1, 3.2, 6.2, 6.3, 7.1, 7.2, 7.3
 */

import React, { useRef, useState, useCallback } from 'react';
import {
  Box,
  Image,
  Tooltip,
  Spinner,
  useToast,
} from '@chakra-ui/react';
import { ApiService } from '../../../services/apiService';

// --- Constants ---

const MAX_FILE_SIZE = 5_242_880; // 5MB in bytes
const ACCEPTED_TYPES = 'image/png,image/jpeg,image/webp,image/gif';
const LOGO_BASE_URL =
  'https://h-dcn-frontend-506221081911.s3.eu-west-1.amazonaws.com/assets/presmeet/logos';

// --- Types ---

export interface ClubLogoUploaderProps {
  clubId: string;
  isAdmin?: boolean;
}

// --- Component ---

const ClubLogoUploader: React.FC<ClubLogoUploaderProps> = ({ clubId, isAdmin }) => {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [cacheBuster, setCacheBuster] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Build the current logo URL (with cache-bust param if available)
  const getLogoUrl = useCallback((): string => {
    const base = `${LOGO_BASE_URL}/${clubId}.png`;
    return cacheBuster ? `${base}?t=${cacheBuster}` : base;
  }, [clubId, cacheBuster]);

  // Handle click on logo / placeholder
  const handleClick = () => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  };

  // Handle image load error (logo doesn't exist yet)
  const handleImageError = () => {
    setHasError(true);
  };

  // Handle image load success
  const handleImageLoad = () => {
    setHasError(false);
  };

  // Validate and upload selected file
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Reset input so same file can be re-selected
    event.target.value = '';

    // Client-side size validation
    if (file.size > MAX_FILE_SIZE) {
      toast({
        title: 'File too large',
        description: 'Maximum size is 5MB',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      return;
    }

    // Read file as base64
    const base64Data = await readFileAsBase64(file);
    const previousCacheBuster = cacheBuster;
    const previousHasError = hasError;

    setIsUploading(true);

    try {
      const response = await ApiService.post<{ logo_url: string }>('/presmeet/logo', {
        image_data: base64Data,
        club_id: clubId,
        content_type: file.type,
      });

      if (response.success && response.data?.logo_url) {
        // Extract cache-bust param from returned URL
        const url = new URL(response.data.logo_url);
        const timestamp = url.searchParams.get('t');
        setCacheBuster(timestamp ?? String(Date.now()));
        setHasError(false);

        toast({
          title: 'Logo updated',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      } else {
        // API returned an error response
        const errorMessage = response.error || 'Upload failed';
        toast({
          title: 'Upload failed',
          description: errorMessage,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });

        // Revert to previous state
        setCacheBuster(previousCacheBuster);
        setHasError(previousHasError);
      }
    } catch (error) {
      // Network failure
      toast({
        title: 'Upload failed',
        description: 'Please check your connection and try again',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });

      // Revert to previous state
      setCacheBuster(previousCacheBuster);
      setHasError(previousHasError);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Tooltip label="Click to upload club logo" hasArrow>
      <Box
        position="relative"
        w="48px"
        h="48px"
        borderRadius="full"
        overflow="hidden"
        cursor={isUploading ? 'default' : 'pointer'}
        onClick={handleClick}
        border="2px solid"
        borderColor="gray.200"
        _hover={{ borderColor: 'orange.300', opacity: isUploading ? 1 : 0.8 }}
        transition="all 0.2s"
        flexShrink={0}
      >
        {/* Logo image or placeholder */}
        {hasError ? (
          <Box
            w="100%"
            h="100%"
            bg="gray.100"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Box
              as="svg"
              viewBox="0 0 24 24"
              boxSize={5}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              color="gray.400"
              data-testid="placeholder-icon"
            >
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </Box>
          </Box>
        ) : (
          <Image
            src={getLogoUrl()}
            alt={`Club logo`}
            w="100%"
            h="100%"
            objectFit="cover"
            onError={handleImageError}
            onLoad={handleImageLoad}
          />
        )}

        {/* Loading overlay */}
        {isUploading && (
          <Box
            position="absolute"
            top={0}
            left={0}
            w="100%"
            h="100%"
            bg="blackAlpha.500"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Spinner size="sm" color="white" />
          </Box>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
      </Box>
    </Tooltip>
  );
};

// --- Helpers ---

/**
 * Read a File as a base64-encoded string (without the data URL prefix).
 */
function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Remove the data URL prefix (e.g., "data:image/png;base64,")
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}

export default ClubLogoUploader;
