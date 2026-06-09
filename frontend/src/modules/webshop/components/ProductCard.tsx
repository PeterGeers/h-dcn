import React, { useState, useEffect, useCallback } from 'react';
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
  IconButton,
  Flex,
  HStack,
  Spinner,
} from '@chakra-ui/react';
import { AddIcon, ChevronLeftIcon, ChevronRightIcon, ArrowBackIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import VariantSelector from './VariantSelector';
import PurchaseRulesFeedback from './PurchaseRulesFeedback';
import { productService } from '../services/api';
import {
  VariantSchema,
  VariantRecord,
  PurchaseRules,
  normalizeVariantSchema,
} from '../types/unifiedProduct.types';

interface Product {
  product_id?: string;
  id?: string;
  name?: string;
  naam?: string;
  prijs?: number | string;
  price?: number;
  images?: string | string[];
  image?: string | string[];
  variant_schema?: VariantSchema;
  purchase_rules?: PurchaseRules;
}

interface CartItem {
  product_id: string;
  variant_id: string;
  variant_attributes: Record<string, string>;
  name?: string;
  naam?: string;
  price?: number;
  quantity: number;
  id?: string;
}

interface ProductCardProps {
  product: Product | null;
  isOpen: boolean;
  onClose: () => void;
  onAddToCart: (cartItem: CartItem) => void;
  /** Quantity already ordered by this member for this product (paid/pending) */
  memberOrderedQuantity?: number;
  /** Quantity already ordered by this member's club for this product (paid/pending) */
  clubOrderedQuantity?: number;
  /** Whether the user has an active membership */
  hasActiveMembership?: boolean;
}

const ProductCard: React.FC<ProductCardProps> = ({
  product,
  isOpen,
  onClose,
  onAddToCart,
  memberOrderedQuantity = 0,
  clubOrderedQuantity = 0,
  hasActiveMembership = true,
}) => {
  const [currentImageIndex, setCurrentImageIndex] = useState<number>(0);
  const [selectedVariant, setSelectedVariant] = useState<VariantRecord | null>(null);
  const [variants, setVariants] = useState<VariantRecord[]>([]);
  const [loadingVariants, setLoadingVariants] = useState<boolean>(false);
  const [variantFetchError, setVariantFetchError] = useState<boolean>(false);
  const [hasPurchaseViolation, setHasPurchaseViolation] = useState<boolean>(false);
  const { t } = useTranslation('products');

  // Fetch variants when product has a variant_schema
  useEffect(() => {
    if (!product || !isOpen) return;

    const productId = product.product_id || product.id || '';

    if (product.variant_schema && Object.keys(product.variant_schema).length > 0) {
      setLoadingVariants(true);
      productService
        .getVariants(productId)
        .then((response: any) => {
          const variantData = Array.isArray(response) ? response : response?.data || [];
          setVariants(variantData);
        })
        .catch((err: Error) => {
          console.error('Failed to fetch variants:', err);
          setVariants([]);
          setVariantFetchError(true);
        })
        .finally(() => {
          setLoadingVariants(false);
        });
    } else {
      // For products without variant_schema, try to load the default variant
      setLoadingVariants(true);
      productService
        .getVariants(productId)
        .then((response: any) => {
          const variantData = Array.isArray(response) ? response : response?.data || [];
          setVariants(variantData);
          // Auto-select default variant (variant with empty variant_attributes)
          const defaultVariant = variantData.find(
            (v: VariantRecord) => Object.keys(v.variant_attributes || {}).length === 0
          );
          if (defaultVariant) {
            setSelectedVariant(defaultVariant);
          }
        })
        .catch(() => {
          setVariants([]);
          setVariantFetchError(true);
        })
        .finally(() => {
          setLoadingVariants(false);
        });
    }

    // Reset state on product change
    setSelectedVariant(null);
    setCurrentImageIndex(0);
    setHasPurchaseViolation(false);
    setVariantFetchError(false);
  }, [product, isOpen]);

  const handleVariantSelect = useCallback((variant: VariantRecord | null) => {
    setSelectedVariant(variant);
  }, []);

  const handlePurchaseViolation = useCallback((hasViolation: boolean) => {
    setHasPurchaseViolation(hasViolation);
  }, []);

  if (!product) return null;

  const hasVariantSchema =
    product.variant_schema && Object.keys(product.variant_schema).length > 0;

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
  images = images
    .map((img) => {
      if (typeof img === 'string') {
        if (img.startsWith('https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com')) {
          return img;
        }
        if (img.startsWith('https://my-hdcn-bucke')) {
          return img.replace(
            'https://my-hdcn-bucke',
            'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com'
          );
        }
      }
      return img;
    })
    .filter((img) => img && typeof img === 'string');

  // Check if selected variant is out of stock
  const isOutOfStock = selectedVariant
    ? !selectedVariant.allow_oversell && selectedVariant.stock <= 0
    : false;

  // Determine if add-to-cart should be enabled
  const canAddToCart = (() => {
    // Disable if variant fetch failed
    if (variantFetchError) return false;
    // For products with variant_schema, a variant must be resolved
    if (hasVariantSchema && !selectedVariant) return false;
    // For products without variant_schema, allow if default variant is loaded or no variants
    if (!hasVariantSchema && variants.length > 0 && !selectedVariant) return false;
    // Cannot add if out of stock
    if (isOutOfStock) return false;
    // Cannot add if purchase rule violated
    if (hasPurchaseViolation) return false;
    return true;
  })();

  const nextImage = (): void => {
    setCurrentImageIndex((prev) => (prev + 1) % images.length);
  };

  const prevImage = (): void => {
    setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  const handleAddToCart = (): void => {
    const cartItem: CartItem = {
      product_id: product.product_id || product.id || '',
      variant_id: selectedVariant?.product_id || '',
      variant_attributes: selectedVariant?.variant_attributes || {},
      name: product.name || product.naam,
      price: Number(product.price ?? product.prijs ?? 0),
      quantity: 1,
    };
    onAddToCart(cartItem);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size={{ base: 'full', md: 'xl' }}>
      <ModalOverlay />
      <ModalContent mx={{ base: 2, md: 'auto' }} my={{ base: 2, md: 'auto' }}>
        <ModalHeader color="black" fontSize={{ base: 'lg', md: 'xl' }} pr={10}>
          {product.name || product.naam}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6} px={{ base: 4, md: 6 }}>
          <Card>
            <CardBody>
              <VStack spacing={{ base: 3, md: 4 }} align="stretch">
                {/* Image carousel - preserved from existing implementation */}
                {images.length > 0 ? (
                  <Box position="relative">
                    <Image
                      src={images[currentImageIndex]}
                      alt={product.name || product.naam}
                      maxH={{ base: '250px', md: '300px' }}
                      w="full"
                      objectFit="contain"
                      mx="auto"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                    {images.length > 1 && (
                      <Flex
                        justify="space-between"
                        position="absolute"
                        top="50%"
                        w="100%"
                        px={2}
                      >
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
                    <Text color="gray.500">{t('card.no_image')}</Text>
                  </Box>
                )}

                {/* Product details - preserved from existing implementation */}
                <VStack align="start" spacing={2}>
                  <Text fontSize={{ base: 'md', md: 'lg' }}>
                    {t('card.price_label')}{' '}
                    <Text as="span" fontWeight="bold" fontSize={{ base: 'lg', md: 'xl' }}>
                      €{(product.price ?? product.prijs) ? Number(product.price ?? product.prijs).toFixed(2) : '0.00'}
                    </Text>
                  </Text>
                  <Text fontSize={{ base: 'sm', md: 'md' }}>
                    <strong>Product:</strong> {product.name || product.naam}
                  </Text>
                </VStack>

                {/* Variant selector - replaces legacy opties dropdown */}
                {hasVariantSchema && (
                  <Box>
                    {loadingVariants ? (
                      <Flex justify="center" py={3}>
                        <Spinner size="sm" />
                        <Text ml={2} fontSize="sm" color="gray.500">
                          Opties laden...
                        </Text>
                      </Flex>
                    ) : variantFetchError ? (
                      <Text color="red.500" fontSize="sm">
                        {t('card.variant_fetch_error')}
                      </Text>
                    ) : (
                      <VariantSelector
                        variantSchema={normalizeVariantSchema(product.variant_schema)!}
                        variants={variants}
                        onVariantSelect={handleVariantSelect}
                      />
                    )}
                  </Box>
                )}

                {/* Variant fetch error for products without variant_schema */}
                {!hasVariantSchema && variantFetchError && (
                  <Text color="red.500" fontSize="sm">
                    {t('card.variant_fetch_error')}
                  </Text>
                )}

                {/* Purchase rules feedback */}
                {product.purchase_rules && (
                  <PurchaseRulesFeedback
                    rules={product.purchase_rules}
                    requestedQuantity={1}
                    memberOrderTotal={memberOrderedQuantity}
                    clubOrderTotal={clubOrderedQuantity}
                    hasMembership={hasActiveMembership}
                    onViolation={handlePurchaseViolation}
                  />
                )}

                {/* Action buttons */}
                <HStack spacing={2}>
                  <Button
                    variant="outline"
                    colorScheme="gray"
                    leftIcon={<ArrowBackIcon />}
                    onClick={onClose}
                    size={{ base: 'md', md: 'lg' }}
                    display={{ base: 'flex', md: 'none' }}
                  >
                    {t('buttons.back', { ns: 'common', defaultValue: 'Terug' })}
                  </Button>
                  <Button
                    bg="orange.500"
                    color="white"
                    _hover={{ bg: 'orange.500', opacity: 0.8 }}
                    onClick={handleAddToCart}
                    isDisabled={!canAddToCart}
                    flex={1}
                    leftIcon={<AddIcon />}
                    size={{ base: 'md', md: 'lg' }}
                    fontSize={{ base: 'sm', md: 'md' }}
                  >
                    <Text display={{ base: 'none', sm: 'block' }}>
                      {t('card.add_to_cart')}
                    </Text>
                    <Text display={{ base: 'block', sm: 'none' }}>
                      {t('card.add_to_cart_short', { defaultValue: 'Toevoegen' })}
                    </Text>
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
