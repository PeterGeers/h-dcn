/**
 * Member Edit View - Using Field Registry System
 * 
 * Editable member modal for administrators using memberView context with edit permissions
 */

import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  VStack,
  HStack,
  Text,
  Badge,
  Card,
  CardHeader,
  CardBody,
  SimpleGrid,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Input,
  Select,
  Textarea,
  Flex,
  Spacer,
  useToast,
  Alert,
  AlertIcon,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Box
} from '@chakra-ui/react';
import { CheckIcon, CloseIcon } from '@chakra-ui/icons';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { MEMBER_MODAL_CONTEXTS, MEMBER_FIELDS, HDCNGroup } from '../config/memberFields';
import { canViewField, canEditField } from '../utils/fieldResolver';
import { renderFieldValue } from '../utils/fieldRenderers';

interface MemberEditViewProps {
  isOpen: boolean;
  onClose: () => void;
  member: any;
  userRole: HDCNGroup;
  userRegion?: string;
  onSave: (data: any) => Promise<void>;
}

const MemberEditView: React.FC<MemberEditViewProps> = ({
  isOpen,
  onClose,
  member,
  userRole,
  userRegion,
  onSave
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  // Get member view context
  const memberContext = MEMBER_MODAL_CONTEXTS.memberView;

  // Evaluate validation condition
  const evaluateValidationCondition = (condition: any, memberData: any): boolean => {
    const fieldValue = memberData[condition.field];
    
    switch (condition.operator) {
      case 'equals':
        return fieldValue === condition.value;
      case 'not_equals':
        return fieldValue !== condition.value;
      case 'exists':
        return fieldValue !== undefined && fieldValue !== null && fieldValue !== '';
      case 'not_exists':
        return fieldValue === undefined || fieldValue === null || fieldValue === '';
      case 'age_less_than':
        if (condition.field === 'geboortedatum' && fieldValue) {
          const birthDate = new Date(fieldValue);
          const today = new Date();
          const age = today.getFullYear() - birthDate.getFullYear();
          const monthDiff = today.getMonth() - birthDate.getMonth();
          
          if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
            return (age - 1) < condition.value;
          }
          return age < condition.value;
        }
        return false;
      default:
        return true;
    }
  };

  // Create validation schema from field definitions
  const createValidationSchema = () => {
    const schema: any = {};
    
    memberContext.sections.forEach(section => {
      section.fields.forEach(fieldConfig => {
        const field = MEMBER_FIELDS[fieldConfig.fieldKey];
        if (field && field.validation && canEditField(field, userRole, member) && !field.computed) {
          let fieldSchema: any;
          
          // Use the field's actual database key for validation (respecting the mapping)
          const validationKey = field.key || fieldConfig.fieldKey;
          
          // Start with appropriate base schema based on data type
          if (field.dataType === 'number') {
            fieldSchema = Yup.number().nullable().transform((value, originalValue) => {
              return originalValue === '' ? null : value;
            });
          } else {
            fieldSchema = Yup.string().nullable();
          }
          
          field.validation.forEach(rule => {
            // Check if this validation rule has a condition
            if (rule.condition) {
              // Evaluate the condition against current member data
              const conditionMet = evaluateValidationCondition(rule.condition, member);
              if (!conditionMet) {
                return; // Skip this validation rule
              }
            }
            
            if (rule.type === 'required') {
              if (field.dataType === 'number') {
                fieldSchema = fieldSchema.required(rule.message || `${field.label} is verplicht`);
              } else {
                fieldSchema = fieldSchema.required(rule.message || `${field.label} is verplicht`);
              }
            } else if (rule.type === 'email') {
              // Make email validation optional if field is empty
              fieldSchema = Yup.string().nullable().test(
                'email',
                rule.message || 'Ongeldig emailadres',
                (value) => !value || Yup.string().email().isValidSync(value)
              );
            } else if (rule.type === 'min_length') {
              fieldSchema = fieldSchema.min(rule.value, rule.message);
            } else if (rule.type === 'min') {
              // For number fields
              fieldSchema = fieldSchema.min(rule.value, rule.message);
            } else if (rule.type === 'max') {
              // For number fields
              fieldSchema = fieldSchema.max(rule.value, rule.message);
            } else if (rule.type === 'iban') {
              // Make IBAN validation optional if field is empty
              fieldSchema = Yup.string().nullable().test(
                'iban',
                rule.message || 'Ongeldig IBAN nummer',
                (value) => !value || /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$/.test(value)
              );
            }
          });
          
          schema[validationKey] = fieldSchema;
        }
      });
    });

    return Yup.object().shape(schema);
  };

  const handleSave = async (values: any) => {
    setIsSubmitting(true);
    try {
      console.log('Saving member data:', values);
      await onSave({
        ...values,
        updated_at: new Date().toISOString()
      });
      
      onClose();
    } catch (error: any) {
      console.error('Error saving member:', error);
      toast({
        title: 'Fout bij opslaan',
        description: error?.message || 'Er is een fout opgetreden. Probeer het opnieuw.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Actief': return 'green';
      case 'Aangemeld': return 'yellow';
      case 'Opgezegd': return 'red';
      case 'Geschorst': return 'red';
      case 'wachtRegio': return 'orange';
      default: return 'gray';
    }
  };

  const getMembershipColor = (membership: string) => {
    switch (membership) {
      case 'Gewoon lid': return 'blue';
      case 'Gezins lid': return 'purple';
      case 'Erelid': return 'gold';
      case 'Donateur': return 'teal';
      case 'Gezins donateur': return 'teal';
      case 'Sponsor': return 'orange';
      default: return 'gray';
    }
  };

  const renderField = (fieldKey: string, values: any, errors: any, touched: any, setFieldValue: any) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (!field) return null;

    const canView = canViewField(field, userRole, member);
    const canEdit = canEditField(field, userRole, member);
    
    if (!canView) return null;

    // Use the field's actual key for data access, fallback to fieldKey
    const dataKey = field.key || fieldKey;
    let value = values[dataKey] || values[fieldKey];
    
    // Handle computed fields
    if (field.computed && field.computeFrom && field.computeFunction) {
      if (field.computeFunction === 'yearsDifference') {
        const sourceValue = values[field.computeFrom] || values[MEMBER_FIELDS[field.computeFrom]?.key];
        if (sourceValue) {
          const startDate = new Date(sourceValue);
          const today = new Date();
          const years = today.getFullYear() - startDate.getFullYear();
          const monthDiff = today.getMonth() - startDate.getMonth();
          
          if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < startDate.getDate())) {
            value = years - 1;
          } else {
            value = years;
          }
        }
      } else if (field.computeFunction === 'year') {
        const sourceValue = values[field.computeFrom] || values[MEMBER_FIELDS[field.computeFrom]?.key];
        if (sourceValue) {
          value = new Date(sourceValue).getFullYear();
        }
      }
    }
    
    const error = errors[dataKey] || errors[fieldKey];
    const isTouched = touched[dataKey] || touched[fieldKey];

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
        <FormControl isInvalid={!!(error && isTouched)}>
          <FormLabel mb={0} color="gray.700" fontWeight="semibold" fontSize="sm">
            {field.label}
          </FormLabel>
          
          {canEdit ? (
            <Field name={dataKey}>
              {({ field: formikField }: any) => {
                if (field.inputType === 'select' && field.enumOptions) {
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
                      {field.enumOptions.map(option => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </Select>
                  );
                } else if (field.inputType === 'textarea') {
                  return (
                    <Textarea 
                      {...formikField} 
                      placeholder={field.placeholder} 
                      rows={3}
                      bg="white"
                      borderColor="gray.300"
                      _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
                      _hover={{ borderColor: "orange.400" }}
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
                } else if (field.inputType === 'iban') {
                  return (
                    <Input 
                      {...formikField} 
                      type="text" 
                      placeholder={field.placeholder} 
                      fontFamily="mono"
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
          ) : (
            <Input
              value={field.key === 'status' ? (
                value || '-'
              ) : field.key === 'lidmaatschap' ? (
                value || '-'
              ) : (
                renderFieldValue(field, value) || '-'
              )}
              bg="gray.200"
              borderColor="gray.400"
              color="gray.700"
              cursor="default"
              isReadOnly
              size="sm"
              fontSize="sm"
              minH="32px"
              _hover={{ bg: "gray.200" }}
            />
          )}
          
          {error && isTouched && (
            <FormErrorMessage>{error as string}</FormErrorMessage>
          )}
        </FormControl>
      </Box>
    );
  };

  const renderSection = (section: any, values: any, errors: any, touched: any, setFieldValue: any) => {
    // Check if user can view this section
    if (!section.permissions?.view.includes(userRole)) {
      return null;
    }

    // Check if section should be shown based on conditions
    if (section.showWhen) {
      const shouldShow = section.showWhen.some((condition: any) => {
        if (condition.operator === 'equals') {
          return values[condition.field] === condition.value;
        }
        return true;
      });
      if (!shouldShow) return null;
    }

    const visibleFields = section.fields
      .filter((fieldConfig: any) => fieldConfig.visible)
      .filter((fieldConfig: any) => {
        const field = MEMBER_FIELDS[fieldConfig.fieldKey];
        return field && canViewField(field, userRole, member);
      })
      .sort((a: any, b: any) => a.order - b.order);

    if (visibleFields.length === 0) return null;

    const content = (
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>
        {visibleFields.map((fieldConfig: any) => 
          renderField(fieldConfig.fieldKey, values, errors, touched, setFieldValue)
        )}
      </SimpleGrid>
    );

    if (section.collapsible) {
      return (
        <AccordionItem 
          key={section.name} 
          border="1px" 
          borderColor="orange.400" 
          borderRadius="lg" 
          bg="gray.800"
          mb={4}
          _last={{ mb: 0 }}
        >
          <AccordionButton 
            bg="gray.700 !important" 
            borderRadius="lg lg 0 0" 
            py={3}
            px={4}
            _hover={{ bg: "gray.600 !important" }}
            _expanded={{ bg: "gray.700 !important", borderRadius: "lg lg 0 0" }}
            _focus={{ boxShadow: "none" }}
          >
            <Box flex="1" textAlign="left">
              <Text fontWeight="semibold" color="orange.300" fontSize="sm">
                {section.title}
              </Text>
            </Box>
            <AccordionIcon color="orange.300" />
          </AccordionButton>
          <AccordionPanel 
            pb={4} 
            pt={4} 
            px={4}
            bg="orange.300 !important" 
            borderRadius="0 0 lg lg"
            color="gray.700"
          >
            {content}
          </AccordionPanel>
        </AccordionItem>
      );
    }

    return (
      <Card key={section.name} bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
        <CardHeader bg="gray.700" borderRadius="lg lg 0 0" py={1}>
          <Text fontWeight="semibold" color="orange.300" fontSize="sm" textAlign="left">
            {section.title}
          </Text>
        </CardHeader>
        <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
          {content}
        </CardBody>
      </Card>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="gray.800" borderColor="orange.400" border="1px">
        <ModalHeader bg="gray.700" color="orange.300">
          <Flex align="center">
            <VStack align="start" spacing={1}>
              <HStack>
                <Text>
                  {member.voornaam} {member.tussenvoegsel} {member.achternaam}
                </Text>
                {member.lidnummer && (
                  <Badge colorScheme="blue">#{member.lidnummer}</Badge>
                )}
              </HStack>
              <Text fontSize="sm" color="gray.300">
                Lidgegevens
              </Text>
            </VStack>
            <Spacer />
            <HStack spacing={3}>
              <Badge colorScheme={getStatusColor(member.status)} size="lg">
                {member.status || 'Onbekend'}
              </Badge>
            </HStack>
          </Flex>
        </ModalHeader>
        <ModalCloseButton color="orange.300" />
        
        <ModalBody bg="black" p={6}>
          <Formik
            initialValues={member}
            validationSchema={createValidationSchema()}
            onSubmit={handleSave}
            enableReinitialize
          >
            {({ values, errors, touched, setFieldValue, isValid }) => {
              // Check if user can edit ANY fields
              const canEditAnyField = memberContext.sections.some(section =>
                section.fields?.some(fieldConfig => {
                  const field = MEMBER_FIELDS[fieldConfig.fieldKey];
                  return field && canEditField(field, userRole, member);
                })
              );

              return (
              <Form id="member-edit-form">
                <VStack spacing={6} align="stretch">
                  {/* Action buttons at top right - only show if user can edit */}
                  {canEditAnyField && (
                    <Flex justify="flex-end">
                      <HStack spacing={3}>
                        <Button
                          variant="outline"
                          size="sm"
                          leftIcon={<CloseIcon />}
                          onClick={onClose}
                          isDisabled={isSubmitting}
                          color="gray.300"
                          borderColor="gray.500"
                          _hover={{ borderColor: "gray.400", color: "white" }}
                        >
                          Annuleren
                        </Button>
                        <Button
                          type="submit"
                          colorScheme="orange"
                          size="sm"
                          leftIcon={<CheckIcon />}
                          isLoading={isSubmitting}
                          isDisabled={!isValid}
                          loadingText="Opslaan..."
                        >
                          Opslaan
                        </Button>
                      </HStack>
                    </Flex>
                  )}

                  {/* Validation error message - only show if user can edit */}
                  {canEditAnyField && !isValid && Object.keys(errors).length > 0 && (
                    <Alert status="error" bg="red.900" color="white" borderRadius="lg">
                      <AlertIcon />
                      <VStack align="start" spacing={1}>
                        <Text fontSize="sm" fontWeight="bold">
                          Corrigeer de volgende fouten:
                        </Text>
                        {Object.entries(errors).map(([field, error]) => {
                          const fieldDef = Object.values(MEMBER_FIELDS).find(f => f.key === field || Object.keys(MEMBER_FIELDS).find(k => k === field));
                          const fieldLabel = fieldDef?.label || field;
                          return (
                            <Text key={field} fontSize="sm" color="red.200">
                              • {fieldLabel}: {error as string}
                            </Text>
                          );
                        })}
                      </VStack>
                    </Alert>
                  )}

                  {/* Non-collapsible sections */}
                  {memberContext.sections
                    .filter(section => !section.collapsible)
                    .sort((a, b) => a.order - b.order)
                    .map(section => renderSection(section, values, errors, touched, setFieldValue))}

                  {/* Collapsible sections in accordion */}
                  <Accordion allowMultiple defaultIndex={[0, 1, 2, 3, 4, 5]} bg="transparent">
                    {memberContext.sections
                      .filter(section => section.collapsible)
                      .sort((a, b) => a.order - b.order)
                      .map(section => renderSection(section, values, errors, touched, setFieldValue))}
                  </Accordion>

                  {/* Debug Information (only in development) */}
                  {process.env.NODE_ENV === 'development' && (
                    <Card bg="gray.900" borderColor="blue.400" border="1px" borderRadius="lg">
                      <CardHeader bg="blue.800" borderRadius="lg lg 0 0" py={2}>
                        <Text fontWeight="semibold" color="blue.300" fontSize="sm">
                          Debug Info (Development Only)
                        </Text>
                      </CardHeader>
                      <CardBody pt={2} pb={2} bg="blue.900" borderRadius="0 0 lg lg">
                        <VStack align="start" spacing={1}>
                          <Text fontSize="xs" color="blue.200">
                            Form Valid: {isValid ? '✅ Ja' : '❌ Nee'}
                          </Text>
                          <Text fontSize="xs" color="blue.200">
                            Submitting: {isSubmitting ? '⏳ Ja' : '✅ Nee'}
                          </Text>
                          <Text fontSize="xs" color="blue.200">
                            Error Count: {Object.keys(errors).length}
                          </Text>
                          {Object.keys(errors).length > 0 && (
                            <Box>
                              <Text fontSize="xs" color="red.300" fontWeight="bold">
                                Validation Errors:
                              </Text>
                              {Object.entries(errors).map(([field, error]) => {
                                const fieldDef = Object.values(MEMBER_FIELDS).find(f => f.key === field) || 
                                                Object.entries(MEMBER_FIELDS).find(([k, f]) => k === field)?.[1];
                                const fieldLabel = fieldDef?.label || field;
                                return (
                                  <Text key={field} fontSize="xs" color="red.300">
                                    {field} ({fieldLabel}): {error as string}
                                  </Text>
                                );
                              })}
                            </Box>
                          )}
                          <Text fontSize="xs" color="blue.200">
                            Form Values Keys: {Object.keys(values).length} fields
                          </Text>
                          <Text fontSize="xs" color="blue.200">
                            Validation Schema Keys: {Object.keys(createValidationSchema().fields).length} rules
                          </Text>
                        </VStack>
                      </CardBody>
                    </Card>
                  )}
                </VStack>
              </Form>
              );
            }}
          </Formik>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default MemberEditView;