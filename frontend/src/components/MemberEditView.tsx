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

  // Create validation schema from field definitions
  const createValidationSchema = () => {
    const schema: any = {};
    
    memberContext.sections.forEach(section => {
      section.fields.forEach(fieldConfig => {
        const field = MEMBER_FIELDS[fieldConfig.fieldKey];
        if (field && field.validation && canEditField(field, userRole, member)) {
          field.validation.forEach(rule => {
            if (rule.type === 'required') {
              schema[field.key] = Yup.string().required(rule.message || `${field.label} is verplicht`);
            } else if (rule.type === 'email') {
              schema[field.key] = Yup.string().email(rule.message || 'Ongeldig emailadres');
            } else if (rule.type === 'min_length') {
              schema[field.key] = Yup.string().min(rule.value, rule.message);
            } else if (rule.type === 'iban') {
              schema[field.key] = Yup.string().matches(
                /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$/,
                rule.message || 'Ongeldig IBAN nummer'
              );
            }
          });
        }
      });
    });

    return Yup.object().shape(schema);
  };

  const handleSave = async (values: any) => {
    setIsSubmitting(true);
    try {
      await onSave({
        ...values,
        updated_at: new Date().toISOString()
      });
      
      onClose();
      toast({
        title: 'Lid bijgewerkt',
        description: 'De lidgegevens zijn succesvol bijgewerkt.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Fout bij opslaan',
        description: 'Er is een fout opgetreden. Probeer het opnieuw.',
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

    const value = values[fieldKey];
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
      <FormControl key={fieldKey} isInvalid={!!(error && isTouched)}>
        <FormLabel>
          <HStack>
            <Text>{field.label}</Text>
            {!canEdit && (
              <Badge colorScheme="gray" size="sm">Alleen lezen</Badge>
            )}
            {field.required && (
              <Text color="red.500">*</Text>
            )}
          </HStack>
        </FormLabel>
        
        {canEdit ? (
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
                return <Textarea {...formikField} placeholder={field.placeholder} rows={3} />;
              } else if (field.inputType === 'date') {
                return <Input {...formikField} type="date" />;
              } else if (field.inputType === 'number') {
                return <Input {...formikField} type="number" placeholder={field.placeholder} />;
              } else if (field.inputType === 'email') {
                return <Input {...formikField} type="email" placeholder={field.placeholder} />;
              } else if (field.inputType === 'tel') {
                return <Input {...formikField} type="tel" placeholder={field.placeholder} />;
              } else if (field.inputType === 'iban') {
                return <Input {...formikField} type="text" placeholder={field.placeholder} fontFamily="mono" />;
              } else {
                return <Input {...formikField} type="text" placeholder={field.placeholder} />;
              }
            }}
          </Field>
        ) : (
          <Box p={3} bg="gray.50" borderRadius="md" border="1px" borderColor="gray.200">
            <Text fontWeight="medium">
              {field.key === 'status' ? (
                <Badge colorScheme={getStatusColor(value)}>
                  {value || '-'}
                </Badge>
              ) : field.key === 'lidmaatschap' ? (
                <Badge colorScheme={getMembershipColor(value)}>
                  {value || '-'}
                </Badge>
              ) : (
                renderFieldValue(field, value) || '-'
              )}
            </Text>
          </Box>
        )}
        
        {field.helpText && (
          <Text fontSize="sm" color="gray.600" mt={1}>{field.helpText}</Text>
        )}
        <FormErrorMessage>{error as string}</FormErrorMessage>
      </FormControl>
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
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
        {visibleFields.map((fieldConfig: any) => 
          renderField(fieldConfig.fieldKey, values, errors, touched, setFieldValue)
        )}
      </SimpleGrid>
    );

    if (section.collapsible) {
      return (
        <AccordionItem key={section.name}>
          <AccordionButton>
            <Box flex="1" textAlign="left">
              <Text fontWeight="semibold" color="orange.500">
                {section.title}
              </Text>
            </Box>
            <AccordionIcon />
          </AccordionButton>
          <AccordionPanel pb={4}>
            {content}
          </AccordionPanel>
        </AccordionItem>
      );
    }

    return (
      <Card key={section.name}>
        <CardHeader>
          <Text fontWeight="semibold" color="orange.500" fontSize="lg">
            {section.title}
          </Text>
        </CardHeader>
        <CardBody>
          {content}
        </CardBody>
      </Card>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <Flex align="center">
            <VStack align="start" spacing={1}>
              <HStack>
                <Text>
                  Bewerken: {member.voornaam} {member.tussenvoegsel} {member.achternaam}
                </Text>
                {member.lidnummer && (
                  <Badge colorScheme="blue">#{member.lidnummer}</Badge>
                )}
              </HStack>
              <Text fontSize="sm" color="gray.600">
                Wijzig de lidgegevens en klik op opslaan
              </Text>
            </VStack>
            <Spacer />
            <Badge colorScheme={getStatusColor(member.status)} size="lg">
              {member.status || 'Onbekend'}
            </Badge>
          </Flex>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <Formik
            initialValues={member}
            validationSchema={createValidationSchema()}
            onSubmit={handleSave}
            enableReinitialize
          >
            {({ values, errors, touched, setFieldValue, isValid }) => (
              <Form>
                <VStack spacing={6} align="stretch">
                  {/* Warning for sensitive data */}
                  <Alert status="warning">
                    <AlertIcon />
                    <VStack align="start" spacing={1}>
                      <Text fontWeight="semibold">Let op bij het bewerken van lidgegevens</Text>
                      <Text fontSize="sm">
                        Controleer alle wijzigingen zorgvuldig voordat u opslaat. Sommige velden zijn alleen-lezen vanwege uw gebruikersrechten.
                      </Text>
                    </VStack>
                  </Alert>

                  {/* Non-collapsible sections */}
                  {memberContext.sections
                    .filter(section => !section.collapsible)
                    .sort((a, b) => a.order - b.order)
                    .map(section => renderSection(section, values, errors, touched, setFieldValue))}

                  {/* Collapsible sections in accordion */}
                  <Accordion allowMultiple defaultIndex={[]}>
                    {memberContext.sections
                      .filter(section => section.collapsible)
                      .sort((a, b) => a.order - b.order)
                      .map(section => renderSection(section, values, errors, touched, setFieldValue))}
                  </Accordion>

                  {/* Save/Cancel Buttons */}
                  <Card>
                    <CardBody>
                      <HStack justify="center" spacing={4}>
                        <Button
                          variant="outline"
                          leftIcon={<CloseIcon />}
                          onClick={onClose}
                          isDisabled={isSubmitting}
                        >
                          Annuleren
                        </Button>
                        <Button
                          type="submit"
                          colorScheme="orange"
                          leftIcon={<CheckIcon />}
                          isLoading={isSubmitting}
                          isDisabled={!isValid}
                          size="lg"
                        >
                          Wijzigingen Opslaan
                        </Button>
                      </HStack>
                    </CardBody>
                  </Card>
                </VStack>
              </Form>
            )}
          </Formik>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default MemberEditView;