/**
 * Admin Member Creation Form - Using Field Registry System
 * 
 * Form for administrators to manually create new member records
 */

import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Input,
  Select,
  Textarea,
  Card,
  CardHeader,
  CardBody,
  SimpleGrid,
  useToast,
  Divider
} from '@chakra-ui/react';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { MEMBER_MODAL_CONTEXTS, MEMBER_FIELDS, getFieldsByGroup, getFilteredEnumOptions } from '../config/memberFields';

interface MemberApplicationFormProps {
  onSubmit: (data: any) => Promise<void>;
  onCancel: () => void;
  userRole?: string;
}

const MemberApplicationForm: React.FC<MemberApplicationFormProps> = ({ 
  onSubmit, 
  onCancel, 
  userRole = 'Members_CRUD_All' 
}) => {
  const toast = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Get memberRegistration context
  const applicationContext = MEMBER_MODAL_CONTEXTS.memberRegistration;

  // Create validation schema from field definitions
  const createValidationSchema = () => {
    const schema: any = {};
    
    applicationContext.sections.forEach(section => {
      // Handle sections with direct fields
      if (section.fields) {
        section.fields.forEach(fieldConfig => {
          const field = MEMBER_FIELDS[fieldConfig.fieldKey];
          if (field && field.validation) {
            field.validation.forEach(rule => {
              if (rule.type === 'required') {
                schema[field.key] = Yup.string().required(rule.message || `${field.label} is verplicht`);
              } else if (rule.type === 'email') {
                schema[field.key] = Yup.string().email(rule.message || 'Ongeldig emailadres');
              } else if (rule.type === 'min_length') {
                schema[field.key] = Yup.string().min(rule.value, rule.message);
              }
            });
          }
        });
      }
      
      // Handle sections with groups
      if (section.groups) {
        section.groups.forEach(groupConfig => {
          const groupFields = getFieldsByGroup(groupConfig.group);
          groupFields.forEach(field => {
            // Check if field should be included
            if (groupConfig.includeFields && !groupConfig.includeFields.includes(field.key)) {
              return; // Skip if not in include list
            }
            
            if (groupConfig.excludeFields && groupConfig.excludeFields.includes(field.key)) {
              return; // Skip if in exclude list
            }
            
            if (field.validation) {
              field.validation.forEach(rule => {
                if (rule.type === 'required') {
                  schema[field.key] = Yup.string().required(rule.message || `${field.label} is verplicht`);
                } else if (rule.type === 'email') {
                  schema[field.key] = Yup.string().email(rule.message || 'Ongeldig emailadres');
                } else if (rule.type === 'min_length') {
                  schema[field.key] = Yup.string().min(rule.value, rule.message);
                }
              });
            }
          });
        });
      }
    });

    return Yup.object().shape(schema);
  };

  // Initial form values
  const initialValues = {
    // Personal
    voornaam: '',
    tussenvoegsel: '',
    achternaam: '',
    geboortedatum: '',
    geslacht: '',
    email: '',
    telefoon: '',
    minderjarigNaam: '',
    nationaliteit: 'Nederlandse',
    
    // Address
    straat: '',
    postcode: '',
    woonplaats: '',
    land: 'Nederland',
    
    // Membership
    status: 'Aangemeld',
    lidmaatschap: '',
    regio: '',
    wiewatwaar: '',
    clubblad: 'Digitaal',
    nieuwsbrief: 'Ja',
    privacy: 'Nee',
    
    // Motor (conditional)
    motormerk: '',
    motortype: '',
    bouwjaar: '',
    kenteken: '',
    
    // Payment
    betaalwijze: 'Incasso',
    bankrekeningnummer: ''
  };

  const handleSubmit = async (values: any) => {
    setIsSubmitting(true);
    try {
      await onSubmit({
        ...values,
        status: 'Aangemeld',
        tijdstempel: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
      
      toast({
        title: 'Lid aangemaakt!',
        description: 'Het nieuwe lid is succesvol aangemaakt.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Fout bij aanmaken',
        description: 'Er is een fout opgetreden. Probeer het opnieuw.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderField = (fieldKey: string, values: any, errors: any, touched: any) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (!field) return null;

    // Check conditional visibility
    if (field.showWhen) {
      const shouldShow = field.showWhen.some(condition => {
        if (condition.operator === 'equals') {
          return values[condition.field] === condition.value;
        }
        if (condition.operator === 'age_less_than') {
          const birthDate = new Date(values[condition.field]);
          const age = new Date().getFullYear() - birthDate.getFullYear();
          return age < condition.value;
        }
        return true;
      });
      if (!shouldShow) return null;
    }

    const error = errors[fieldKey];
    const isTouched = touched[fieldKey];

    return (
      <Box key={fieldKey} mb={1}>
        <FormControl isInvalid={!!(error && isTouched)}>
          <FormLabel mb={0} color="gray.700" fontWeight="semibold" fontSize="sm">
            {field.label}
          </FormLabel>
          <Field name={fieldKey}>
            {({ field: formikField }: any) => {
              if (field.inputType === 'select' && field.enumOptions) {
                // Get filtered enum options based on user role
                const filteredOptions = getFilteredEnumOptions(field, userRole as any);
                return (
                  <Select 
                    {...formikField} 
                    placeholder={field.placeholder}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    size="sm"
                    fontSize="sm"
                  >
                    {filteredOptions.map(option => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </Select>
                );
              } else if (field.inputType === 'textarea') {
                return (
                  <Textarea 
                    {...formikField} 
                    placeholder={field.placeholder}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    rows={3}
                    size="sm"
                    fontSize="sm"
                  />
                );
              } else if (field.inputType === 'date') {
                return (
                  <Input 
                    {...formikField} 
                    type="date"
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    size="sm"
                    fontSize="sm"
                  />
                );
              } else if (field.inputType === 'number') {
                return (
                  <Input 
                    {...formikField} 
                    type="number" 
                    placeholder={field.placeholder}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    size="sm"
                    fontSize="sm"
                  />
                );
              } else if (field.inputType === 'email') {
                return (
                  <Input 
                    {...formikField} 
                    type="email" 
                    placeholder={field.placeholder}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    size="sm"
                    fontSize="sm"
                  />
                );
              } else if (field.inputType === 'tel') {
                return (
                  <Input 
                    {...formikField} 
                    type="tel" 
                    placeholder={field.placeholder}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    size="sm"
                    fontSize="sm"
                  />
                );
              } else {
                return (
                  <Input 
                    {...formikField} 
                    type="text" 
                    placeholder={field.placeholder}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    size="sm"
                    fontSize="sm"
                  />
                );
              }
            }}
          </Field>
          {error && isTouched && (
            <FormErrorMessage>{error as string}</FormErrorMessage>
          )}
        </FormControl>
      </Box>
    );
  };

  const renderSectionFields = (section: any, values: any, errors: any, touched: any) => {
    const fields: any[] = [];
    
    // Add fields from groups
    if (section.groups) {
      section.groups.forEach((groupConfig: any) => {
        const groupFields = getFieldsByGroup(groupConfig.group);
        groupFields.forEach(field => {
          // Check if field should be included
          if (groupConfig.includeFields && !groupConfig.includeFields.includes(field.key)) {
            return;
          }
          if (groupConfig.excludeFields && groupConfig.excludeFields.includes(field.key)) {
            return;
          }
          fields.push(field.key);
        });
      });
    }
    
    // Add individual fields
    if (section.fields) {
      section.fields.forEach((fieldConfig: any) => {
        if (fieldConfig.visible) {
          fields.push(fieldConfig.fieldKey);
        }
      });
    }
    
    return fields.map(fieldKey => renderField(fieldKey, values, errors, touched));
  };

  return (
    <Box maxW="1200px" mx="auto" p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Heading color="orange.400" mb={2} textAlign="left">
            Nieuw Lid Aanmaken
          </Heading>
          <Text color="gray.300" textAlign="left">
            Vul onderstaande gegevens in om een nieuw lid aan te maken
          </Text>
        </Box>

        {/* Form */}
        <Formik
          initialValues={initialValues}
          validationSchema={createValidationSchema()}
          onSubmit={handleSubmit}
        >
          {({ values, errors, touched, isValid }) => (
            <Form>
              <VStack spacing={6} align="stretch">
                {/* Render all sections */}
                {applicationContext.sections
                  .filter(section => section.name !== 'vrijwaring' && section.name !== 'ondergetekende')
                  .sort((a, b) => a.order - b.order)
                  .map(section => {
                    // Check section conditional visibility
                    if (section.showWhen) {
                      const shouldShow = section.showWhen.some(condition => {
                        if (condition.operator === 'equals') {
                          return values[condition.field] === condition.value;
                        }
                        return true;
                      });
                      if (!shouldShow) return null;
                    }

                    return (
                      <Card key={section.name} bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
                        <CardHeader bg="gray.700" borderRadius="lg lg 0 0" py={1}>
                          <Heading size="sm" color="orange.300" textAlign="left">
                            {section.title}
                          </Heading>
                        </CardHeader>
                        <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
                          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>
                            {renderSectionFields(section, values, errors, touched)}
                          </SimpleGrid>
                        </CardBody>
                      </Card>
                    );
                  })}

                {/* Vrijwaring Section */}
                <Card bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
                  <CardHeader bg="gray.700" borderRadius="lg lg 0 0" py={1}>
                    <Heading size="sm" color="orange.300" textAlign="left">
                      Vrijwaring
                    </Heading>
                  </CardHeader>
                  <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
                    <Text fontSize="sm" color="gray.700">
                      Met aanvaarding van het lidmaatschap verklaar je dat deelname aan activiteiten, wel of niet georganiseerd door of namens het bestuur van H-DCN, geheel voor eigen risico en rekening is. Het bestuur H-DCN, noch haar afzonderlijke bestuursleden c.q. commissarissen aanvaarden enige aansprakelijkheid voor schade in welke vorm dan ook, direct of indirect, voortvloeiende uit activiteiten door of namens H-DCN.
                    </Text>
                  </CardBody>
                </Card>

                {/* Ondergetekende Section */}
                <Card bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
                  <CardHeader bg="gray.700" borderRadius="lg lg 0 0" py={1}>
                    <Heading size="sm" color="orange.300" textAlign="left">
                      Ondergetekende
                    </Heading>
                  </CardHeader>
                  <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
                    <Text fontSize="sm" color="gray.700">
                      Ondergetekende verklaart bovenstaande naar waarheid te hebben ingevuld en zich te zullen houden aan de Statuten en het Huishoudelijk Reglement van de H-DCN (dit inzage op de website (https://h-dcn.nl/home/hdcnalgemeneinformatie), en of bij het regio- c.q. algemeen secretariaat). Ondergetekende machtigt hierbij de H-DCN de jaarlijkse contributie te innen m.b.v. automatische incasso van haar of zijn bankrekening, tot schriftelijke wederopzegging, waarbij de termijn tot uiterlijk 01 november voor het komende jaar in acht genomen moet worden.
                    </Text>
                  </CardBody>
                </Card>

                {/* Action Buttons */}
                <HStack justify="space-between" pt={4}>
                  <Button
                    variant="outline"
                    onClick={onCancel}
                    size="lg"
                    color="gray.300"
                    borderColor="gray.500"
                    _hover={{ borderColor: "gray.400", color: "white" }}
                  >
                    Annuleren
                  </Button>
                  
                  <Button
                    type="submit"
                    colorScheme="orange"
                    isLoading={isSubmitting}
                    isDisabled={!isValid}
                    size="lg"
                  >
                    Lid Aanmaken
                  </Button>
                </HStack>
              </VStack>
            </Form>
          )}
        </Formik>
      </VStack>
    </Box>
  );
};

export default MemberApplicationForm;