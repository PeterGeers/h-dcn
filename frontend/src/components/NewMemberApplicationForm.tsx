/**
 * New Member Application Form - Simplified Single Page Version
 * 
 * Single form for new members who have logged in via Cognito
 * but don't exist in the member table yet. Shows all sections at once.
 */

import React, { useState, useEffect } from 'react';
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
  Tooltip,
  Divider,
  Spinner
} from '@chakra-ui/react';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { MEMBER_MODAL_CONTEXTS, MEMBER_FIELDS, getVisibleFields, getFilteredEnumOptions } from '../config/memberFields';
import { canViewField, canEditField } from '../utils/fieldResolver';
import { ApiService } from '../services/apiService';
import { computeCalculatedFields, getCalculatedFieldValue } from '../utils/calculatedFields';

interface NewMemberApplicationFormProps {
  userEmail: string; // From Cognito
  onSubmit: (data: any) => Promise<void>;
  onCancel?: () => void;
}

const NewMemberApplicationForm: React.FC<NewMemberApplicationFormProps> = ({ 
  userEmail, 
  onSubmit, 
  onCancel 
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [existingApplication, setExistingApplication] = useState<any>(null);
  const [isLoadingExisting, setIsLoadingExisting] = useState(true);
  const toast = useToast();

  // Get membership registration context (not membershipApplication)
  const applicationContext = MEMBER_MODAL_CONTEXTS.memberRegistration;
  const userRole = 'verzoek_lid'; // New applicants have applicant role

  // Helper function to determine if a field is required based on memberFields configuration
  const isRequiredField = (fieldKey: string) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (!field) return false;
    
    // Check if field is marked as required in the configuration
    if (field.required === true) return true;
    
    // Check validation rules for required (but skip conditional requirements)
    if (field.validation) {
      return field.validation.some(rule => rule.type === 'required' && !rule.condition);
    }
    
    return false;
  };

  // Create validation schema based on memberFields configuration
  const createValidationSchema = () => {
    const schemaFields: Record<string, any> = {};
    
    // Get all fields from the memberRegistration context
    applicationContext.sections.forEach(section => {
      const visibleFields = getVisibleFields(section);
      visibleFields.forEach(fieldConfig => {
        const field = MEMBER_FIELDS[fieldConfig.fieldKey];
        if (!field) return;
        
        const fieldKey = fieldConfig.fieldKey;
        
        // Skip fields that are not allowed for new applicants
        const forbiddenFields = ['status', 'created_at', 'updated_at', 'korte_naam', 'leeftijd', 'verjaardag'];
        if (forbiddenFields.includes(fieldKey)) return;
        
        // Skip bankrekeningnummer - it has custom conditional validation below
        if (fieldKey === 'bankrekeningnummer') return;
        
        // Skip email validation - it's pre-filled from Cognito
        if (fieldKey === 'email') {
          schemaFields[fieldKey] = Yup.string().email('Voer een geldig emailadres in');
          return;
        }
        
        let fieldSchema: any;
        
        // Create base schema based on data type
        switch (field.dataType) {
          case 'date':
            fieldSchema = Yup.date();
            // Add max date validation for birth date
            if (fieldConfig.fieldKey === 'geboortedatum') {
              fieldSchema = fieldSchema.max(new Date(), 'Geboortedatum kan niet in de toekomst liggen');
            }
            break;
          case 'number':
            fieldSchema = Yup.number();
            break;
          case 'enum':
            const filteredOptions = getFilteredEnumOptions(field, userRole);
            fieldSchema = Yup.string().oneOf(filteredOptions, `Selecteer een geldige ${field.label.toLowerCase()}`);
            break;
          default:
            fieldSchema = Yup.string();
        }
        
        // Apply validation rules from field configuration
        if (field.validation) {
          field.validation.forEach(rule => {
            switch (rule.type) {
              case 'required':
                // Check if condition applies
                if (!rule.condition) {
                  fieldSchema = fieldSchema.required(rule.message || `${field.label} is verplicht`);
                }
                break;
              case 'email':
                if (field.dataType === 'string') {
                  fieldSchema = fieldSchema.email(rule.message || 'Voer een geldig emailadres in');
                }
                break;
              case 'min_length':
                if (field.dataType === 'string') {
                  fieldSchema = fieldSchema.min(rule.value, rule.message || `Minimaal ${rule.value} karakters`);
                }
                break;
              case 'max_length':
                if (field.dataType === 'string') {
                  fieldSchema = fieldSchema.max(rule.value, rule.message || `Maximaal ${rule.value} karakters`);
                }
                break;
              case 'iban':
                if (field.dataType === 'string') {
                  // Use exact same IBAN validation as MemberEditView for consistency
                  fieldSchema = fieldSchema.test(
                    'iban',
                    rule.message || 'Ongeldig IBAN nummer',
                    (value) => !value || /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$/.test(value)
                  );
                }
                break;
              case 'pattern':
                if (field.dataType === 'string') {
                  fieldSchema = fieldSchema.matches(new RegExp(rule.value), rule.message || 'Ongeldige format');
                }
                break;
              case 'min':
                if (field.dataType === 'number') {
                  fieldSchema = fieldSchema.min(rule.value, rule.message || `Minimaal ${rule.value}`);
                }
                break;
              case 'max':
                if (field.dataType === 'number') {
                  fieldSchema = fieldSchema.max(rule.value, rule.message || `Maximaal ${rule.value}`);
                }
                break;
            }
          });
        }
        
        // Check if field is required
        if (isRequiredField(fieldConfig.fieldKey)) {
          const requiredMessage = field.validation?.find(r => r.type === 'required')?.message || `${field.label} is verplicht`;
          fieldSchema = fieldSchema.required(requiredMessage);
        }
        
        schemaFields[fieldConfig.fieldKey] = fieldSchema;
      });
    });
    
    // Override privacy validation - both 'Ja' and 'Nee' should be valid, but field is required
    schemaFields.privacy = Yup.string()
      .required('Privacy keuze is verplicht')
      .oneOf(['Ja', 'Nee'], 'Selecteer Ja of Nee voor privacy');
    
    // Add conditional validation for minors
    schemaFields.minderjarigNaam = Yup.string().when('geboortedatum', {
      is: (birthDate: string) => {
        if (!birthDate) return false;
        const age = (new Date().getTime() - new Date(birthDate).getTime()) / (1000 * 60 * 60 * 24 * 365);
        return age < 18;
      },
      then: (schema) => schema.required('Naam ouder/voogd is verplicht voor minderjarigen'),
      otherwise: (schema) => schema.notRequired()
    });
    
    // Add conditional validation for IBAN based on membership type (matching field configuration)
    schemaFields.bankrekeningnummer = Yup.string().when('lidmaatschap', {
      is: (lidmaatschap: string) => {
        const requiredMembershipTypes = ['Gewoon lid', 'Gezins lid', 'Donateur', 'Gezins donateur', 'Sponsor'];
        return requiredMembershipTypes.includes(lidmaatschap);
      },
      then: (schema) => schema.required('IBAN is verplicht voor dit lidmaatschapstype')
        .test('iban', 'Voer een geldig IBAN nummer in', (value) => 
          !value || /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$/.test(value)
        )
        .min(15, 'IBAN moet minimaal 15 karakters bevatten')
        .max(34, 'IBAN mag maximaal 34 karakters bevatten'),
      otherwise: (schema) => schema.notRequired()
    });
    
    console.log('Validation schema fields:', Object.keys(schemaFields));
    return Yup.object(schemaFields);
  };

  const validationSchema = createValidationSchema();

  // Check for existing application on component mount
  useEffect(() => {
    const checkExistingApplication = async () => {
      try {
        // Try to get existing member data using /members/me endpoint
        const response = await ApiService.get('/members/me');
        if (response.success && response.data && response.data.member) {
          // Only set existingApplication if member data actually exists
          setExistingApplication(response.data.member);
          console.log('Existing member application found:', response.data.member);
        } else {
          console.log('No existing application found - this is normal for new applicants');
        }
      } catch (error) {
        console.log('Error checking for existing application (this is normal for new users):', error);
      } finally {
        setIsLoadingExisting(false);
      }
    };

    checkExistingApplication();
  }, [userEmail]);

  // Initial form values with email from Cognito and existing data if available
  const getInitialValues = () => {
    const initialValues: Record<string, any> = {
      email: userEmail, // Always use the email from Cognito (but won't be sent to backend)
      // Don't include status, created_at, updated_at - backend handles these
    };
    
    // Set defaults from field configuration
    applicationContext.sections.forEach(section => {
      const visibleFields = getVisibleFields(section);
      visibleFields.forEach(fieldConfig => {
        const field = MEMBER_FIELDS[fieldConfig.fieldKey];
        if (!field) return;
        
        const fieldKey = fieldConfig.fieldKey;
        
        // Skip system fields that backend handles
        const systemFields = ['email', 'status', 'created_at', 'updated_at'];
        if (systemFields.includes(fieldKey)) return;
        
        // Use existing application data if available, otherwise use field default or empty string
        if (existingApplication && existingApplication[fieldKey] !== undefined) {
          initialValues[fieldKey] = existingApplication[fieldKey];
        } else if (field.defaultValue !== undefined) {
          initialValues[fieldKey] = field.defaultValue;
        } else {
          // Set appropriate empty value based on data type
          switch (field.dataType) {
            case 'string':
              initialValues[fieldKey] = '';
              break;
            case 'number':
              initialValues[fieldKey] = '';
              break;
            case 'date':
              initialValues[fieldKey] = '';
              break;
            case 'boolean':
              initialValues[fieldKey] = false;
              break;
            case 'enum':
              initialValues[fieldKey] = '';
              break;
            default:
              initialValues[fieldKey] = '';
          }
        }
      });
    });
    
    // Ensure privacy is not defaulted to 'Ja' - require explicit consent
    if (!existingApplication?.privacy) {
      initialValues.privacy = '';
    }
    
    // Add email back for display purposes only (won't be sent to backend)
    initialValues.email = userEmail;
    
    console.log('Initial form values:', initialValues);
    return initialValues;
  };

  const initialValues = getInitialValues();

  const handleSubmit = async (values: any) => {
    setIsSubmitting(true);
    try {
      // Filter out forbidden fields for new applicants
      const baseAllowedFields = [
        // Required fields
        'voornaam', 'achternaam', 'geboortedatum', 'geslacht', 'telefoon',
        'straat', 'postcode', 'woonplaats', 'lidmaatschap', 'regio', 'privacy',
        // Optional fields
        'initialen', 'tussenvoegsel', 'minderjarigNaam', 'land', 'motormerk',
        'motortype', 'bouwjaar', 'kenteken', 'wiewatwaar', 'clubblad',
        'nieuwsbrief', 'betaalwijze', 'bankrekeningnummer'
      ];
      
      // For updates (PUT), don't include email and status as they shouldn't change
      // For new applications (POST), include email and status
      const allowedFields = existingApplication 
        ? baseAllowedFields  // PUT: exclude email and status
        : [...baseAllowedFields, 'email', 'status']; // POST: include email and status
      
      console.log('Is update (existingApplication):', !!existingApplication);
      console.log('Allowed fields for submission:', allowedFields);
      
      const submissionData: any = {};
      
      // Only include allowed fields that have values
      allowedFields.forEach(fieldKey => {
        const fieldValue = values[fieldKey];
        if (fieldValue !== undefined && fieldValue !== '') {
          submissionData[fieldKey] = fieldValue;
          console.log(`Including field ${fieldKey}:`, fieldValue);
        } else {
          console.log(`Skipping field ${fieldKey}:`, fieldValue);
        }
      });
      
      // For new applications (POST), always include email and status
      // For updates (PUT), don't include these as they shouldn't change
      if (!existingApplication) {
        submissionData.email = userEmail;
        submissionData.status = 'Aangemeld';
      }
      
      console.log('Filtered submission data:', submissionData);
      console.log('Is update (existing application):', !!existingApplication);
      console.log('Final submission keys:', Object.keys(submissionData));

      await onSubmit(submissionData);
      
      const isUpdate = existingApplication !== null;
      
      toast({
        title: isUpdate ? 'Aanvraag bijgewerkt' : 'Aanvraag verzonden',
        description: isUpdate 
          ? 'Uw wijzigingen zijn opgeslagen en worden opnieuw beoordeeld.'
          : 'Uw aanvraag is succesvol verzonden en wordt beoordeeld.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Fout bij verzenden',
        description: 'Er is een fout opgetreden. Probeer het opnieuw.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderField = (fieldKey: string, values: any, errors: any, touched: any, setFieldValue: any) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (!field) return null;

    // Skip fields that are not allowed for new applicants
    const forbiddenFields = ['status', 'created_at', 'updated_at'];
    if (forbiddenFields.includes(fieldKey)) return null;

    const canView = canViewField(field, userRole, values);
    const canEdit = canEditField(field, userRole, values);
    
    if (!canView) return null;

    // Handle computed fields and field mappings
    let value = values[fieldKey];
    
    // For email field, always use the userEmail from Cognito
    if (fieldKey === 'email') {
      value = userEmail;
    } else if (field.defaultValue !== undefined && (value === '' || value === undefined || value === null)) {
      value = field.defaultValue;
    }
    
    // Special handling for ingangsdatum field which maps to tijdstempel
    if (fieldKey === 'ingangsdatum' && field.key === 'tijdstempel') {
      value = values['tijdstempel'] || values[fieldKey];
    }
    
    if (field.computed) {
      // Use the shared calculated fields utility
      value = getCalculatedFieldValue(values, fieldKey);
    }

    const error = errors[fieldKey];
    const isTouched = touched[fieldKey];
    const isRequired = isRequiredField(fieldKey);

    // Check conditional visibility
    if (field.showWhen) {
      const shouldShow = field.showWhen.some(condition => {
        if (condition.operator === 'equals') {
          const result = values[condition.field] === condition.value;
          console.log(`Conditional visibility for ${fieldKey}: ${condition.field} === ${condition.value} = ${result} (actual: ${values[condition.field]})`);
          return result;
        }
        if (condition.operator === 'age_less_than') {
          const birthDate = new Date(values[condition.field]);
          const age = new Date().getFullYear() - birthDate.getFullYear();
          const result = age < condition.value;
          console.log(`Age condition for ${fieldKey}: age ${age} < ${condition.value} = ${result}`);
          return result;
        }
        return true;
      });
      if (!shouldShow) {
        console.log(`Field ${fieldKey} hidden due to conditional visibility`);
        return null;
      }
    }

    return (
      <Box key={fieldKey} mb={1}>
        <FormControl isInvalid={!!(error && isTouched)}>
          <FormLabel mb={0} color="gray.700" fontWeight="semibold" fontSize="sm">
            <Tooltip label={field.helpText}>
              <Text cursor="help">
                {field.label}
              </Text>
            </Tooltip>
          </FormLabel>
          
          <Field name={fieldKey}>
            {({ field: formikField }: any) => {
              if (field.inputType === 'select' && field.enumOptions) {
                const filteredOptions = getFilteredEnumOptions(field, userRole);
                return (
                  <Select
                    {...formikField}
                    value={value || ''}
                    onChange={(e) => setFieldValue(fieldKey, e.target.value)}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    isDisabled={!canEdit}
                    size="sm"
                    fontSize="sm"
                    placeholder={field.placeholder}
                  >
                    <option value="">Selecteer...</option>
                    {filteredOptions.map((option: any) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </Select>
                );
              }
              
              if (field.inputType === 'textarea') {
                return (
                  <Textarea
                    {...formikField}
                    value={value || ''}
                    onChange={(e) => setFieldValue(fieldKey, e.target.value)}
                    bg="white"
                    borderColor="gray.300"
                    _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                    _hover={{ borderColor: "orange.400" }}
                    isDisabled={!canEdit}
                    rows={3}
                    size="sm"
                    fontSize="sm"
                    placeholder={field.placeholder}
                  />
                );
              }
              
              return (
                <Input
                  {...formikField}
                  type={field.inputType === 'text' ? 'text' : field.inputType || 'text'}
                  value={value || ''}
                  onChange={(e) => setFieldValue(fieldKey, e.target.value)}
                  bg="white"
                  borderColor="gray.300"
                  _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                  _hover={{ borderColor: "orange.400" }}
                  isDisabled={!canEdit || fieldKey === 'email' || field.computed} // Email and computed fields are read-only
                  size="sm"
                  fontSize="sm"
                  placeholder={field.placeholder}
                />
              );
            }}
          </Field>
          
          {error && isTouched && (
            <FormErrorMessage>{error}</FormErrorMessage>
          )}
        </FormControl>
      </Box>
    );
  };

  const renderSection = (section: any, values: any, errors: any, touched: any, setFieldValue: any) => {
    // Check section-level showWhen conditions
    if (section.showWhen) {
      const shouldShow = section.showWhen.some((condition: any) => {
        if (condition.operator === 'equals') {
          return values[condition.field] === condition.value;
        }
        return true;
      });
      if (!shouldShow) return null;
    }
    
    const visibleFields = getVisibleFields(section);
    
    if (visibleFields.length === 0) return null;

    return (
      <Card key={section.name} bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg" mb={6}>
        <CardHeader bg="gray.700" borderRadius="lg lg 0 0" py={1}>
          <Heading size="sm" color="orange.300" textAlign="left">
            {section.title}
          </Heading>
        </CardHeader>
        <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>
            {visibleFields.map((fieldConfig: any) => 
              renderField(fieldConfig.fieldKey, values, errors, touched, setFieldValue)
            )}
          </SimpleGrid>
        </CardBody>
      </Card>
    );
  };

  if (isLoadingExisting) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        minH="100vh" 
        bg="black"
      >
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.500" thickness="4px" />
          <Text color="gray.300">Gegevens laden...</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box maxW="1200px" mx="auto" p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box textAlign="center" mb={6}>
          <Heading size="xl" color="orange.300" mb={2}>
            {existingApplication ? 'Wijzig je lidmaatschapsaanvraag' : 'Welkom bij H-DCN!'}
          </Heading>
          <Text color="gray.300" fontSize="lg" mb={4}>
            {existingApplication 
              ? 'Je kunt je gegevens wijzigen en opnieuw indienen voor herbeoordeling'
              : 'Met dit formulier kun je je aanmelden voor het lidmaatschap van de H-DCN (Harley-Davidson Club Nederland).'
            }
          </Text>
          {existingApplication && (
            <Text color="orange.300" fontSize="md" mb={4}>
              Status: {existingApplication.status} • Ingediend: {new Date(existingApplication.created_at).toLocaleDateString('nl-NL')}
            </Text>
          )}
          <Divider borderColor="orange.400" />
        </Box>

        {/* Form */}
        <Formik
          initialValues={initialValues}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
          enableReinitialize
        >
          {({ values, errors, touched, isValid, setFieldValue }) => {
            // Debug logging to see validation state
            console.log('Form validation state:', { isValid, errors, values });
            
            return (
            <Form>
              <VStack spacing={6} align="stretch">
                {/* Render all sections */}
                {applicationContext.sections.map((section) => 
                  renderSection(section, values, errors, touched, setFieldValue)
                )}

                {/* Vrijwaring Section */}
                <Card bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg" mb={6}>
                  <CardHeader bg="gray.700" borderRadius="lg lg 0 0" py={1}>
                    <Heading size="sm" color="orange.300" textAlign="left">
                      Vrijwaring
                    </Heading>
                  </CardHeader>
                  <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
                    <Text color="gray.700" fontSize="sm" lineHeight="1.6">
                      Met aanvaarding van het lidmaatschap verklaar je dat deelname aan activiteiten, wel of niet georganiseerd door of namens het bestuur van H-DCN, geheel voor eigen risico en rekening is. Het bestuur H-DCN, noch haar afzonderlijke bestuursleden c.q. commissarissen aanvaarden enige aansprakelijkheid voor schade in welke vorm dan ook, direct of indirect, voortvloeiende uit activiteiten door of namens H-DCN.
                    </Text>
                  </CardBody>
                </Card>

                {/* Ondergetekende Section */}
                <Card bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg" mb={6}>
                  <CardHeader bg="gray.700" borderRadius="lg lg 0 0" py={1}>
                    <Heading size="sm" color="orange.300" textAlign="left">
                      Ondergetekende
                    </Heading>
                  </CardHeader>
                  <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
                    <Text color="gray.700" fontSize="sm" lineHeight="1.6" mb={4}>
                      Ondergetekende verklaart bovenstaande naar waarheid te hebben ingevuld en zich te zullen houden aan de Statuten en het Huishoudelijk Reglement van de H-DCN (dit ter inzage op de website{' '}
                      <Text as="a" 
                            href="https://h-dcn.nl/home/hdcnalgemeneinformatie" 
                            target="_blank" 
                            rel="noopener noreferrer"
                            color="orange.600" 
                            textDecoration="underline"
                            _hover={{ color: "orange.500" }}>
                        https://h-dcn.nl/home/hdcnalgemeneinformatie
                      </Text>
                      , en of bij het regio- c.q. algemeen secretariaat).
                    </Text>
                    <Text color="gray.700" fontSize="sm" lineHeight="1.6">
                      Ondergetekende machtigt hierbij de H-DCN de jaarlijkse contributie te innen m.b.v. automatische incasso van haar of zijn bankrekening, tot schriftelijke wederopzegging, waarbij de termijn tot uiterlijk 01 november voor het komende jaar in acht genomen moet worden.
                    </Text>
                  </CardBody>
                </Card>

                {/* Submit Button */}
                <Card bg="gray.800" borderColor="orange.400" border="2px" borderRadius="lg">
                  <CardBody>
                    <VStack spacing={4}>
                      <Text color="gray.300" textAlign="center">
                        {existingApplication 
                          ? 'Door op "Wijzigingen Opslaan" te klikken, wordt je aanvraag opnieuw ter beoordeling ingediend.'
                          : 'Door op "Aanmelden" te klikken, bevestigt u dat de verstrekte informatie correct is.'
                        }
                      </Text>
                      <HStack spacing={4} justify="center">
                        {onCancel && (
                          <Button
                            variant="outline"
                            colorScheme="orange"
                            onClick={onCancel}
                            size="lg"
                          >
                            Annuleren
                          </Button>
                        )}
                        <Button
                          type="submit"
                          colorScheme="orange"
                          size="lg"
                          isLoading={isSubmitting}
                          isDisabled={!isValid}
                          loadingText={existingApplication ? "Opslaan..." : "Aanmelden..."}
                          px={8}
                        >
                          {existingApplication ? "Wijzigingen Opslaan" : "Aanmelden"}
                        </Button>
                      </HStack>
                      
                      {/* Debug info */}
                      {!isValid && (
                        <Box mt={4} p={3} bg="red.50" borderRadius="md" border="1px" borderColor="red.200">
                          <Text fontSize="sm" color="red.600" fontWeight="semibold">
                            Validatie fouten:
                          </Text>
                          <Text fontSize="xs" color="red.500" mt={1}>
                            {JSON.stringify(errors, null, 2)}
                          </Text>
                        </Box>
                      )}
                    </VStack>
                  </CardBody>
                </Card>
              </VStack>
            </Form>
            );
          }}
        </Formik>
      </VStack>
    </Box>
  );
};

export default NewMemberApplicationForm;
