import { Box, Button, Image, VStack, Input, HStack, Text, InputGroup, InputLeftAddon, FormControl, FormErrorMessage, IconButton, Collapse, useDisclosure, Checkbox, Modal, ModalOverlay, ModalContent, ModalHeader, ModalFooter, ModalBody, ModalCloseButton, Badge } from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon, ChevronDownIcon, ChevronRightIcon as ChevronRight, CloseIcon, DeleteIcon, CheckIcon, AddIcon } from '@chakra-ui/icons';
import { Formik, Form, Field, FormikProps } from 'formik';
import * as Yup from 'yup';
import { uploadToS3 } from '../services/s3Upload';
import { useState, useEffect, useCallback } from 'react';
import { Product, Event as HDCNEvent } from '../../../types';
import VariantSchemaEditor from './VariantSchemaEditor';
import OrderItemFieldsEditor from './OrderItemFieldsEditor';
import PurchaseRulesEditor from './PurchaseRulesEditor';
import { VariantSchema, OrderItemField, PurchaseRules } from '../../webshop/types/unifiedProduct.types';
import { getAuthHeadersForGet } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';
import { updateVariantSchema, addVariantToProduct } from '../api/productApi';
import { getRequiredFields, getProductField } from '../../../config/productFields';
import { VariantSubTable } from '../../webshop-management/components/VariantSubTable';
import { AdminVariant, AdminProduct } from '../../webshop-management/types/admin.types';
import { getAdminProducts, deleteVariant } from '../../webshop-management/services/adminApi';

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
  onClose: () => void;
  filteredProducts: Product[];
  onNavigate: (product: Product) => void;
  readOnly?: boolean; // Add read-only mode support
}

interface CategoryStructure {
  [key: string]: {
    children?: {
      [key: string]: any;
    };
  };
}

interface CategorySelectorProps {
  setFieldValue: (field: string, value: any) => void;
}

interface GroupItemProps {
  groupName: string;
  groupData: {
    children?: {
      [key: string]: any;
    };
  };
}

// Validation schema derived from the productFields registry.
// Required fields for parent products are checked; all else is optional.
const requiredParentFields = getRequiredFields('parent');
const schemaShape: Record<string, any> = {};
for (const key of requiredParentFields) {
  const fieldDef = getProductField(key);
  if (!fieldDef || fieldDef.inputType === 'hidden') continue; // skip auto-generated fields
  const label = fieldDef.label || key;
  schemaShape[key] = Yup.mixed().required(`${label} is verplicht`);
}
const schema = Yup.object().shape(schemaShape);

export default function ProductCard({ product, products, onSave, onDelete, onNew, onClose, filteredProducts, onNavigate, readOnly = false }: ProductCardProps) {
  const [uploading, setUploading] = useState<boolean>(false);
  const [categoryStructure, setCategoryStructure] = useState<CategoryStructure>({});
  const [selectedCategory, setSelectedCategory] = useState<{ groep: string; subgroep: string }>({ groep: '', subgroep: '' });
  const { isOpen: isCategoryModalOpen, onOpen: onCategoryModalOpen, onClose: onCategoryModalClose } = useDisclosure();
  const [mainFormSetFieldValue, setMainFormSetFieldValue] = useState<((field: string, value: any) => void) | null>(null);
  const [events, setEvents] = useState<HDCNEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState<boolean>(false);
  const [variantSchemaHasErrors, setVariantSchemaHasErrors] = useState<boolean>(false);
  const [variants, setVariants] = useState<AdminVariant[]>([]);
  const [isLoadingVariants, setIsLoadingVariants] = useState<boolean>(false);

  const fetchVariants = useCallback(async () => {
    const productId = product.product_id || product.id;
    if (!productId) return;
    setIsLoadingVariants(true);
    try {
      const adminProducts = await getAdminProducts();
      const matched = adminProducts.find((p: AdminProduct) => p.product_id === productId);
      setVariants(matched?.variants ?? []);
    } catch (err) {
      console.error('Error fetching variants:', err);
    } finally {
      setIsLoadingVariants(false);
    }
  }, [product.product_id, product.id]);

  // Fetch variants when product has a non-empty variant_schema
  useEffect(() => {
    const schema = (product as any).variant_schema;
    const hasVariantValues = schema && Object.values(schema).some((vals: any) => Array.isArray(vals) && vals.length > 0);
    if (hasVariantValues) {
      fetchVariants();
    } else {
      setVariants([]);
    }
  }, [product, fetchVariants]);

  useEffect(() => {
    // Build category structure dynamically from actual product data.
    // Categories appear once at least one product uses them.
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

  // Fetch events for the event_id selector
  useEffect(() => {
    const fetchEvents = async () => {
      setEventsLoading(true);
      try {
        const headers = await getAuthHeadersForGet();
        const response = await fetch(API_URLS.events(), { headers });
        if (response.ok) {
          const data = await response.json();
          setEvents(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error('Error fetching events:', err);
      } finally {
        setEventsLoading(false);
      }
    };
    fetchEvents();
  }, []);

  const CategoryDisplay = ({ groep, subgroep, onClick }: { groep: string; subgroep: string; onClick: () => void }) => {
    const displayText = groep && subgroep 
      ? `${groep} - ${subgroep}`
      : groep 
        ? groep
        : 'Selecteer categorie...';
    
    return (
      <Box
        height="40px"
        px={4}
        py={2}
        bg="gray.600"
        borderRadius="md"
        border="1px solid"
        borderColor="gray.500"
        cursor={readOnly ? 'default' : 'pointer'}
        onClick={readOnly ? undefined : onClick}
        _hover={readOnly ? {} : { borderColor: 'gray.400' }}
        display="flex"
        alignItems="center"
        fontSize="md"
        width="50%"
        _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 1px #3182ce' }}
      >
        <Text color={groep ? 'white' : 'gray.300'}>
          {displayText}
        </Text>
      </Box>
    );
  };

  const CategorySelector = ({ setFieldValue }: CategorySelectorProps) => {
    const GroupItem = ({ groupName, groupData }: GroupItemProps) => {
      const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: selectedCategory.groep === groupName });
      const hasChildren = groupData.children && Object.keys(groupData.children).length > 0;
      
      return (
        <Box>
          <Button
            variant="ghost"
            justifyContent="flex-start"
            width="full"
            size="sm"
            fontSize="md"
            py={2}
            leftIcon={hasChildren ? (isOpen ? <ChevronDownIcon /> : <ChevronRight />) : undefined}
            onClick={() => {
              if (hasChildren) {
                onToggle();
              } else if (!readOnly) {
                // If no children, select this as both groep and subgroep
                setSelectedCategory({ groep: groupName, subgroep: '' });
                setFieldValue('groep', groupName);
                setFieldValue('subgroep', '');
                onCategoryModalClose(); // Close modal after selection
              }
            }}
            color="white"
            bg={selectedCategory.groep === groupName && !selectedCategory.subgroep ? 'orange.600' : 'transparent'}
            _hover={{ bg: readOnly ? 'transparent' : 'gray.700' }}
            isDisabled={readOnly}
            fontWeight={selectedCategory.groep === groupName ? 'bold' : 'normal'}
          >
            {groupName}
            {!hasChildren && <Text fontSize="xs" color="gray.500" ml={2}>(geen subgroepen)</Text>}
          </Button>
          
          {hasChildren && (
            <Collapse in={isOpen}>
              <VStack align="stretch" pl={6} spacing={1} mt={1}>
                {Object.entries(groupData.children).map(([subgroup, subgroupData]) => (
                  <Button
                    key={subgroup}
                    variant="ghost"
                    size="sm"
                    fontSize="sm"
                    py={2}
                    justifyContent="flex-start"
                    onClick={() => {
                      if (!readOnly) {
                        setSelectedCategory({ groep: groupName, subgroep: subgroup });
                        setFieldValue('groep', groupName);
                        setFieldValue('subgroep', subgroup);
                        onCategoryModalClose(); // Close modal after selection
                      }
                    }}
                    color="white"
                    bg={selectedCategory.groep === groupName && selectedCategory.subgroep === subgroup ? 'orange.700' : 'transparent'}
                    _hover={{ bg: readOnly ? 'transparent' : 'gray.700' }}
                    isDisabled={readOnly}
                    fontWeight={selectedCategory.groep === groupName && selectedCategory.subgroep === subgroup ? 'bold' : 'normal'}
                    borderLeft="2px solid"
                    borderColor="orange.400"
                    borderRadius="0"
                    ml={2}
                  >
                    📁 {subgroup}
                  </Button>
                ))}
              </VStack>
            </Collapse>
          )}
        </Box>
      );
    };

    return (
      <Box p={3} bg="gray.800" borderRadius="md" border="1px solid" borderColor="gray.600" maxH="400px" overflowY="auto">
        <Text fontSize="md" fontWeight="bold" mb={3} color="white">
          {readOnly ? 'Categorie (alleen-lezen):' : 'Selecteer Categorie:'}
        </Text>
        
        <VStack align="stretch" spacing={1}>
          {Object.keys(categoryStructure).length === 0 ? (
            <Text fontSize="sm" color="gray.500" textAlign="center" py={4}>
              Geen categorieën beschikbaar
            </Text>
          ) : (
            Object.entries(categoryStructure).map(([groupName, groupData]) => (
              <GroupItem key={groupName} groupName={groupName} groupData={groupData} />
            ))
          )}
        </VStack>

        {/* New group/subgroup inputs */}
        {!readOnly && (
          <Box mt={4} pt={3} borderTop="1px solid" borderColor="gray.300">
            <Text fontSize="sm" fontWeight="bold" color="gray.200" mb={2}>Nieuwe categorie toevoegen:</Text>
            <HStack spacing={2} mb={2}>
              <Input
                size="sm"
                placeholder="Nieuwe groep"
                bg="gray.600"
                color="white"
                borderColor="gray.500"
                _placeholder={{ color: 'gray.300' }}
                id="new-group-input"
                onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter') {
                    const val = (e.target as HTMLInputElement).value.trim();
                    if (val) {
                      setSelectedCategory({ groep: val, subgroep: '' });
                      setFieldValue('groep', val);
                      setFieldValue('subgroep', '');
                      onCategoryModalClose();
                    }
                  }
                }}
              />
              <Button size="sm" colorScheme="orange" onClick={() => {
                const input = document.getElementById('new-group-input') as HTMLInputElement;
                const val = input?.value?.trim();
                if (val) {
                  setSelectedCategory({ groep: val, subgroep: '' });
                  setFieldValue('groep', val);
                  setFieldValue('subgroep', '');
                  onCategoryModalClose();
                }
              }}>+</Button>
            </HStack>
            <HStack spacing={2}>
              <Input
                size="sm"
                placeholder="Nieuwe subgroep"
                bg="gray.600"
                color="white"
                borderColor="gray.500"
                _placeholder={{ color: 'gray.300' }}
                id="new-subgroup-input"
                isDisabled={!selectedCategory.groep}
                onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter' && selectedCategory.groep) {
                    const val = (e.target as HTMLInputElement).value.trim();
                    if (val) {
                      setSelectedCategory({ groep: selectedCategory.groep, subgroep: val });
                      setFieldValue('groep', selectedCategory.groep);
                      setFieldValue('subgroep', val);
                      onCategoryModalClose();
                    }
                  }
                }}
              />
              <Button size="sm" colorScheme="orange" isDisabled={!selectedCategory.groep} onClick={() => {
                const input = document.getElementById('new-subgroup-input') as HTMLInputElement;
                const val = input?.value?.trim();
                if (val && selectedCategory.groep) {
                  setSelectedCategory({ groep: selectedCategory.groep, subgroep: val });
                  setFieldValue('groep', selectedCategory.groep);
                  setFieldValue('subgroep', val);
                  onCategoryModalClose();
                }
              }}>+</Button>
            </HStack>
            <Text fontSize="xs" color="gray.500" mt={1}>Typ een naam en druk Enter of klik +</Text>
          </Box>
        )}
      </Box>
    );
  };

  if (!filteredProducts || filteredProducts.length === 0) {
    return null;
  }
  
  const currentIndex = filteredProducts.findIndex(p => p.id === product.id);
  const canGoPrevious = currentIndex > 0;
  const canGoNext = currentIndex < filteredProducts.length - 1;
  
  const handlePrevious = () => {
    if (canGoPrevious && filteredProducts[currentIndex - 1]) {
      onNavigate(filteredProducts[currentIndex - 1]);
    }
  };
  
  const handleNext = () => {
    if (canGoNext && filteredProducts[currentIndex + 1]) {
      onNavigate(filteredProducts[currentIndex + 1]);
    }
  };

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
          event_ids: (product as any).event_ids || [],
          variant_schema: (product as any).variant_schema || undefined,
          order_item_fields: (product as any).order_item_fields || undefined,
          purchase_rules: (product as any).purchase_rules || undefined,
        }}
        validationSchema={schema}
        onSubmit={(values) => {
          if (variantSchemaHasErrors) return;
          // Remove legacy fields from payload, send only canonical registry fields
          const { opties, nietInWinkel, event_id, id, name, price, image, ...cleanValues } = values as any;

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

              {/* ID and Price with navigation buttons */}
              <HStack spacing={4} width="100%">
                {filteredProducts.length > 1 && (
                  <IconButton
                    icon={<ChevronLeftIcon />}
                    colorScheme="orange"
                    isDisabled={!canGoPrevious}
                    onClick={handlePrevious}
                    aria-label="Vorige product"
                    size="sm"
                  />
                )}
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
                {filteredProducts.length > 1 && (
                  <IconButton
                    icon={<ChevronRightIcon />}
                    colorScheme="orange"
                    isDisabled={!canGoNext}
                    onClick={handleNext}
                    aria-label="Volgende product"
                    size="sm"
                  />
                )}
              </HStack>

              {/* Category field */}
              <FormControl isInvalid={!!((errors.groep && touched.groep) || (errors.subgroep && touched.subgroep))}>
                <CategoryDisplay 
                  groep={values.groep || ''} 
                  subgroep={values.subgroep || ''} 
                  onClick={onCategoryModalOpen}
                />
                <FormErrorMessage>{(errors.groep || errors.subgroep) as string}</FormErrorMessage>
              </FormControl>

              {/* Event_ids multiselect — per webshop-as-event.md */}
              <FormControl>
                <Text fontSize="xs" fontWeight="bold" color="gray.700" mb={1}>
                  Zichtbaar in:
                </Text>
                <VStack align="stretch" spacing={1}>
                  {[{ id: 'evt-webshop', label: 'Webshop (algemeen)' }, ...events.map(e => ({ id: e.event_id, label: e.title || e.naam || e.event_id }))].map((evt) => (
                    <Checkbox
                      key={evt.id}
                      isChecked={(values.event_ids || []).includes(evt.id)}
                      onChange={(e) => {
                        const current: string[] = values.event_ids || [];
                        if (e.target.checked) {
                          setFieldValue('event_ids', [...current, evt.id]);
                        } else {
                          setFieldValue('event_ids', current.filter((id: string) => id !== evt.id));
                        }
                      }}
                      colorScheme="orange"
                      size="sm"
                      isDisabled={readOnly}
                    >
                      <Text fontSize="sm" color="gray.800">{evt.label}</Text>
                    </Checkbox>
                  ))}
                </VStack>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {eventsLoading ? 'Events laden...' : `Selecteer waar dit product zichtbaar is (${events.length} events)`}
                </Text>
              </FormControl>

              {/* Legacy required_attributes display */}
              {(product as any).required_attributes && !values.variant_schema && !values.order_item_fields && !values.purchase_rules && (
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

              {/* Variant Schema Editor - collapsible */}
              <CollapsibleSection title="Variant Schema" defaultOpen={!!values.variant_schema && Object.keys(values.variant_schema).length > 0}>
                <VariantSchemaEditor
                  value={values.variant_schema || {}}
                  onChange={(schema: VariantSchema) => {
                    setFieldValue('variant_schema', Object.keys(schema).length > 0 ? schema : undefined);
                    // Validate variant schema errors
                    const axes = Object.entries(schema);
                    let hasErrors = false;
                    if (axes.length > 0) {
                      const totalCombinations = axes.reduce((product, [, vals]) => product * (vals.length || 1), 1);
                      if (totalCombinations > 100) hasErrors = true;
                      const axisNames = axes.map(([name]) => name.trim().toLowerCase());
                      axes.forEach(([name, vals], index) => {
                        if (!name.trim()) hasErrors = true;
                        const dupIdx = axisNames.indexOf(name.trim().toLowerCase());
                        if (dupIdx !== -1 && dupIdx !== index) hasErrors = true;
                        const trimmedValues = vals.map((v) => v.trim().toLowerCase());
                        vals.forEach((val, vIndex) => {
                          if (!val.trim()) hasErrors = true;
                          const dupVIdx = trimmedValues.indexOf(val.trim().toLowerCase());
                          if (dupVIdx !== -1 && dupVIdx !== vIndex) hasErrors = true;
                        });
                      });
                    }
                    setVariantSchemaHasErrors(hasErrors);
                  }}
                  productId={product.product_id || product.id}
                  onSyncSchema={async (schema: VariantSchema) => {
                    const productId = product.product_id || product.id;
                    if (!productId) return;
                    await updateVariantSchema(productId, schema);
                  }}
                  onAddVariant={async (variantAttributes: Record<string, string>) => {
                    const productId = product.product_id || product.id;
                    if (!productId) return;
                    await addVariantToProduct(productId, variantAttributes);
                  }}
                  onRemoveVariant={async (variantAttributes: Record<string, string>) => {
                    const productId = product.product_id || product.id;
                    if (!productId) return;
                    // Resolve variant_attributes → variant_id using fetched variants list
                    const matchedVariant = variants.find((v) => {
                      const attrs = v.variant_attributes;
                      if (!attrs) return false;
                      const keys = Object.keys(variantAttributes);
                      return keys.length === Object.keys(attrs).length &&
                        keys.every((k) => attrs[k] === variantAttributes[k]);
                    });
                    if (!matchedVariant) {
                      throw new Error('Variant niet gevonden voor de geselecteerde attributen');
                    }
                    await deleteVariant(productId, matchedVariant.product_id);
                    // Refresh variants after deletion
                    await fetchVariants();
                  }}
                />
                {variantSchemaHasErrors && (
                  <Text fontSize="xs" color="red.500" mt={1}>
                    Los variant schema fouten op voordat u opslaat
                  </Text>
                )}
              </CollapsibleSection>

              {/* Variant Sub-Table — renders when variant_schema has at least one axis with values */}
              {values.variant_schema && Object.values(values.variant_schema as Record<string, string[]>).some((vals) => vals.length > 0) && (
                <CollapsibleSection title="Varianten" defaultOpen={true}>
                  <VariantSubTable
                    product={{
                      product_id: product.product_id || product.id,
                      name: values.naam || product.naam || '',
                      price: parseFloat(values.prijs) || 0,
                      active: true,
                      is_parent: true,
                      variant_schema: values.variant_schema,
                      variants: variants,
                    } as AdminProduct}
                    variants={variants}
                    onUpdate={fetchVariants}
                    isRefetching={isLoadingVariants}
                  />
                </CollapsibleSection>
              )}

              {/* Order Item Fields Editor - collapsible */}
              {!readOnly && (
                <CollapsibleSection title="Bestelvelden per item" defaultOpen={!!values.order_item_fields && values.order_item_fields.length > 0}>
                  <OrderItemFieldsEditor
                    value={values.order_item_fields || []}
                    onChange={(fields: OrderItemField[]) => setFieldValue('order_item_fields', fields.length > 0 ? fields : undefined)}
                  />
                </CollapsibleSection>
              )}

              {/* Purchase Rules Editor - collapsible */}
              {!readOnly && (
                <CollapsibleSection title="Aankoopregels" defaultOpen={!!values.purchase_rules && Object.values(values.purchase_rules).some(v => v != null)}>
                  <PurchaseRulesEditor
                    value={values.purchase_rules || {}}
                    onChange={(rules: PurchaseRules) => {
                      const hasValues = Object.values(rules).some(v => v != null && v !== false);
                      setFieldValue('purchase_rules', hasValues ? rules : undefined);
                    }}
                  />
                </CollapsibleSection>
              )}

              {/* Image upload button */}
              <Button 
                colorScheme="orange" 
                size="sm"
                isDisabled={readOnly}
                onClick={async () => {
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
                        const uploadPromises = files.map(file => uploadToS3(file, product.id));
                        const s3Urls = await Promise.all(uploadPromises);
                        const currentImages = values.images || [];
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
                }}
              >
                + Afbeeldingen
              </Button>

              {uploading && <Text color="blue.500">Uploading...</Text>}

              {/* Images section with 30% larger size */}
              {values.images && values.images.length > 0 && (
                <Box>
                  <Text fontSize="sm" fontWeight="bold" mb={2}>Afbeeldingen ({values.images.length}):</Text>
                  <VStack spacing={2}>
                    {values.images.map((imageUrl: string, index: number) => (
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
                            const newImages = values.images.filter((_: string, i: number) => i !== index);
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

              {/* Action buttons */}
              <HStack spacing={4}>
                {!readOnly && (
                  <IconButton
                    icon={<CheckIcon />}
                    colorScheme="orange"
                    size="sm"
                    type="submit"
                    aria-label="Opslaan"
                    isDisabled={variantSchemaHasErrors}
                    _hover={{ bg: 'orange.600' }}
                  />
                )}
                {!readOnly && product.id && (
                  <IconButton
                    icon={<DeleteIcon />}
                    colorScheme="red"
                    size="sm"
                    onClick={() => onDelete(product.id)}
                    aria-label="Verwijder product"
                    _hover={{ bg: 'red.600' }}
                  />
                )}
                {!readOnly && (
                  <IconButton
                    icon={<AddIcon />}
                    colorScheme="green"
                    size="sm"
                    onClick={onNew}
                    aria-label="Nieuw product"
                    _hover={{ bg: 'green.600' }}
                  />
                )}
                {readOnly && (
                  <Text fontSize="sm" color="gray.600" fontStyle="italic">
                    Alleen-lezen modus - geen bewerkingsrechten
                  </Text>
                )}
              </HStack>
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
              <CategorySelector setFieldValue={mainFormSetFieldValue} />
            )}
          </ModalBody>
          <ModalFooter>
            <Button colorScheme="gray" onClick={onCategoryModalClose}>
              Sluiten
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}