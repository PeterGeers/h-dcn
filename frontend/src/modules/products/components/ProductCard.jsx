import { Box, Button, Image, VStack, Input, HStack, Text, InputGroup, InputLeftAddon, FormControl, FormErrorMessage, IconButton, Collapse, useDisclosure, Checkbox } from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon, ChevronDownIcon, ChevronRightIcon as ChevronRight } from '@chakra-ui/icons';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { uploadToS3 } from '../services/s3Upload';
import { getParameterByName } from '../api/productApi';
import { useState, useEffect } from 'react';


const schema = Yup.object().shape({
  id: Yup.string().required(),
  naam: Yup.string().required(),
  groep: Yup.string().required(),
  subgroep: Yup.string().required(),
  prijs: Yup.number().required().min(0),
  opties: Yup.string().test('opties-validation', 'Opties moet leeg zijn of minimaal 2 waarden bevatten gescheiden door komma\'s', function(value) {
    if (!value || value.trim() === '') return true;
    const parts = value.split(',').map(part => part.trim()).filter(part => part.length > 0);
    return parts.length >= 2;
  }),
  images: Yup.array().of(Yup.string()).nullable(),
});

export default function ProductCard({ product, products, onSave, onDelete, onNew, onClose, filteredProducts, onNavigate }) {
  const [uploading, setUploading] = useState(false);
  const [categoryStructure, setCategoryStructure] = useState({});
  const [selectedCategory, setSelectedCategory] = useState({ groep: '', subgroep: '' });

  useEffect(() => {
    getParameterByName('productgroepen')
      .then(res => {
        const data = JSON.parse(res.data.value || '{}');
        setCategoryStructure(data);
      })
      .catch(() => {
        setCategoryStructure({});
      });
  }, [products]);

  useEffect(() => {
    setSelectedCategory({ groep: product.groep || '', subgroep: product.subgroep || '' });
  }, [product]);

  const CategorySelector = ({ setFieldValue }) => {
    const GroupItem = ({ groupName, groupData }) => {
      const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: selectedCategory.groep === groupName });
      
      return (
        <Box>
          <Button
            variant="ghost"
            justifyContent="flex-start"
            width="full"
            size="sm"
            fontSize="md"
            py={1}
            leftIcon={groupData.children ? (isOpen ? <ChevronDownIcon /> : <ChevronRight />) : null}
            onClick={onToggle}
            bg={selectedCategory.groep === groupName && !selectedCategory.subgroep ? 'orange.200' : 'transparent'}
            _hover={{ bg: 'orange.100' }}
          >
            {groupName}
          </Button>
          
          {groupData.children && (
            <Collapse in={isOpen}>
              <VStack align="stretch" pl={4} spacing={0}>
                {Object.keys(groupData.children).map(subgroup => (
                  <Button
                    key={subgroup}
                    variant="ghost"
                    size="sm"
                    fontSize="md"
                    py={1}
                    justifyContent="flex-start"
                    onClick={() => {
                      setSelectedCategory({ groep: groupName, subgroep: subgroup });
                      setFieldValue('groep', groupName);
                      setFieldValue('subgroep', subgroup);
                    }}
                    bg={selectedCategory.groep === groupName && selectedCategory.subgroep === subgroup ? 'orange.300' : 'transparent'}
                    _hover={{ bg: 'orange.200' }}
                  >
                    {subgroup}
                  </Button>
                ))}
              </VStack>
            </Collapse>
          )}
        </Box>
      );
    };

    return (
      <Box p={2} bg="gray.50" borderRadius="md" border="1px solid" borderColor="gray.200" maxH="200px" overflowY="auto">
        <Text fontSize="md" fontWeight="bold" mb={1} color="gray.700">Selecteer categorie:</Text>
        <VStack align="stretch" spacing={0}>
          {Object.keys(categoryStructure).map(groupName => (
            <GroupItem key={groupName} groupName={groupName} groupData={categoryStructure[groupName]} />
          ))}
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
          prijs: product.prijs ? parseFloat(product.prijs).toFixed(2) : '',
          images: (() => {
            // Debug: log all product fields to see image storage format
            console.log('Product data for', product.id, ':', product);
            
            // Handle different image storage formats
            if (product.images && Array.isArray(product.images)) {
              console.log('Using images array:', product.images);
              return product.images;
            }
            if (product.image) {
              const imageArray = Array.isArray(product.image) ? product.image : [product.image];
              console.log('Using image field:', imageArray);
              return imageArray;
            }
            if (product.afbeelding) {
              const afbeeldingArray = Array.isArray(product.afbeelding) ? product.afbeelding : [product.afbeelding];
              console.log('Using afbeelding field:', afbeeldingArray);
              return afbeeldingArray;
            }
            if (product.foto) {
              const fotoArray = Array.isArray(product.foto) ? product.foto : [product.foto];
              console.log('Using foto field:', fotoArray);
              return fotoArray;
            }
            console.log('No images found for product', product.id);
            return [];
          })(),
          groep: product.groep || '',
          subgroep: product.subgroep || '',
          opties: product.opties || '',
          nietInWinkel: product.nietInWinkel || false
        }}
        validationSchema={schema}
        onSubmit={(values) => onSave(values)}
      >
        {({ values, setFieldValue, errors, touched }) => (
          <Form>
            <VStack spacing={4}>
            <HStack spacing={4}>
              <FormControl isInvalid={errors.id && touched.id} flex={1}>
                <Field name="id" as={Input} placeholder="id" color="black" borderColor={errors.id && touched.id ? 'red.500' : 'gray.200'} id="product-id" />
                <FormErrorMessage>{errors.id}</FormErrorMessage>
              </FormControl>
              <FormControl isInvalid={errors.prijs && touched.prijs} flex={1}>
                <Field name="prijs">
                  {({ field, form }) => (
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
                <FormErrorMessage>{errors.prijs}</FormErrorMessage>
              </FormControl>
            </HStack>
            <FormControl isInvalid={errors.naam && touched.naam}>
              <Field name="naam" as={Input} placeholder="Naam" color="black" borderColor={errors.naam && touched.naam ? 'red.500' : 'gray.200'} id="product-naam" />
              <FormErrorMessage>{errors.naam}</FormErrorMessage>
            </FormControl>
              <FormControl isInvalid={(errors.groep && touched.groep) || (errors.subgroep && touched.subgroep)}>
                <Field name="groep">
                  {({ form }) => (
                    <CategorySelector setFieldValue={form.setFieldValue} />
                  )}
                </Field>
                <FormErrorMessage>{errors.groep || errors.subgroep}</FormErrorMessage>
              </FormControl>
              
              {selectedCategory.groep && selectedCategory.subgroep && (
                <Text fontSize="sm" color="gray.600">
                  Geselecteerd: <strong>{selectedCategory.groep} - {selectedCategory.subgroep}</strong>
                </Text>
              )}
              <FormControl isInvalid={errors.opties && touched.opties}>
                <Field name="opties" as={Input} placeholder="Opties (gescheiden door komma's)" color="black" borderColor={errors.opties && touched.opties ? 'red.500' : 'gray.200'} />
                <FormErrorMessage>{errors.opties}</FormErrorMessage>
              </FormControl>
              <FormControl>
                <Field name="nietInWinkel">
                  {({ field, form }) => (
                    <Checkbox
                      {...field}
                      isChecked={field.value}
                      onChange={(e) => form.setFieldValue('nietInWinkel', e.target.checked)}
                      colorScheme="orange"
                    >
                      Staat er niet op in de winkel
                    </Checkbox>
                  )}
                </Field>
              </FormControl>
              {/* Navigation and Image Upload Row */}
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
                  onClick={async () => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = 'image/*';
                    input.multiple = true;
                    input.onchange = async (e) => {
                      const files = Array.from(e.target.files);
                      if (files.length > 0) {
                        try {
                          setUploading(true);
                          const uploadPromises = files.map(file => uploadToS3(file));
                          const s3Urls = await Promise.all(uploadPromises);
                          const currentImages = values.images || [];
                          setFieldValue('images', [...currentImages, ...s3Urls]);
                        } catch (error) {
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
                    {values.images.map((imageUrl, index) => (
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
                          onClick={() => {
                            const newImages = values.images.filter((_, i) => i !== index);
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
                <Button type="submit" colorScheme="orange">Opslaan</Button>
                {product.id && (
                  <Button colorScheme="red" onClick={() => onDelete(product.id)}>Verwijder</Button>
                )}
                <Button onClick={onNew}>Nieuw</Button>
                <Button colorScheme="gray" onClick={onClose}>Sluiten</Button>
              </HStack>
            </VStack>
          </Form>
        )}
      </Formik>

    </Box>
  );
}
