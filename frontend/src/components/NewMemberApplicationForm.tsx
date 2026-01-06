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
import { MEMBER_MODAL_CONTEXTS, MEMBER_FIELDS, getVisibleFields, getFilteredEnumOptions } from '../config/memberFields';
import { canViewField, canEditField } from '../utils/fieldResolver';
import { membershipService } from '../utils/membershipService';

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
  const userRole = 'Verzoek_lid'; // New applicants have applicant role

  // Check for existing application on component mount
  useEffect(() => {
    const checkExistingApplication = async () => {
      try {
        // Try to get existing member data by email
        const existingMember = await membershipService.getMemberByEmail(userEmail);
        if (existingMember) {
          setExistingApplication(existingMember);
        }
      } catch (error) {
        console.log('No existing application found (this is normal for new users)');
      } finally {
        setIsLoadingExisting(false);
      }
    };

    checkExistingApplication();
  }, [userEmail]);

  // Initial form values with email from Cognito and existing data if available
  const initialValues = {
    email: userEmail,
    status: existingApplication?.status || 'Aangemeld',
    created_at: existingApplication?.created_at || new Date().toISOString(),
    // Set defaults for required fields, using existing data if available
    lidmaatschap: existingApplication?.lidmaatschap || '',
    regio: existingApplication?.regio || '',
    clubblad: existingApplication?.clubblad || 'Digitaal',
    nieuwsbrief: existingApplication?.nieuwsbrief || 'Ja',
    privacy: existingApplication?.privacy || 'Nee',
    betaalwijze: existingApplication?.betaalwijze || 'Incasso',
    land: existingApplication?.land || 'Nederland',
    nationaliteit: existingApplication?.nationaliteit || 'Nederlandse',
    // Pre-populate all other fields from existing application
    ...existingApplication
  };

  const handleSubmit = async (values: any) => {
    setIsSubmitting(true);
    try {
      const submissionData = {
        ...values,
        updated_at: new Date().toISOString()
      };

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

    const canView = canViewField(field, userRole, values);
    const canEdit = canEditField(field, userRole, values);
    
    if (!canView) return null;

    // Handle computed fields and field mappings
    let value = values[fieldKey] || field.defaultValue;
    
    // Special handling for ingangsdatum field which maps to tijdstempel
    if (fieldKey === 'ingangsdatum' && field.key === 'tijdstempel') {
      value = values['tijdstempel'] || values[fieldKey];
    }
    
    if (field.computed && field.computeFrom && field.computeFunction) {
      let sourceValue = values[field.computeFrom];
      
      if (sourceValue && field.computeFunction === 'yearsDifference') {
        const sourceDate = new Date(sourceValue);
        if (!isNaN(sourceDate.getTime())) {
          const currentDate = new Date();
          const yearsDiff = currentDate.getFullYear() - sourceDate.getFullYear();
          const monthDiff = currentDate.getMonth() - sourceDate.getMonth();
          value = monthDiff < 0 || (monthDiff === 0 && currentDate.getDate() < sourceDate.getDate()) 
            ? yearsDiff - 1 
            : yearsDiff;
        }
      } else if (sourceValue && field.computeFunction === 'year') {
        const sourceDate = new Date(sourceValue);
        if (!isNaN(sourceDate.getTime())) {
          value = sourceDate.getFullYear();
        }
      }
    }

    const error = errors[fieldKey];
    const isTouched = touched[fieldKey];

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

    return (
      <Box key={fieldKey} mb={1}>
        <FormControl isInvalid={!!(error && isTouched)} isRequired={false}>
          <FormLabel mb={0} color="gray.700" fontWeight="semibold" fontSize="sm">
            <Tooltip label={field.helpText}>
              <Text cursor="help">{field.label}</Text>
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
                  isDisabled={!canEdit || fieldKey === 'email'} // Email is always read-only
                  size="sm"
                  fontSize="sm"
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
          onSubmit={handleSubmit}
          enableReinitialize
        >
          {({ values, errors, touched, isValid, setFieldValue }) => (
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
                          loadingText={existingApplication ? "Opslaan..." : "Aanmelden..."}
                          px={8}
                        >
                          {existingApplication ? "Wijzigingen Opslaan" : "Aanmelden"}
                        </Button>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>
              </VStack>
            </Form>
          )}
        </Formik>
      </VStack>
    </Box>
  );
};

export default NewMemberApplicationForm;
