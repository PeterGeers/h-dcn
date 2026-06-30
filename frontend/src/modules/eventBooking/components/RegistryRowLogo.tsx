/**
 * RegistryRowLogo — Displays a registry row logo (or placeholder) with optional upload.
 *
 * Renders the logo as a 48×48 rounded image when `logoUrl` is provided.
 * Shows a camera icon placeholder when logo is absent/null/empty.
 * If `isAdmin` is true and `onUpload` is provided, clicking opens a file dialog
 * for selecting a new logo image. The image is resized client-side before upload.
 *
 * Validates: Requirements 3.3, 3.4, 4.3
 */

import React, { useRef, useState } from 'react';
import {
  Box,
  Image,
  Tooltip,
  Spinner,
  useToast,
} from '@chakra-ui/react';
import { resizeImage } from '../../../utils/imageResize';

// --- Constants ---

const MAX_FILE_SIZE = 5_242_880; // 5MB in bytes
const ACCEPTED_TYPES = 'image/png,image/jpeg,image/webp,image/gif';

// --- Types ---

export interface RegistryRowLogoProps {
  logoUrl: string | null | undefined;
  label?: string;
  isAdmin?: boolean;
  onUpload?: (file: File) => void;
}

// --- Component ---

const RegistryRowLogo: React.FC<RegistryRowLogoProps> = ({
  logoUrl,
  label,
  isAdmin = false,
  onUpload,
}) => {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [hasError, setHasError] = useState(false);

  const hasLogo = typeof logoUrl === 'string' && logoUrl.trim().length > 0;
  const canUpload = isAdmin && !!onUpload;

  const handleClick = () => {
    if (canUpload && !isUploading) {
      fileInputRef.current?.click();
    }
  };

  const handleImageError = () => {
    setHasError(true);
  };

  const handleImageLoad = () => {
    setHasError(false);
  };

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

    setIsUploading(true);

    try {
      // Resize image to 200×200 max (logo dimensions)
      const resizedFile = await resizeImage(file, {
        maxWidth: 200,
        maxHeight: 200,
        quality: 0.9,
        format: 'png',
      });

      // Notify parent with the resized file
      onUpload?.(resizedFile);

      toast({
        title: 'Logo uploaded',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Upload failed',
        description: 'Could not process the image',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsUploading(false);
    }
  };

  const tooltipLabel = canUpload
    ? `Click to upload ${label || 'logo'}`
    : label || 'Logo';

  const showPlaceholder = !hasLogo || hasError;

  return (
    <Tooltip label={tooltipLabel} hasArrow>
      <Box
        position="relative"
        w="48px"
        h="48px"
        borderRadius="full"
        overflow="hidden"
        cursor={canUpload && !isUploading ? 'pointer' : 'default'}
        onClick={handleClick}
        border="2px solid"
        borderColor="gray.200"
        _hover={canUpload ? { borderColor: 'orange.300', opacity: 0.8 } : undefined}
        transition="all 0.2s"
        flexShrink={0}
        data-testid="registry-row-logo"
      >
        {/* Logo image or placeholder */}
        {showPlaceholder ? (
          <Box
            w="100%"
            h="100%"
            bg="gray.100"
            display="flex"
            alignItems="center"
            justifyContent="center"
            data-testid="logo-placeholder"
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
            src={logoUrl!}
            alt={label ? `${label} logo` : 'Registry row logo'}
            w="100%"
            h="100%"
            objectFit="cover"
            onError={handleImageError}
            onLoad={handleImageLoad}
            data-testid="logo-image"
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

        {/* Hidden file input (only rendered when upload is enabled) */}
        {canUpload && (
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
        )}
      </Box>
    </Tooltip>
  );
};

export default RegistryRowLogo;
