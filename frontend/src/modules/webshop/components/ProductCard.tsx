import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Card,
  CardBody,
  Text,
  Button,
  VStack,
  Image,
  Box,
  Select,
  IconButton,
  Flex,
  HStack
} from '@chakra-ui/react';
import { AddIcon, ChevronLeftIcon, ChevronRightIcon, ArrowBackIcon } from '@chakra-ui/icons';

interface Product {
  id: string;
  naam: string;
  prijs: number | string;
  opties?: string;
  images?: string | string[];
  image?: string | string[];
}

interface CartItem {
  product_id: string;
  name?: string;
  naam?: string;
  price?: number;
  quantity: number;
  selectedOption?: string;
  id?: string;
}

interface ProductCardProps {
  product: Product | null;
  isOpen: boolean;
  onClose: () => void;
  onAddToCart: (cartItem: CartItem) => void;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, isOpen, onClose, onAddToCart }) => {
  const [currentImageIndex, setCurrentImageIndex] = useState<number>(0);
  const [selectedOption, setSelectedOption] = useState<string>('');

  if (!product) return null;

  // Handle both 'image' and 'images' properties from API
  let images: string[] = [];
  const imageData = product.images || product.image;
  
  if (imageData) {
    if (Array.isArray(imageData)) {
      images = imageData;
    } else if (typeof imageData === 'string') {
      images = [imageData];
    }
  }
  
  // Fix image URLs if they're incomplete or use them as-is if complete
  images = images.map(img => {
    if (typeof img === 'string') {
      // If URL is already complete, use it as-is
      if (img.startsWith('https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com')) {
        return img;
      }
      // If URL is incomplete, fix it
      if (img.startsWith('https://my-hdcn-bucke')) {
        return img.replace('https://my-hdcn-bucke', 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com');
      }
    }
    return img;
  }).filter(img => img && typeof img === 'string');
  
  // Parse options from opties field (supports comma-separated values)
  const options = product.opties && typeof product.opties === 'string' ? 
    product.opties.split(',').map(opt => opt.trim()).filter(opt => opt.length > 0) : [];

  const nextImage = (): void => {
    setCurrentImageIndex((prev) => (prev + 1) % images.length);
  };

  const prevImage = (): void => {
    setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  const handleAddToCart = (): void => {
    const cartItem: CartItem = {
      product_id: product.id,
      name: product.naam,
      price: Number(product.prijs),
      quantity: 1,
      selectedOption: options.length > 0 ? selectedOption : undefined
    };
    onAddToCart(cartItem);
    onClose();
  };

  const canAddToCart = options.length === 0 || selectedOption;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size={{ base: 'full', md: 'xl' }}>
      <ModalOverlay />
      <ModalContent mx={{ base: 2, md: 'auto' }} my={{ base: 2, md: 'auto' }}>
        <ModalHeader 
          color="black"
          fontSize={{ base: 'lg', md: 'xl' }}
          pr={10}
        >
          {product.naam}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6} px={{ base: 4, md: 6 }}>
          <Card>
            <CardBody>
              <VStack spacing={{ base: 3, md: 4 }} align="stretch">
                {images.length > 0 ? (
                  <Box position="relative">
                    <Image
                      src={images[currentImageIndex]}
                      alt={product.naam}
                      maxH={{ base: '250px', md: '300px' }}
                      w="full"
                      objectFit="contain"
                      mx="auto"
                      onError={(e) => {
                        console.error('Image failed to load:', images[currentImageIndex]);
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                      onLoad={() => {
                        console.log('Image loaded successfully:', images[currentImageIndex]);
                      }}
                    />
                    {images.length > 1 && (
                      <Flex justify="space-between" position="absolute" top="50%" w="100%" px={2}>
                        <IconButton
                          icon={<ChevronLeftIcon />}
                          onClick={prevImage}
                          size={{ base: 'md', md: 'sm' }}
                          bg="white"
                          shadow="md"
                          _hover={{ bg: 'gray.100' }}
                          aria-label="Previous image"
                        />
                        <IconButton
                          icon={<ChevronRightIcon />}
                          onClick={nextImage}
                          size={{ base: 'md', md: 'sm' }}
                          bg="white"
                          shadow="md"
                          _hover={{ bg: 'gray.100' }}
                          aria-label="Next image"
                        />
                      </Flex>
                    )}
                  </Box>
                ) : (
                  <Box 
                    height="300px" 
                    bg="gray.100" 
                    display="flex" 
                    alignItems="center" 
                    justifyContent="center"
                    borderRadius="md"
                  >
                    <Text color="gray.500">Geen afbeelding beschikbaar</Text>
                  </Box>
                )}
                
                <VStack align="start" spacing={2}>
                  <Text fontSize={{ base: 'md', md: 'lg' }}>
                    Prijs: <Text as="span" fontWeight="bold" fontSize={{ base: 'lg', md: 'xl' }}>€{product.prijs ? Number(product.prijs).toFixed(2) : '0.00'}</Text>
                  </Text>
                  <Text fontSize={{ base: 'sm', md: 'md' }}>
                    <strong>Product:</strong> {product.naam}
                  </Text>
                </VStack>

                {options.length > 0 && (
                  <Box>
                    <Text fontWeight="medium" mb={2}>Opties:</Text>
                    <Select
                      placeholder="Selecteer een optie"
                      value={selectedOption}
                      onChange={(e) => setSelectedOption(e.target.value)}
                    >
                      {options.map((option, index) => (
                        <option key={index} value={option}>{option}</option>
                      ))}
                    </Select>
                  </Box>
                )}

                {options.length > 0 && !selectedOption && (
                  <Text 
                    color="red.500" 
                    fontSize={{ base: 'xs', md: 'sm' }} 
                    textAlign="center"
                  >
                    Selecteer eerst een optie
                  </Text>
                )}
                
                <HStack spacing={2}>
                  <Button
                    variant="outline"
                    colorScheme="gray"
                    leftIcon={<ArrowBackIcon />}
                    onClick={onClose}
                    size={{ base: 'md', md: 'lg' }}
                    display={{ base: 'flex', md: 'none' }}
                  >
                    Terug
                  </Button>
                  <Button
                    bg="orange.500"
                    color="white"
                    _hover={{ bg: "orange.500", opacity: 0.8 }}
                    onClick={handleAddToCart}
                    isDisabled={!canAddToCart}
                    flex={1}
                    leftIcon={<AddIcon />}
                    size={{ base: 'md', md: 'lg' }}
                    fontSize={{ base: 'sm', md: 'md' }}
                  >
                    <Text display={{ base: 'none', sm: 'block' }}>Toevoegen aan winkelwagen</Text>
                    <Text display={{ base: 'block', sm: 'none' }}>Toevoegen</Text>
                  </Button>
                </HStack>
              </VStack>
            </CardBody>
          </Card>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default ProductCard;