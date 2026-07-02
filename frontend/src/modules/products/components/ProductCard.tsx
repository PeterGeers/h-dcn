import { Box, Button, VStack, Input, HStack, Text, InputGroup, InputLeftAddon, FormControl, FormErrorMessage, IconButton, Collapse, useDisclosure, Modal, ModalOverlay, ModalContent, ModalHeader, ModalFooter, ModalBody, ModalCloseButton, Badge } from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon as ChevronRight, CloseIcon, AddIcon } from '@chakra-ui/icons';
import { Formik, Form, Field, FormikProps } from 'formik';
import * as Yup from 'yup';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Product } from '../../../types';
import OrderItemFieldsEditor from './OrderItemFieldsEditor';
import PurchaseRulesEditor from './PurchaseRulesEditor';
import { OrderItemField, PurchaseRules } from '../../webshop/types/unifiedProduct.types';
import { getAuthHeadersForGet } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';
import { getRequiredFields, getProductField } from '../../../config/productFields';
import { getValidationMessage } from '../../../utils/validationMessages';
import { VariantSubTable } from '../../webshop-management/components/VariantSubTable';
import { AdminVariant, AdminProduct } from '../../webshop-management/types/admin.types';
import { VariantEditModal } from './VariantEditModal';
import { canHaveVariants } from '../../../utils/productHelpers';
import { ProductImageSection } from './ProductImageSection';
import { ProductCardActions } from './ProductCardActions';
import { CategoryDisplay, CategorySelector, CategoryStructure } from './CategorySelector';

/**
 * CollapsibleSection renders a titled, expandable/collapsible box
 * used to wrap the new product configuration editors.
 */
function CollapsibleSection({ title, defaultOpen = false, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: defaultOpen });
  return (
    <Box w="100%" borderWidth="1px" borderColor="gray.400" borderRadius="md" overflow="hidden">
      <Button
        w="100%"
        variant="ghost"
        justifyContent="space-between"
        onClick={onToggle}
        size="sm"
        rightIcon={isOpen ? <ChevronDownIcon /> : <ChevronRight />}
        bg="gray.700"
        color="white"
        _hover={{ bg: 'gray.600' }}
        borderRadius="0"
      >
        {title}
      </Button>
      <Collapse in={isOpen}>
        <Box p={3} bg="gray.800">
          {children}
        </Box>
      </Collapse>
    </Box>
  );
}

interface ProductCardProps {
  product: Product;
  products: Product[];
  onSave: (values: Product) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  onCopy?: (product: Product) => void;
  onClose: () => void;
  filteredProducts: Product[];
  readOnly?: boolean;
  onDeactivate?: (product: Product) => void;
  onActivate?: (product: Product) => void;
  onHardDelete?: (product: Product) => void;
}

// Required fields for parent products — computed once outside the component.
const requiredParentFields = getRequiredFields('parent');

export default function ProductCard({ product, products, onSave, onDelete, onNew, onCopy, onClose, filteredProducts, readOnly = false, onDeactivate, onActivate, onHardDelete }: ProductCardProps) {
  const { t } = useTranslation('products');

  // Validation schema derived from the productFields registry.
  // Built inside the component so the `t` function is available for i18n messages.
  const schema = useMemo(() => {
    const schemaShape: Record<string, any> = {};
    for (const key of requiredParentFields) {
      const fieldDef = getProductField(key);
      if (!fieldDef || fieldDef.inputType === 'hidden') continue; // skip auto-generated fields
      const label = fieldDef.label || key;
      schemaShape[key] = Yup.mixed().required(() => getValidationMessage(t, 'required', { field: label }));
    }
    return Yup.object().shape(schemaShape);
  }, [t]);
  const [categoryStructure, setCategoryStructure] = useState<CategoryStructure>({});
  const [selectedCategory, setSelectedCategory] = useState<{ groep: string; subgroep: string }>({ groep: '', subgroep: '' });
  const { isOpen: isCategoryModalOpen, onOpen: onCategoryModalOpen, onClose: onCategoryModalClose } = useDisclosure();
  const [mainFormSetFieldValue, setMainFormSetFieldValue] = useState<((field: string, value: any) => void) | null>(null);
  const [variants, setVariants] = useState<AdminVariant[]>([]);
  const [isLoadingVariants, setIsLoadingVariants] = useState<boolean>(false);
  const [variantModalOpen, setVariantModalOpen] = useState<boolean>(false);
  const [selectedVariantForEdit, setSelectedVariantForEdit] = useState<AdminVariant | null>(null);

  const fetchVariants = useCallback(async () => {
    const productId = product.product_id || product.id;
    if (!productId) return;
    setIsLoadingVariants(true);
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(`${API_URLS.base}/products/${encodeURIComponent(productId)}/variants`, { headers });
      if (response.ok) {
        const data = await response.json();
        setVariants(data.variants ?? []);
      } else {
        console.error('Error fetching variants:', response.status);
        setVariants([]);
      }
    } catch (err) {
      console.error('Error fetching variants:', err);
    } finally {
      setIsLoadingVariants(false);
    }
  }, [product.product_id, product.id]);

  // Fetch variants for parent products (any product that's not explicitly a variant)
  useEffect(() => {
    if (canHaveVariants(product as any)) {
      fetchVariants();
    } else {
      setVariants([]);
    }
  }, [product, fetchVariants]);

  useEffect(() => {
    // Build category structure dynamically from actual product data.
    const derived: CategoryStructure = {};

    products.forEach(p => {
      if (p.groep) {
        if (!derived[p.groep]) {
          derived[p.groep] = { children: {} };
        }
        if (p.subgroep && !derived[p.groep].children![p.subgroep]) {
          derived[p.groep].children![p.subgroep] = { id: p.subgroep, value: p.subgroep };
        }
      }
    });

    setCategoryStructure(derived);
  }, [products]);

  useEffect(() => {
    setSelectedCategory({ groep: product.groep || '', subgroep: product.subgroep || '' });
  }, [product]);

  if (!filteredProducts || filteredProducts.length === 0) {
    return null;
  }

  return (
    <Box
      bg="orange.100"
      p={6}
      borderRadius="md"
      boxShadow="xl"
      border="2px solid orange"
      position="fixed"
      top="50%"
      left="50%"
      transform="translate(-50%, -50%)"
      zIndex={1000}
      maxHeight="80vh"
      overflowY="auto"
      width="400px"
    >
      {/* Close button in top-right corner */}
      <IconButton
        icon={<CloseIcon />}
        size="sm"
        colorScheme="gray"
        variant="ghost"
        position="absolute"
        top={2}
        right={2}
        onClick={onClose}
        aria-label="Sluiten"
        _hover={{ bg: 'gray.200' }}
      />

      <Formik
        initialValues={{
          ...product,
          prijs: product.prijs ? parseFloat(product.prijs.toString()).toFixed(2) : '',
          naam: product.naam || '',
          artikelcode: (product as any).artikelcode || '',
          images: (product as any).images || [],
          groep: product.groep || '',
          subgroep: product.subgroep || '',
          order_item_fields: (product as any).order_item_fields || undefined,
          purchase_rules: (product as any).purchase_rules || undefined,
        }}
        validationSchema={schema}
        onSubmit={(values) => {
          // Remove legacy fields from payload, send only canonical registry fields
          const { opties, nietInWinkel, event_id, event_ids, id, name, price, image, ...cleanValues } = values as any;

          // Coerce numeric validation fields in order_item_fields to integers
          if (cleanValues.order_item_fields) {
            cleanValues.order_item_fields = cleanValues.order_item_fields.map((field: any) => {
              if (field.validation) {
                const numericKeys = ['min_length', 'max_length', 'minimum', 'maximum'];
                numericKeys.forEach(key => {
                  if (field.validation[key] !== undefined && field.validation[key] !== '') {
                    const parsed = parseInt(field.validation[key], 10);
                    if (!isNaN(parsed)) {
                      field.validation[key] = parsed;
                    }
                  } else if (field.validation[key] === '') {
                    delete field.validation[key];
                  }
                });
              }
              return field;
            });
          }

          // Coerce numeric fields in purchase_rules to integers
          if (cleanValues.purchase_rules) {
            const purchaseNumericKeys = ['max_per_order', 'max_per_member', 'max_per_club', 'min_per_club'];
            purchaseNumericKeys.forEach(key => {
              if (cleanValues.purchase_rules[key] !== undefined && cleanValues.purchase_rules[key] !== '') {
                const parsed = parseInt(cleanValues.purchase_rules[key], 10);
                if (!isNaN(parsed)) {
                  cleanValues.purchase_rules[key] = parsed;
                }
              } else if (cleanValues.purchase_rules[key] === '') {
                delete cleanValues.purchase_rules[key];
              }
            });
          }

          onSave(cleanValues);
        }}
      >
        {({ values, setFieldValue, errors, touched, isSubmitting, submitCount }: FormikProps<any>) => {
          // Store the setFieldValue function for use in the modal
          if (!mainFormSetFieldValue) {
            setMainFormSetFieldValue(() => setFieldValue);
          }

          // Show errors after at least one submit attempt
          const hasErrors = submitCount > 0 && Object.keys(errors).length > 0;

          return (
          <Form>
            <VStack spacing={4}>
              {/* Validation error banner — shows all errors clearly */}
              {hasErrors && (
                <Box bg="red.100" border="1px solid" borderColor="red.400" borderRadius="md" p={3} w="100%">
                  <Text color="red.700" fontWeight="bold" fontSize="sm">
                    Kan niet opslaan:
                  </Text>
                  {Object.values(errors).map((err, i) => (
                    <Text key={i} color="red.600" fontSize="sm">• {err as string}</Text>
                  ))}
                </Box>
              )}

              {/* Name field at the top */}
              <FormControl isInvalid={!!(errors.naam && (touched.naam || submitCount > 0))}>
                <Field name="naam" as={Input} placeholder="Naam" color="white" bg="gray.600" borderColor={errors.naam && (touched.naam || submitCount > 0) ? 'red.500' : 'gray.500'} id="product-naam" isDisabled={readOnly} _placeholder={{ color: 'gray.300' }} />
                <FormErrorMessage>{errors.naam as string}</FormErrorMessage>
              </FormControl>

              {/* ID and Price */}
              <HStack spacing={4} width="100%">
                <FormControl isInvalid={!!(errors.artikelcode && touched.artikelcode)} flex={1}>
                  <Field name="artikelcode" as={Input} placeholder="Artikel code (bijv. G5)" color="white" bg="gray.600" borderColor={errors.artikelcode && touched.artikelcode ? 'red.500' : 'gray.500'} id="product-artikelcode" isDisabled={readOnly} _placeholder={{ color: 'gray.300' }} />
                  <FormErrorMessage>{errors.artikelcode as string}</FormErrorMessage>
                </FormControl>
                <FormControl isInvalid={!!(errors.prijs && touched.prijs)} flex={1}>
                  <Field name="prijs">
                    {({ field, form }: any) => (
                      <InputGroup>
                        <InputLeftAddon bg="orange.300" color="black" fontWeight="bold">€</InputLeftAddon>
                        <Input
                          {...field}
                          placeholder="0.00"
                          type="number"
                          step="0.01"
                          color="white"
                          bg="gray.600"
                          fontWeight="bold"
                          borderColor={errors.prijs && touched.prijs ? 'red.500' : 'gray.500'}
                          _placeholder={{ color: 'gray.300' }}
                          isDisabled={readOnly}
                          onChange={(e) => {
                            const value = e.target.value;
                            form.setFieldValue('prijs', value);
                          }}
                          onBlur={(e) => {
                            const value = parseFloat(e.target.value);
                            if (!isNaN(value)) {
                              form.setFieldValue('prijs', value.toFixed(2));
                            }
                          }}
                        />
                      </InputGroup>
                    )}
                  </Field>
                  <FormErrorMessage>{errors.prijs as string}</FormErrorMessage>
                </FormControl>
              </HStack>

              {/* Category field */}
              <FormControl isInvalid={!!((errors.groep && touched.groep) || (errors.subgroep && touched.subgroep))}>
                <CategoryDisplay
                  groep={values.groep || ''}
                  subgroep={values.subgroep || ''}
                  onClick={onCategoryModalOpen}
                  readOnly={readOnly}
                />
                <FormErrorMessage>{(errors.groep || errors.subgroep) as string}</FormErrorMessage>
              </FormControl>

              {/* Legacy required_attributes display */}
              {(product as any).required_attributes && !values.order_item_fields && !values.purchase_rules && (
                <Box w="100%" p={3} bg="yellow.50" borderRadius="md" border="1px solid" borderColor="yellow.300">
                  <HStack mb={2}>
                    <Text fontSize="sm" fontWeight="bold" color="yellow.800">
                      Legacy veldconfiguratie
                    </Text>
                    <Badge colorScheme="yellow" fontSize="xs">Migratie vereist</Badge>
                  </HStack>
                  <Box
                    p={2}
                    bg="gray.50"
                    borderRadius="sm"
                    fontSize="xs"
                    color="gray.600"
                    maxH="100px"
                    overflowY="auto"
                    fontFamily="mono"
                  >
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                      {JSON.stringify((product as any).required_attributes, null, 2)}
                    </pre>
                  </Box>
                </Box>
              )}

              {/* Variant Sub-Table — collapsible for parent products */}
              {canHaveVariants(product as any) && (
                <CollapsibleSection title={`Varianten (${variants.length})`} defaultOpen={false}>
                  {!readOnly && (
                    <Button
                      size="xs"
                      colorScheme="orange"
                      leftIcon={<AddIcon />}
                      mb={2}
                      onClick={() => {
                        setSelectedVariantForEdit(null);
                        setVariantModalOpen(true);
                      }}
                    >
                      Variant toevoegen
                    </Button>
                  )}
                  <VariantSubTable
                    product={{
                      product_id: product.product_id || product.id,
                      name: values.naam || product.naam || '',
                      price: parseFloat(values.prijs) || 0,
                      active: true,
                      is_parent: true,
                      variants: variants,
                    } as AdminProduct}
                    variants={variants}
                    onUpdate={fetchVariants}
                    isRefetching={isLoadingVariants}
                    onRowClick={(variant) => {
                      setSelectedVariantForEdit(variant);
                      setVariantModalOpen(true);
                    }}
                  />
                </CollapsibleSection>
              )}

              {/* Order Item Fields Editor - collapsible */}
              {!readOnly && (
                <CollapsibleSection title="Bestelvelden per item" defaultOpen={false}>
                  <OrderItemFieldsEditor
                    value={values.order_item_fields || []}
                    onChange={(fields: OrderItemField[]) => setFieldValue('order_item_fields', fields)}
                  />
                </CollapsibleSection>
              )}

              {/* Purchase Rules Editor - collapsible */}
              {!readOnly && (
                <CollapsibleSection title="Aankoopregels" defaultOpen={false}>
                  <PurchaseRulesEditor
                    value={values.purchase_rules || {}}
                    onChange={(rules: PurchaseRules) => {
                      const hasValues = Object.values(rules).some(v => v != null && v !== false);
                      setFieldValue('purchase_rules', hasValues ? rules : undefined);
                    }}
                  />
                </CollapsibleSection>
              )}

              {/* Images CollapsibleSection */}
              <CollapsibleSection title="Afbeeldingen" defaultOpen={false}>
                <ProductImageSection
                  images={values.images || []}
                  productId={product.id}
                  readOnly={readOnly}
                  setFieldValue={setFieldValue}
                />
              </CollapsibleSection>

              {/* Action buttons */}
              <ProductCardActions
                product={product}
                readOnly={readOnly}
                onDelete={onDelete}
                onNew={onNew}
                onCopy={onCopy}
                onDeactivate={onDeactivate}
                onActivate={onActivate}
                onHardDelete={onHardDelete}
              />
            </VStack>
          </Form>
          );
        }}
      </Formik>

      {/* Category Selection Modal */}
      <Modal isOpen={isCategoryModalOpen} onClose={onCategoryModalClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Selecteer Categorie</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {mainFormSetFieldValue && (
              <CategorySelector
                setFieldValue={mainFormSetFieldValue}
                categoryStructure={categoryStructure}
                selectedCategory={selectedCategory}
                setSelectedCategory={setSelectedCategory}
                readOnly={readOnly}
                onCategoryModalClose={onCategoryModalClose}
              />
            )}
          </ModalBody>
          <ModalFooter>
            <Button colorScheme="gray" onClick={onCategoryModalClose}>
              Sluiten
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Variant Edit Modal — opens when clicking a variant value tag */}
      <VariantEditModal
        isOpen={variantModalOpen}
        onClose={() => setVariantModalOpen(false)}
        productId={product.product_id || product.id || ''}
        variant={selectedVariantForEdit}
        existingVariants={variants}
        onSuccess={fetchVariants}
        parentPrice={parseFloat((product as any).prijs) || 0}
      />
    </Box>
  );
}
