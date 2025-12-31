import React from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalCloseButton,
  VStack, HStack, Text, Badge, Divider, SimpleGrid, Box
} from '@chakra-ui/react';
import { Member } from '../../../types';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';
import { hasRegionalAccess } from '../../../utils/regionalMapping';

interface MemberDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  member: Member | null;
  user?: any; // Add user prop for permission checking
}

function MemberDetailModal({ isOpen, onClose, member, user }: MemberDetailModalProps) {
  if (!member) return null;

  const userRoles = getUserRoles(user || {});
  const isOwnRecord = member.email === user?.attributes?.email;

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'green';
      case 'inactive': return 'red';
      case 'pending': return 'yellow';
      default: return 'gray';
    }
  };

  const hasValue = (value: any) => value && value !== '' && value !== 'undefined' && value !== null;

  /**
   * Check if current user can view a specific field type based on their roles AND membership type restrictions
   */
  const canViewFieldType = (fieldType: 'personal' | 'address' | 'membership' | 'motor' | 'financial' | 'administrative'): boolean => {
    // Admin roles can view all fields
    if (userRoles.includes('hdcnAdmins') || 
        userRoles.includes('Members_CRUD_All') || 
        userRoles.includes('Members_Read_All')) {
      return true;
    }

    // Own record - members can view their personal, address, membership, and motor fields
    if (isOwnRecord && userRoles.includes('hdcnLeden')) {
      // PRESERVE EXISTING MEMBERSHIP TYPE RESTRICTIONS
      // Motor fields are only relevant for specific membership types
      if (fieldType === 'motor') {
        const membershipType = member?.lidmaatschap || member?.membership_type;
        const motorRequiredTypes = ['Gewoon lid', 'Gezins lid'];
        return motorRequiredTypes.includes(membershipType);
      }
      
      return ['personal', 'address', 'membership'].includes(fieldType);
    }

    // Financial fields - only specific roles can view
    if (fieldType === 'financial') {
      return userRoles.some(role => 
        role.includes('Treasurer') || 
        role.includes('Members_CRUD_All') ||
        role.includes('hdcnAdmins')
      );
    }

    // Administrative fields - only admin roles can view
    if (fieldType === 'administrative') {
      return userRoles.includes('hdcnAdmins') || 
             userRoles.includes('Members_CRUD_All') ||
             userRoles.includes('System_User_Management');
    }

    // Regional access - check if user has regional permissions for this member's region
    if (member.regio) {
      if (hasRegionalAccess(userRoles, member.regio)) {
        // Regional users can view personal, address, membership, motor fields
        // PRESERVE EXISTING MEMBERSHIP TYPE RESTRICTIONS for motor fields
        if (fieldType === 'motor') {
          const membershipType = member?.lidmaatschap || member?.membership_type;
          const motorRequiredTypes = ['Gewoon lid', 'Gezins lid'];
          return motorRequiredTypes.includes(membershipType);
        }
        
        return ['personal', 'address', 'membership'].includes(fieldType);
      }
    }

    // National roles with member read access
    if (userRoles.includes('National_Chairman') || 
        userRoles.includes('National_Secretary') ||
        userRoles.includes('Webmaster') ||
        userRoles.includes('Tour_Commissioner') ||
        userRoles.includes('Club_Magazine_Editorial')) {
      // PRESERVE EXISTING MEMBERSHIP TYPE RESTRICTIONS for motor fields
      if (fieldType === 'motor') {
        const membershipType = member?.lidmaatschap || member?.membership_type;
        const motorRequiredTypes = ['Gewoon lid', 'Gezins lid'];
        return motorRequiredTypes.includes(membershipType);
      }
      
      return ['personal', 'address', 'membership'].includes(fieldType);
    }

    return false;
  };

  const renderField = (label: string, value: any) => {
    if (!hasValue(value)) return null;
    return <Text><strong>{label}:</strong> {value}</Text>;
  };

  const personalFields = [
    ['Voornaam', member.voornaam],
    ['Achternaam', member.achternaam],
    ['Initialen', member.initialen],
    ['Tussenvoegsel', member.tussenvoegsel],
    ['Geboortedatum', member.geboortedatum],
    ['Geslacht', member.geslacht],
    ['Email', member.email],
    ['Telefoon', member.telefoon || member.phone],
    ['Mobiel', member.mobiel],
    ['Werk telefoon', member.werktelefoon],
    ['BSN', member.bsn],
    ['Nationaliteit', member.nationaliteit]
  ].filter(([_, value]) => hasValue(value));

  const addressFields = [
    ['Straat', member.straat],
    ['Huisnummer', member.huisnummer],
    ['Postcode', member.postcode],
    ['Woonplaats', member.woonplaats],
    ['Land', member.land],
    ['Postadres', member.postadres],
    ['Post postcode', member.postpostcode],
    ['Post woonplaats', member.postwoonplaats],
    ['Post land', member.postland]
  ].filter(([_, value]) => hasValue(value));

  const membershipFields = [
    ['Type', member.lidmaatschap || member.membership_type || member.membershipType],
    ['Regio', member.regio],
    ['Clubblad', member.clubblad],
    ['Nieuwsbrief', member.nieuwsbrief],
    ['Lidnummer', member.lidnummer],
    ['Lid sinds', member.created_at ? new Date(member.created_at).toLocaleDateString('nl-NL') : null],
    ['Laatste update', member.updated_at ? new Date(member.updated_at).toLocaleDateString('nl-NL') : null],
    ['Ingangsdatum', member.ingangsdatum],
    ['Einddatum', member.einddatum],
    ['Opzegtermijn', member.opzegtermijn]
  ].filter(([_, value]) => hasValue(value));

  const motorFields = [
    ['Merk', member.motormerk],
    ['Type', member.motortype],
    ['Model', member.motormodel],
    ['Kleur', member.motorkleur],
    ['Bouwjaar', member.bouwjaar],
    ['Kenteken', member.kenteken],
    ['Cilinderinhoud', member.cilinderinhoud],
    ['Vermogen', member.vermogen]
  ].filter(([_, value]) => hasValue(value));

  const financialFields = [
    ['Bankrekeningnummer', member.bankrekeningnummer],
    ['IBAN', member.iban],
    ['BIC', member.bic],
    ['Contributie', member.contributie],
    ['Betaalwijze', member.betaalwijze],
    ['Incasso', member.incasso]
  ].filter(([_, value]) => hasValue(value));

  // Get all other fields not already shown
  const knownFields = new Set([
    'voornaam', 'achternaam', 'initialen', 'tussenvoegsel', 'geboortedatum', 'geslacht', 'email', 'telefoon', 'phone', 'mobiel', 'werktelefoon', 'bsn', 'nationaliteit',
    'straat', 'huisnummer', 'postcode', 'woonplaats', 'land', 'postadres', 'postpostcode', 'postwoonplaats', 'postland',
    'lidmaatschap', 'membership_type', 'regio', 'clubblad', 'nieuwsbrief', 'lidnummer', 'created_at', 'updated_at', 'ingangsdatum', 'einddatum', 'opzegtermijn', 'status',
    'motormerk', 'motortype', 'motormodel', 'motorkleur', 'bouwjaar', 'kenteken', 'cilinderinhoud', 'vermogen',
    'bankrekeningnummer', 'iban', 'bic', 'contributie', 'betaalwijze', 'incasso',
    'member_id', 'name', 'address'
  ]);
  
  const otherFields = Object.entries(member)
    .filter(([key, value]) => !knownFields.has(key) && hasValue(value))
    .map(([key, value]) => [key.charAt(0).toUpperCase() + key.slice(1), value]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          Lid Details - {member.name || `${member.voornaam} ${member.achternaam}`}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack spacing={6} align="stretch">
            
            {/* Status */}
            <HStack justify="space-between">
              <Text fontWeight="bold">Status:</Text>
              <Badge colorScheme={getStatusColor(member.status)} fontSize="md">
                {member.status || 'Onbekend'}
              </Badge>
            </HStack>

            {canViewFieldType('personal') && personalFields.length > 0 && (
              <>
                <Divider borderColor="orange.400" />
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                    Persoonlijke Gegevens
                  </Text>
                  <SimpleGrid columns={2} spacing={4}>
                    <VStack align="start" spacing={2}>
                      {personalFields.slice(0, Math.ceil(personalFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                    <VStack align="start" spacing={2}>
                      {personalFields.slice(Math.ceil(personalFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                  </SimpleGrid>
                </Box>
              </>
            )}

            {canViewFieldType('address') && addressFields.length > 0 && (
              <>
                <Divider borderColor="orange.400" />
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                    Adresgegevens
                  </Text>
                  <SimpleGrid columns={2} spacing={4}>
                    <VStack align="start" spacing={2}>
                      {addressFields.slice(0, Math.ceil(addressFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                    <VStack align="start" spacing={2}>
                      {addressFields.slice(Math.ceil(addressFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                  </SimpleGrid>
                </Box>
              </>
            )}

            {canViewFieldType('membership') && membershipFields.length > 0 && (
              <>
                <Divider borderColor="orange.400" />
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                    Lidmaatschap
                  </Text>
                  <SimpleGrid columns={2} spacing={4}>
                    <VStack align="start" spacing={2}>
                      {membershipFields.slice(0, Math.ceil(membershipFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                    <VStack align="start" spacing={2}>
                      {membershipFields.slice(Math.ceil(membershipFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                  </SimpleGrid>
                </Box>
              </>
            )}

            {canViewFieldType('motor') && motorFields.length > 0 && (
              <>
                <Divider borderColor="orange.400" />
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                    Motor Gegevens
                  </Text>
                  <SimpleGrid columns={2} spacing={4}>
                    <VStack align="start" spacing={2}>
                      {motorFields.slice(0, Math.ceil(motorFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                    <VStack align="start" spacing={2}>
                      {motorFields.slice(Math.ceil(motorFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                  </SimpleGrid>
                </Box>
              </>
            )}

            {/* Show message if motor fields are hidden due to membership type */}
            {!canViewFieldType('motor') && (member?.lidmaatschap === 'Gezins donateur zonder motor' || member?.lidmaatschap === 'Donateur zonder motor') && (
              <>
                <Divider borderColor="orange.400" />
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                    Motor Gegevens
                  </Text>
                  <Text color="gray.400" fontStyle="italic">
                    Motor gegevens zijn niet van toepassing voor lidmaatschap type: {member?.lidmaatschap}
                  </Text>
                </Box>
              </>
            )}

            {canViewFieldType('financial') && financialFields.length > 0 && (
              <>
                <Divider borderColor="orange.400" />
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                    Financiële Gegevens
                  </Text>
                  <SimpleGrid columns={2} spacing={4}>
                    <VStack align="start" spacing={2}>
                      {financialFields.slice(0, Math.ceil(financialFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                    <VStack align="start" spacing={2}>
                      {financialFields.slice(Math.ceil(financialFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                  </SimpleGrid>
                </Box>
              </>
            )}

            {otherFields.length > 0 && (
              <>
                <Divider borderColor="orange.400" />
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                    Overige Informatie
                  </Text>
                  <SimpleGrid columns={2} spacing={4}>
                    <VStack align="start" spacing={2}>
                      {otherFields.slice(0, Math.ceil(otherFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                    <VStack align="start" spacing={2}>
                      {otherFields.slice(Math.ceil(otherFields.length / 2)).map(([label, value], index) => (
                        <Text key={index}><strong>{label}:</strong> {value}</Text>
                      ))}
                    </VStack>
                  </SimpleGrid>
                </Box>
              </>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}

export default MemberDetailModal;