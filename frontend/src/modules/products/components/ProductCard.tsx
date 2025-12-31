import { Box, Button, Image, VStack, Input, HStack, Text, InputGroup, InputLeftAddon, FormControl, FormErrorMessage, IconButton, Collapse, useDisclosure, Checkbox } from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon, ChevronDownIcon, ChevronRightIcon as ChevronRight } from '@chakra-ui/icons';
import { Formik, Form, Field, FormikProps } from 'formik';
import * as Yup from 'yup';
import { uploadToS3 } from '../services/s3Upload';
import { useState, useEffect } from 'react';
import { Product } from '../../../types';

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

const schema = Yup.object().shape({
  id: Yup.string().required('Product ID is verplicht'),
  naam: Yup.string().required('Productnaam is verplicht'),
  groep: Yup.string().required('Productgroep is verplicht'),
  subgroep: Yup.string().when('groep', {
    is: (groep: string) => groep && groep.length > 0,
    then: (schema) => schema.notRequired(), // Subgroep is optional if groep is selected
    otherwise: (schema) => schema.notRequired()
  }),
  prijs: Yup.number().required('Prijs is verplicht').min(0, 'Prijs moet 0 of hoger zijn'),
  opties: Yup.string().test('opties-validation', 'Opties moet leeg zijn of minimaal 2 waarden bevatten gescheiden door komma\'s', function(value) {
    if (!value || value.trim() === '') return true;
    const parts = value.split(',').map(part => part.trim()).filter(part => part.length > 0);
    return parts.length >= 2;
  }),
  images: Yup.array().of(Yup.string()).nullable(),
});

export default function ProductCard({ product, products, onSave, onDelete, onNew, onClose, filteredProducts, onNavigate, readOnly = false }: ProductCardProps) {
  const [uploading, setUploading] = useState<boolean>(false);
  const [categoryStructure, setCategoryStructure] = useState<CategoryStructure>({});
  const [selectedCategory, setSelectedCategory] = useState<{ groep: string; subgroep: string }>({ groep: '', subgroep: '' });

  useEffect(() => {
    // Load product categories from S3 bucket parameters
    const loadCategories = async () => {
      try {
        const s3Url = 'https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/parameters.json';
        const timestamp = new Date().getTime();
        const response = await fetch(`${s3Url}?t=${timestamp}`);
        
        if (response.ok) {
          const parameters = await response.json();
          // Use productgroepen from S3 parameters
          const productGroups = parameters.productgroepen || {};
          setCategoryStructure(productGroups);
        } else {
          // Fallback to empty structure
          setCategoryStructure({});
        }
      } catch (error) {
        console.error('Error loading product categories:', error);
        setCategoryStructure({});
      }
    };
    
    loadCategories();
  }, []);

  useEffect(() => {
    setSelectedCategory({ groep: product.groep || '', subgroep: product.subgroep || '' });
  }, [product]);

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
              }
            }}
            bg={selectedCategory.groep === groupName && !selectedCategory.subgroep ? 'orange.200' : 'transparent'}
            _hover={{ bg: readOnly ? 'transparent' : 'orange.100' }}
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
                      }
                    }}
                    bg={selectedCategory.groep === groupName && selectedCategory.subgroep === subgroup ? 'orange.300' : 'transparent'}
                    _hover={{ bg: readOnly ? 'transparent' : 'orange.200' }}
                    isDisabled={readOnly}
                    fontWeight={selectedCategory.groep === groupName && selectedCategory.subgroep === subgroup ? 'bold' : 'normal'}
                    borderLeft="2px solid"
                    borderColor="orange.200"
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
      <Box p={3} bg="gray.50" borderRadius="md" border="1px solid" borderColor="gray.200" maxH="250px" overflowY="auto">
        <Text fontSize="md" fontWeight="bold" mb={2} color="gray.700">
          {readOnly ? 'Categorie (alleen-lezen):' : 'Selecteer Categorie:'}
        </Text>
        
        {/* Show current selection clearly */}
        {selectedCategory.groep && (
          <Box mb={3} p={2} bg="orange.100" borderRadius="md" border="1px solid" borderColor="orange.300">
            <Text fontSize="sm" fontWeight="bold" color="orange.800">
              Geselecteerd:
            </Text>
            <Text fontSize="sm" color="orange.700">
              📂 <strong>{selectedCategory.groep}</strong>
              {selectedCategory.subgroep && (
                <>
                  <br />
                  📁 <strong>{selectedCategory.subgroep}</strong>
                </>
              )}
            </Text>
          </Box>
        )}
        
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
      <Formik
        initialValues={{
          ...product,
          prijs: product.prijs ? parseFloat(product.prijs.toString()).toFixed(2) : '',
          naam: product.naam || product.name || '',
          images: (() => {
            const productAny = product as any;
            
            if (productAny.images && Array.isArray(productAny.images)) {
              return productAny.images;
            }
            if (productAny.image) {
              const imageArray = Array.isArray(productAny.image) ? productAny.image : [productAny.image];
              return imageArray;
            }
            if (productAny.afbeelding) {
              const afbeeldingArray = Array.isArray(productAny.afbeelding) ? productAny.afbeelding : [productAny.afbeelding];
              return afbeeldingArray;
            }
            if (productAny.foto) {
              const fotoArray = Array.isArray(productAny.foto) ? productAny.foto : [productAny.foto];
              return fotoArray;
            }
            return [];
          })(),
          groep: product.groep || '',
          subgroep: product.subgroep || '',
          opties: product.opties || '',
          nietInWinkel: (product as any).nietInWinkel || false
        }}
        validationSchema={schema}
        onSubmit={(values) => onSave(values)}
      >
        {({ values, setFieldValue, errors, touched }: FormikProps<any>) => (
          <Form>
            <VStack spacing={4}>
              <HStack spacing={4}>
                <FormControl isInvalid={!!(errors.id && touched.id)} flex={1}>
                  <Field name="id" as={Input} placeholder="id" color="black" borderColor={errors.id && touched.id ? 'red.500' : 'gray.200'} id="product-id" isDisabled={readOnly} />
                  <FormErrorMessage>{errors.id as string}</FormErrorMessage>
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
                          color="black" 
                          fontWeight="bold"
                          borderColor={errors.prijs && touched.prijs ? 'red.500' : 'gray.200'}
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
              <FormControl isInvalid={!!(errors.naam && touched.naam)}>
                <Field name="naam" as={Input} placeholder="Naam" color="black" borderColor={errors.naam && touched.naam ? 'red.500' : 'gray.200'} id="product-naam" isDisabled={readOnly} />
                <FormErrorMessage>{errors.naam as string}</FormErrorMessage>
              </FormControl>
              <FormControl isInvalid={!!((errors.groep && touched.groep) || (errors.subgroep && touched.subgroep))}>
                <Field name="groep">
                  {({ form }: any) => (
                    <CategorySelector setFieldValue={form.setFieldValue} />
                  )}
                </Field>
                <FormErrorMessage>{(errors.groep || errors.subgroep) as string}</FormErrorMessage>
              </FormControl>
              <FormControl isInvalid={!!(errors.opties && touched.opties)}>
                <Field name="opties" as={Input} placeholder="Opties (gescheiden door komma's)" color="black" borderColor={errors.opties && touched.opties ? 'red.500' : 'gray.200'} isDisabled={readOnly} />
                <FormErrorMessage>{errors.opties as string}</FormErrorMessage>
              </FormControl>
              <FormControl>
                <Field name="nietInWinkel">
                  {({ field, form }: any) => (
                    <Checkbox
                      {...field}
                      isChecked={field.value}
                      onChange={(e) => form.setFieldValue('nietInWinkel', e.target.checked)}
                      colorScheme="orange"
                      isDisabled={readOnly}
                    >
                      Staat er niet op in de winkel
                    </Checkbox>
                  )}
                </Field>
              </FormControl>
              <HStack spacing={4} justifyContent="center">
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
                <Button 
                  colorScheme="orange" 
                  size="sm"
                  isDisabled={readOnly}
                  onClick={async () => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = 'image/*';
                    input.multiple = true;
                    input.onchange = async (e: Event) => {
                      const target = e.target as HTMLInputElement;
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
              {uploading && <Text color="blue.500">Uploading...</Text>}

              {values.images && values.images.length > 0 && (
                <Box>
                  <Text fontSize="sm" fontWeight="bold" mb={2}>Afbeeldingen ({values.images.length}):</Text>
                  <VStack spacing={2}>
                    {values.images.map((imageUrl: string, index: number) => (
                      <HStack key={index} spacing={2} width="100%">
                        <Image 
                          src={imageUrl} 
                          boxSize="60px"
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

              <HStack spacing={4}>
                {!readOnly && <Button type="submit" colorScheme="orange">Opslaan</Button>}
                {!readOnly && product.id && (
                  <Button colorScheme="red" onClick={() => onDelete(product.id)}>Verwijder</Button>
                )}
                {!readOnly && <Button onClick={onNew}>Nieuw</Button>}
                <Button colorScheme="gray" onClick={onClose}>
                  {readOnly ? 'Sluiten' : 'Sluiten'}
                </Button>
                {readOnly && (
                  <Text fontSize="sm" color="gray.600" fontStyle="italic">
                    Alleen-lezen modus - geen bewerkingsrechten
                  </Text>
                )}
              </HStack>
            </VStack>
          </Form>
        )}
      </Formik>
    </Box>
  );
}