/**
 * Member Self-Service View - Using Field Registry System
 * 
 * Shows member their own data with editable/non-editable fields based on selfService permissions
 * Follows look-and-feel guidelines with visual field state indicators
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
  Icon,
  Flex,
  Spacer,
  Collapse,
  Tooltip
} from '@chakra-ui/react';
import { CheckIcon, ChevronDownIcon, ChevronUpIcon, EditIcon } from '@chakra-ui/icons';
import { Formik, Form, Field } from 'formik';
import { MEMBER_MODAL_CONTEXTS, MEMBER_FIELDS, getVisibleFields } from '../config/memberFields';
import { resolveFieldsForContext, canViewField, canEditField } from '../utils/fieldResolver';
import { renderFieldValue } from '../utils/fieldRenderers';

interface MemberSelfServiceViewProps {
  member: any;
  onUpdate: (data: any) => Promise<void>;
}

const MemberSelfServiceView: React.FC<MemberSelfServiceViewProps> = ({ member, onUpdate }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    membership: true,    // Start with membership as requested
    personal: true,
    address: true,
    motor: false,
    financial: false,
    administrative: false
  });
  const toast = useToast();

  // Debug: Log member data to see what fields are available
  // console.log('Member data in MemberSelfServiceView:', member);

  // Get member view context and resolve fields for hdcnLeden role
  const memberContext = MEMBER_MODAL_CONTEXTS.memberView;
  const userRole = 'hdcnLeden';

  const handleSave = async (values: any) => {
    setIsSubmitting(true);
    try {
      await onUpdate({
        ...values,
        updated_at: new Date().toISOString()
      });
      
      setHasChanges(false);
      toast({
        title: 'Gegevens bijgewerkt',
        description: 'Uw gegevens zijn succesvol bijgewerkt.',
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

  const toggleSection = (sectionName: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  const renderField = (fieldKey: string, values: any, errors: any, touched: any, setFieldValue: any) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (!field) return null;

    const canView = canViewField(field, userRole, member);
    // For self-service, check if field has selfService: true
    const canSelfEdit = field.permissions?.selfService === true;
    
    if (!canView) return null;

    // Handle computed fields and field mappings
    let value = values[fieldKey] || member[fieldKey];
    
    // Debug logging for all fields
    // console.log(`Field ${fieldKey}: initial value = "${value}", field.key = "${field.key}"`);
    
    // Special handling for ingangsdatum field which maps to tijdstempel
    if (fieldKey === 'ingangsdatum' && field.key === 'tijdstempel') {
      value = values['tijdstempel'] || member['tijdstempel'];
      // console.log(`Field mapping for ${fieldKey}: mapped to tijdstempel = "${value}"`);
    }
    
    if (field.computed && field.computeFrom && field.computeFunction) {
      const sourceField = Array.isArray(field.computeFrom) ? field.computeFrom[0] : field.computeFrom;
      let sourceValue = values[sourceField] || member[sourceField];
      
      // If computeFrom is 'ingangsdatum' but we need to get from 'tijdstempel'
      if (sourceField === 'ingangsdatum') {
        sourceValue = values['tijdstempel'] || member['tijdstempel'];
      }
      if (sourceValue && field.computeFunction === 'yearsDifference') {
        let sourceDate;
        
        // Handle different date formats
        if (typeof sourceValue === 'string') {
          // Try to parse Dutch date format like "26 september 2009"
          if (sourceValue.includes('september') || sourceValue.includes('januari') || sourceValue.includes('februari') || 
              sourceValue.includes('maart') || sourceValue.includes('april') || sourceValue.includes('mei') ||
              sourceValue.includes('juni') || sourceValue.includes('juli') || sourceValue.includes('augustus') ||
              sourceValue.includes('oktober') || sourceValue.includes('november') || sourceValue.includes('december')) {
            const monthMap = {
              'januari': '01', 'februari': '02', 'maart': '03', 'april': '04',
              'mei': '05', 'juni': '06', 'juli': '07', 'augustus': '08',
              'september': '09', 'oktober': '10', 'november': '11', 'december': '12'
            };
            
            const parts = sourceValue.split(' ');
            if (parts.length === 3) {
              const day = parts[0].padStart(2, '0');
              const month = monthMap[parts[1].toLowerCase()];
              const year = parts[2];
              if (month) {
                sourceDate = new Date(`${year}-${month}-${day}`);
              }
            }
          } else {
            // Try standard date parsing
            sourceDate = new Date(sourceValue);
          }
        } else {
          sourceDate = new Date(sourceValue);
        }
        
        if (sourceDate && !isNaN(sourceDate.getTime())) {
          const currentDate = new Date();
          const yearsDiff = currentDate.getFullYear() - sourceDate.getFullYear();
          const monthDiff = currentDate.getMonth() - sourceDate.getMonth();
          value = monthDiff < 0 || (monthDiff === 0 && currentDate.getDate() < sourceDate.getDate()) 
            ? yearsDiff - 1 
            : yearsDiff;
          // console.log(`Computed ${fieldKey}: sourceValue="${sourceValue}", sourceDate=${sourceDate}, years=${value}`);
        } else {
          // console.log(`Failed to parse date for ${fieldKey}: sourceValue="${sourceValue}"`);
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

    // Show all fields that user can view (including empty ones)
    
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
            {canSelfEdit ? (
              <Tooltip label={field.helpText || "Dit veld kunt u zelf bewerken"}>
                <Text cursor="help">{field.label}</Text>
              </Tooltip>
            ) : (
              <Tooltip label={field.helpText || "Dit veld is alleen-lezen"}>
                <Text cursor="help">{field.label}</Text>
              </Tooltip>
            )}
          </FormLabel>
          
          {canSelfEdit ? (
            <Field name={fieldKey}>
              {({ field: formikField }: any) => {
                const commonProps = {
                  ...formikField,
                  placeholder: field.placeholder,
                  bg: "white",
                  borderColor: error && isTouched ? "red.500" : "gray.300",
                  _hover: { borderColor: "orange.400" },
                  _focus: { borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" },
                  _placeholder: { color: "gray.400" },
                  cursor: "text",
                  size: "sm",
                  fontSize: "sm",
                  onChange: (e: any) => {
                    formikField.onChange(e);
                    setHasChanges(true);
                  }
                };

                if (field.inputType === 'select' && field.enumOptions) {
                  return (
                    <Select {...commonProps} cursor="pointer" size="sm">
                      <option value="">Selecteer...</option>
                      {field.enumOptions.map(option => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </Select>
                  );
                } else if (field.inputType === 'textarea') {
                  return <Textarea {...commonProps} rows={2} size="sm" />;
                } else if (field.inputType === 'date') {
                  return <Input {...commonProps} type="date" size="sm" />;
                } else if (field.inputType === 'number') {
                  return <Input {...commonProps} type="number" size="sm" />;
                } else if (field.inputType === 'email') {
                  return <Input {...commonProps} type="email" size="sm" />;
                } else if (field.inputType === 'tel') {
                  return <Input {...commonProps} type="tel" size="sm" />;
                } else if (field.inputType === 'iban') {
                  return <Input {...commonProps} type="text" size="sm" />;
                } else {
                  return <Input {...commonProps} type="text" size="sm" />;
                }
              }}
            </Field>
          ) : (
            <Box 
              p={2} 
              bg="gray.100" 
              borderRadius="md" 
              border="1px" 
              borderColor="gray.300" 
              minH="32px"
              cursor="default"
              display="flex"
              alignItems="center"
            >
              <Text color="gray.600" fontWeight="medium" fontSize="sm">
                {value !== null && value !== undefined && value !== '' 
                  ? (field.suffix ? `${value} ${field.suffix}` : renderFieldValue(field, value))
                  : '-'
                }
              </Text>
            </Box>
          )}
          
          <FormErrorMessage>{error as string}</FormErrorMessage>
        </FormControl>
      </Box>
    );
  };

  const renderSection = (section: any, values: any, errors: any, touched: any, setFieldValue: any) => {
    // console.log(`Rendering section: ${section.name}`, section);
    
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

    const visibleFields = getVisibleFields(section);
    // console.log(`Visible fields for ${section.name}:`, visibleFields.map(f => f.fieldKey));

    // Always show sections that user can view (even if empty)
    const isExpanded = expandedSections[section.name] ?? section.defaultExpanded ?? true;

    return (
      <Card key={section.name} mb={6} bg="gray.800" borderColor="orange.400" border="1px" borderRadius="lg">
        <CardHeader 
          bg="gray.700"
          cursor={section.collapsible ? "pointer" : "default"}
          onClick={section.collapsible ? () => toggleSection(section.name) : undefined}
          _hover={section.collapsible ? { bg: "gray.600" } : {}}
          py={1}
          borderRadius="lg lg 0 0"
        >
          <Flex align="center">
            <Heading size="sm" color="orange.300">
              {section.title}
            </Heading>
            <Spacer />
            {section.collapsible && (
              <Icon as={isExpanded ? ChevronUpIcon : ChevronDownIcon} color="orange.300" />
            )}
          </Flex>
        </CardHeader>
        <Collapse in={isExpanded}>
          <CardBody pt={4} pb={4} bg="orange.300" borderRadius="0 0 lg lg">
            <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>
              {visibleFields.map((fieldConfig: any) => 
                renderField(fieldConfig.fieldKey, values, errors, touched, setFieldValue)
              )}
            </SimpleGrid>
          </CardBody>
        </Collapse>
      </Card>
    );
  };

  return (
    <Box maxW="1200px" mx="auto" p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        {/* Form */}
        <Formik
          initialValues={member}
          onSubmit={handleSave}
          enableReinitialize
        >
          {({ values, errors, touched, isValid, setFieldValue }) => (
            <Form>
              <VStack spacing={0} align="stretch">
                {/* Render sections in specific order: membership first, then others, but exclude administrative */}
                {memberContext.sections
                  .filter(section => section.name !== 'administrative') // Hide administrative section
                  .sort((a, b) => {
                    // Put membership first, then sort by order
                    if (a.name === 'membership') return -1;
                    if (b.name === 'membership') return 1;
                    return a.order - b.order;
                  })
                  .map(section => renderSection(section, values, errors, touched, setFieldValue))}

                {/* Save Button - Only show if there are changes */}
                {hasChanges && (
                  <Box 
                    position="fixed" 
                    bottom={6} 
                    left="50%" 
                    transform="translateX(-50%)"
                    zIndex={9999}
                    bg="white"
                    p={3}
                    borderRadius="lg"
                    boxShadow="xl"
                    border="2px"
                    borderColor="orange.500"
                  >
                    <Button
                      type="submit"
                      colorScheme="orange"
                      isLoading={isSubmitting}
                      isDisabled={!isValid}
                      size="md"
                      _hover={{ bg: "orange.600" }}
                      boxShadow="md"
                      borderRadius="full"
                      p={3}
                    >
                      <EditIcon />
                    </Button>
                  </Box>
                )}
              </VStack>
            </Form>
          )}
        </Formik>
      </VStack>
    </Box>
  );
};

export default MemberSelfServiceView;