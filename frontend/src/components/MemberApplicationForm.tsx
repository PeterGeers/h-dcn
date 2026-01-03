/**
 * Member Application Form - Using Field Registry System
 * 
 * Progressive disclosure membership application form using membershipApplication context
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
  Stepper,
  Step,
  StepIndicator,
  StepStatus,
  StepIcon,
  StepNumber,
  StepTitle,
  StepDescription,
  StepSeparator,
  useSteps,
  Alert,
  AlertIcon,
  Card,
  CardHeader,
  CardBody,
  SimpleGrid,
  Checkbox,
  useToast
} from '@chakra-ui/react';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { MEMBER_MODAL_CONTEXTS, MEMBER_FIELDS } from '../config/memberFields';
import { renderFieldValue, getFieldInputComponent } from '../utils/fieldRenderers';
import { canViewField, canEditField } from '../utils/fieldResolver';

interface MemberApplicationFormProps {
  onSubmit: (data: any) => Promise<void>;
  onCancel: () => void;
}

const MemberApplicationForm: React.FC<MemberApplicationFormProps> = ({ onSubmit, onCancel }) => {
  const toast = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Get membershipApplication context
  const applicationContext = MEMBER_MODAL_CONTEXTS.membershipApplication;
  const steps = applicationContext.sections.map(section => ({
    title: section.title,
    description: section.name
  }));

  const { activeStep, setActiveStep } = useSteps({
    index: 0,
    count: steps.length,
  });

  // Create validation schema from field definitions
  const createValidationSchema = () => {
    const schema: any = {};
    
    applicationContext.sections.forEach(section => {
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
    
    // Address
    straat: '',
    postcode: '',
    woonplaats: '',
    land: 'Nederland',
    nationaliteit: 'Nederlandse',
    
    // Membership
    lidmaatschap: '',
    regio: '',
    wiewatwaar: '',
    
    // Motor (conditional)
    motormerk: '',
    motortype: '',
    bouwjaar: '',
    kenteken: '',
    
    // Preferences
    clubblad: 'Digitaal',
    nieuwsbrief: 'Ja',
    privacy: 'Nee',
    
    // Payment
    betaalwijze: 'Incasso',
    bankrekeningnummer: '',
    
    // Agreement
    akkoord: false
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
        title: 'Aanmelding verzonden!',
        description: 'Uw aanmelding is succesvol verzonden en wordt binnenkort behandeld.',
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
      <FormControl key={fieldKey} isInvalid={!!(error && isTouched)}>
        <FormLabel>{field.label}</FormLabel>
        <Field name={fieldKey}>
          {({ field: formikField }: any) => {
            if (field.inputType === 'select' && field.enumOptions) {
              return (
                <Select {...formikField} placeholder={field.placeholder}>
                  {field.enumOptions.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </Select>
              );
            } else if (field.inputType === 'textarea') {
              return <Textarea {...formikField} placeholder={field.placeholder} />;
            } else if (field.inputType === 'date') {
              return <Input {...formikField} type="date" />;
            } else if (field.inputType === 'number') {
              return <Input {...formikField} type="number" placeholder={field.placeholder} />;
            } else if (field.inputType === 'email') {
              return <Input {...formikField} type="email" placeholder={field.placeholder} />;
            } else if (field.inputType === 'tel') {
              return <Input {...formikField} type="tel" placeholder={field.placeholder} />;
            } else {
              return <Input {...formikField} type="text" placeholder={field.placeholder} />;
            }
          }}
        </Field>
        {field.helpText && <Text fontSize="sm" color="gray.600" mt={1}>{field.helpText}</Text>}
        <FormErrorMessage>{error as string}</FormErrorMessage>
      </FormControl>
    );
  };

  return (
    <Box maxW="800px" mx="auto" p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box textAlign="center">
          <Heading color="orange.500" mb={2}>
            Aanmelding H-DCN Lidmaatschap
          </Heading>
          <Text color="gray.600">
            Vul onderstaande gegevens in om lid te worden van de H-DCN
          </Text>
        </Box>

        {/* Progress Stepper */}
        <Stepper index={activeStep} colorScheme="orange">
          {steps.map((step, index) => (
            <Step key={index}>
              <StepIndicator>
                <StepStatus
                  complete={<StepIcon />}
                  incomplete={<StepNumber />}
                  active={<StepNumber />}
                />
              </StepIndicator>
              <Box flexShrink="0">
                <StepTitle>{step.title}</StepTitle>
              </Box>
              <StepSeparator />
            </Step>
          ))}
        </Stepper>

        {/* Form */}
        <Formik
          initialValues={initialValues}
          validationSchema={createValidationSchema()}
          onSubmit={handleSubmit}
        >
          {({ values, errors, touched, setFieldValue, isValid }) => (
            <Form>
              <VStack spacing={6} align="stretch">
                {/* Current Step Content */}
                <Card>
                  <CardHeader>
                    <Heading size="md" color="orange.500">
                      {applicationContext.sections[activeStep]?.title}
                    </Heading>
                  </CardHeader>
                  <CardBody>
                    <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                      {applicationContext.sections[activeStep]?.fields
                        .filter(fieldConfig => fieldConfig.visible)
                        .sort((a, b) => a.order - b.order)
                        .map(fieldConfig => 
                          renderField(fieldConfig.fieldKey, values, errors, touched, setFieldValue)
                        )}
                    </SimpleGrid>
                  </CardBody>
                </Card>

                {/* Agreement Checkbox (last step) */}
                {activeStep === steps.length - 1 && (
                  <Card>
                    <CardBody>
                      <FormControl isInvalid={!!(errors.akkoord && touched.akkoord)}>
                        <Field name="akkoord">
                          {({ field }: any) => (
                            <Checkbox {...field} isChecked={values.akkoord} colorScheme="orange">
                              Ik ga akkoord met de voorwaarden en het lidmaatschap van de H-DCN
                            </Checkbox>
                          )}
                        </Field>
                        <FormErrorMessage>{errors.akkoord as string}</FormErrorMessage>
                      </FormControl>
                    </CardBody>
                  </Card>
                )}

                {/* Navigation Buttons */}
                <HStack justify="space-between">
                  <HStack>
                    <Button
                      variant="outline"
                      onClick={onCancel}
                    >
                      Annuleren
                    </Button>
                    {activeStep > 0 && (
                      <Button
                        variant="outline"
                        onClick={() => setActiveStep(activeStep - 1)}
                      >
                        Vorige
                      </Button>
                    )}
                  </HStack>
                  
                  <HStack>
                    {activeStep < steps.length - 1 ? (
                      <Button
                        colorScheme="orange"
                        onClick={() => setActiveStep(activeStep + 1)}
                      >
                        Volgende
                      </Button>
                    ) : (
                      <Button
                        type="submit"
                        colorScheme="orange"
                        isLoading={isSubmitting}
                        isDisabled={!isValid || !values.akkoord}
                      >
                        Aanmelding Verzenden
                      </Button>
                    )}
                  </HStack>
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