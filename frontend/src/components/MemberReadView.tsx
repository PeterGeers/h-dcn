/**
 * Member Read View - Using Field Registry System
 * 
 * Read-only member view modal for administrators using memberView context
 */

import React from 'react';
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
  Heading,
  Text,
  Badge,
  Card,
  CardHeader,
  CardBody,
  SimpleGrid,
  Divider,
  Flex,
  Spacer,
  Icon,
  Box,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText
} from '@chakra-ui/react';
import { EditIcon, InfoIcon, CalendarIcon, EmailIcon, PhoneIcon } from '@chakra-ui/icons';
import { MEMBER_MODAL_CONTEXTS, MEMBER_FIELDS, HDCNGroup } from '../config/memberFields';
import { canViewField } from '../utils/fieldResolver';
import { renderFieldValue } from '../utils/fieldRenderers';

interface MemberReadViewProps {
  isOpen: boolean;
  onClose: () => void;
  member: any;
  userRole: HDCNGroup;
  userRegion?: string;
  onEdit?: () => void;
}

const MemberReadView: React.FC<MemberReadViewProps> = ({
  isOpen,
  onClose,
  member,
  userRole,
  userRegion,
  onEdit
}) => {
  // Get member view context
  const memberContext = MEMBER_MODAL_CONTEXTS.memberView;

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

  const renderFieldValue = (field: any, value: any) => {
    if (!value) return '-';
    
    if (field.inputType === 'date' && value) {
      return new Date(value).toLocaleDateString('nl-NL');
    }
    
    if (field.key === 'bankrekeningnummer' && value) {
      // Show full IBAN for admins
      return value;
    }
    
    if (field.key === 'geboortedatum' && value) {
      const birthDate = new Date(value);
      const age = new Date().getFullYear() - birthDate.getFullYear();
      return `${birthDate.toLocaleDateString('nl-NL')} (${age} jaar)`;
    }
    
    return value;
  };

  const renderField = (fieldKey: string) => {
    const field = MEMBER_FIELDS[fieldKey];
    if (!field) return null;

    const canView = canViewField(field, userRole, member);
    if (!canView) return null;

    const value = member[fieldKey];

    // Check conditional visibility
    if (field.showWhen) {
      const shouldShow = field.showWhen.some(condition => {
        if (condition.operator === 'equals') {
          return member[condition.field] === condition.value;
        }
        if (condition.operator === 'age_less_than') {
          const birthDate = new Date(member[condition.field]);
          const age = new Date().getFullYear() - birthDate.getFullYear();
          return age < condition.value;
        }
        return true;
      });
      if (!shouldShow) return null;
    }

    return (
      <Box key={fieldKey}>
        <Text fontSize="sm" color="gray.600" fontWeight="semibold">
          {field.label}
        </Text>
        <Text fontSize="md" mt={1}>
          {field.key === 'status' ? (
            <Badge colorScheme={getStatusColor(value)} size="sm">
              {renderFieldValue(field, value)}
            </Badge>
          ) : field.key === 'lidmaatschap' ? (
            <Badge colorScheme={getMembershipColor(value)} size="sm">
              {renderFieldValue(field, value)}
            </Badge>
          ) : (
            renderFieldValue(field, value)
          )}
        </Text>
        {field.helpText && (
          <Text fontSize="xs" color="gray.500" mt={1}>
            {field.helpText}
          </Text>
        )}
      </Box>
    );
  };

  const renderSection = (section: any) => {
    // Check if user can view this section
    if (!section.permissions?.view.includes(userRole)) {
      return null;
    }

    // Check if section should be shown based on conditions
    if (section.showWhen) {
      const shouldShow = section.showWhen.some((condition: any) => {
        if (condition.operator === 'equals') {
          return member[condition.field] === condition.value;
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
          renderField(fieldConfig.fieldKey)
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
          <Heading size="md" color="orange.500">
            {section.title}
          </Heading>
        </CardHeader>
        <CardBody>
          {content}
        </CardBody>
      </Card>
    );
  };

  // Calculate member statistics
  const memberAge = member.geboortedatum ? 
    new Date().getFullYear() - new Date(member.geboortedatum).getFullYear() : null;
  
  const memberSince = member.tijdstempel ? 
    new Date(member.tijdstempel).getFullYear() : null;
  
  const yearsAsMember = memberSince ? 
    new Date().getFullYear() - memberSince : null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
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
              <HStack spacing={4} fontSize="sm" color="gray.600">
                {member.email && (
                  <HStack spacing={1}>
                    <EmailIcon />
                    <Text>{member.email}</Text>
                  </HStack>
                )}
                {member.telefoon && (
                  <HStack spacing={1}>
                    <PhoneIcon />
                    <Text>{member.telefoon}</Text>
                  </HStack>
                )}
                {member.regio && (
                  <Text>Regio: {member.regio}</Text>
                )}
              </HStack>
            </VStack>
            <Spacer />
            <VStack align="end" spacing={2}>
              <Badge colorScheme={getStatusColor(member.status)} size="lg">
                {member.status || 'Onbekend'}
              </Badge>
              {member.lidmaatschap && (
                <Badge colorScheme={getMembershipColor(member.lidmaatschap)}>
                  {member.lidmaatschap}
                </Badge>
              )}
            </VStack>
          </Flex>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <VStack spacing={6} align="stretch">
            {/* Quick Stats */}
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
              {memberAge && (
                <Stat>
                  <StatLabel>Leeftijd</StatLabel>
                  <StatNumber>{memberAge}</StatNumber>
                  <StatHelpText>jaar</StatHelpText>
                </Stat>
              )}
              {yearsAsMember && (
                <Stat>
                  <StatLabel>Lid sinds</StatLabel>
                  <StatNumber>{yearsAsMember}</StatNumber>
                  <StatHelpText>jaar</StatHelpText>
                </Stat>
              )}
              {member.motormerk && (
                <Stat>
                  <StatLabel>Motor</StatLabel>
                  <StatNumber fontSize="md">{member.motormerk}</StatNumber>
                  <StatHelpText>{member.motortype}</StatHelpText>
                </Stat>
              )}
              {member.bouwjaar && (
                <Stat>
                  <StatLabel>Bouwjaar</StatLabel>
                  <StatNumber>{member.bouwjaar}</StatNumber>
                  <StatHelpText>motor</StatHelpText>
                </Stat>
              )}
            </SimpleGrid>

            <Divider />

            {/* Sections */}
            <VStack spacing={4} align="stretch">
              {/* Non-collapsible sections */}
              {memberContext.sections
                .filter(section => !section.collapsible)
                .sort((a, b) => a.order - b.order)
                .map(section => renderSection(section))}

              {/* Collapsible sections in accordion */}
              <Accordion allowMultiple>
                {memberContext.sections
                  .filter(section => section.collapsible)
                  .sort((a, b) => a.order - b.order)
                  .map(section => renderSection(section))}
              </Accordion>
            </VStack>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            <Button variant="outline" onClick={onClose}>
              Sluiten
            </Button>
            {onEdit && (
              <Button 
                colorScheme="orange" 
                leftIcon={<EditIcon />}
                onClick={onEdit}
              >
                Bewerken
              </Button>
            )}
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default MemberReadView;