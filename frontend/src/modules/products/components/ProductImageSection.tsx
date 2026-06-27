import { Box, Button, VStack, HStack, Text, Image } from '@chakra-ui/react';
import { uploadToS3 } from '../services/s3Upload';
import { useState } from 'react';

interface ProductImageSectionProps {
  images: string[];
  productId: string;
  readOnly: boolean;
  setFieldValue: (field: string, value: any) => void;
}

/**
 * Image upload and gallery section for ProductCard.
 * Handles S3 upload and displays thumbnails with delete option.
 */
export function ProductImageSection({ images, productId, readOnly, setFieldValue }: ProductImageSectionProps) {
  const [uploading, setUploading] = useState<boolean>(false);

  const handleUpload = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.multiple = true;
    input.onchange = async (e) => {
      const target = (e as any).target as HTMLInputElement;
      const files = Array.from(target.files || []);
      if (files.length > 0) {
        try {
          setUploading(true);
          const uploadPromises = files.map(file => uploadToS3(file, productId));
          const s3Urls = await Promise.all(uploadPromises);
          const currentImages = images || [];
          setFieldValue('images', [...currentImages, ...s3Urls]);
        } catch (error: any) {
          console.error('Error uploading images:', error);
          alert('Upload failed: ' + error.message);
        } finally {
          setUploading(false);
        }
      }
    };
    input.click();
  };

  return (
    <>
      <Button
        colorScheme="orange"
        size="sm"
        isDisabled={readOnly}
        onClick={handleUpload}
      >
        + Afbeeldingen
      </Button>

      {uploading && <Text color="blue.500">Uploading...</Text>}

      {images && images.length > 0 && (
        <Box mt={3}>
          <Text fontSize="sm" fontWeight="bold" mb={2}>Afbeeldingen ({images.length}):</Text>
          <VStack spacing={2}>
            {images.map((imageUrl: string, index: number) => (
              <HStack key={index} spacing={2} width="100%">
                <Image
                  src={imageUrl}
                  boxSize="78px"
                  objectFit="cover"
                  border="1px solid gray"
                  borderRadius="md"
                />
                <Text fontSize="xs" flex={1} isTruncated>{String(imageUrl || '').split('/').pop()?.replace(/[<>"'&]/g, '') || 'Unknown'}</Text>
                <Button
                  size="xs"
                  colorScheme="red"
                  isDisabled={readOnly}
                  onClick={() => {
                    const newImages = images.filter((_: string, i: number) => i !== index);
                    setFieldValue('images', newImages);
                  }}
                >
                  ×
                </Button>
              </HStack>
            ))}
          </VStack>
        </Box>
      )}
    </>
  );
}
