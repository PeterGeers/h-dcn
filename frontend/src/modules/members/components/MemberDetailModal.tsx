import React from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalCloseButton,
  VStack, HStack, Text, Badge, Divider, SimpleGrid, Box
} from '@chakra-ui/react';
import { Member } from '../../../types';

interface MemberDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  member: Member | null;
}

function MemberDetailModal({ isOpen, onClose, member }: MemberDetailModalProps) {
  if (!member) return null;

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'green';
      case 'inactive': return 'red';
      case 'pending': return 'yellow';
      default: return 'gray';
    }
  };

  const hasValue = (value: any) => value && value !== '' && value !== 'undefined' && value !== null;

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
    ['Type', member.lidmaatschap || member.membership_type],
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

            {personalFields.length > 0 && (
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

            {addressFields.length > 0 && (
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

            {membershipFields.length > 0 && (
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

            {motorFields.length > 0 && (
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

            {financialFields.length > 0 && (
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