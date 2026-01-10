/**
 * Address Labels Section Component for H-DCN Reporting Dashboard
 * 
 * This component provides a section containing various address label
 * generation options for different use cases.
 */

import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Grid,
  GridItem,
  Alert,
  AlertIcon
} from '@chakra-ui/react';
import { EmailIcon, EditIcon, AtSignIcon, StarIcon } from '@chakra-ui/icons';
import { Member } from '../../types/index';
import AddressLabelCard from './AddressLabelCard';

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface AddressLabelsSectionProps {
  members: Member[];
  userRole: string;
  userRegion?: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AddressLabelsSection: React.FC<AddressLabelsSectionProps> = ({
  members,
  userRole,
  userRegion
}) => {
  // Filter members by region for regional administrators
  const regionalMembers = React.useMemo(() => {
    if (userRegion && !['System_CRUD', 'Members_CRUD'].includes(userRole)) {
      return members.filter(member => member.regio === userRegion);
    }
    return members;
  }, [members, userRole, userRegion]);

  // Check if user has access to different label types
  const canAccessPaperLabels = ['System_CRUD', 'Members_CRUD', 'Communication_CRUD'].includes(userRole);
  const canAccessRegionalLabels = true; // All reporting users can access regional labels
  const canAccessAllLabels = ['System_CRUD', 'Members_CRUD'].includes(userRole);

  if (regionalMembers.length === 0) {
    return (
      <Box bg="gray.800" borderRadius="lg" p={6}>
        <Alert status="info">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold">Geen leden beschikbaar</Text>
            <Text fontSize="sm">
              Er zijn geen leden beschikbaar voor het genereren van adreslabels.
            </Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  return (
    <Box bg="gray.800" borderRadius="lg" p={6}>
      <VStack spacing={6} align="stretch">
        {/* Section Header */}
        <VStack spacing={2} align="start">
          <Heading color="orange.500" size="lg">
            🏷️ Adreslabels
          </Heading>
          <Text color="gray.300" fontSize="sm">
            Genereer adreslabels voor verschillende doeleinden en distributie
          </Text>
          {userRegion && !canAccessAllLabels && (
            <Text color="blue.300" fontSize="xs">
              Gefilterd op regio: {userRegion}
            </Text>
          )}
        </VStack>

        {/* Label Cards Grid */}
        <Grid templateColumns="repeat(auto-fit, minmax(300px, 1fr))" gap={6}>
          {/* Paper Clubblad Labels */}
          {canAccessPaperLabels && (
            <GridItem>
              <AddressLabelCard
                members={regionalMembers}
                title="Papieren Clubblad"
                description="Adreslabels voor papieren clubblad verzending"
                viewName="addressStickersPaper"
                icon={EmailIcon}
                colorScheme="blue"
                filterDescription="Alleen actieve leden met papieren clubblad voorkeur"
              />
            </GridItem>
          )}

          {/* Regional Labels */}
          {canAccessRegionalLabels && (
            <GridItem>
              <AddressLabelCard
                members={regionalMembers}
                title="Regionale Mailings"
                description="Adreslabels voor regionale communicatie en evenementen"
                viewName="addressStickersRegional"
                icon={AtSignIcon}
                colorScheme="green"
                filterDescription={
                  userRegion && !canAccessAllLabels
                    ? `Alleen actieve leden in regio ${userRegion}`
                    : "Alleen actieve leden"
                }
              />
            </GridItem>
          )}

          {/* All Members Labels (System/Members CRUD only) */}
          {canAccessAllLabels && (
            <GridItem>
              <AddressLabelCard
                members={members} // Use all members, not filtered by region
                title="Alle Leden"
                description="Adreslabels voor alle leden (alle regio's)"
                viewName="addressStickersAll"
                icon={StarIcon}
                colorScheme="purple"
                filterDescription="Alle leden met geldige adresgegevens"
              />
            </GridItem>
          )}

          {/* Birthday Cards Labels */}
          <GridItem>
            <AddressLabelCard
              members={regionalMembers}
              title="Verjaardagskaarten"
              description="Adreslabels voor het versturen van verjaardagskaarten"
              viewName="birthdayLabels"
              icon={EditIcon}
              colorScheme="pink"
              filterDescription="Actieve leden met volledige adresgegevens"
            />
          </GridItem>
        </Grid>

        {/* Usage Instructions */}
        <Box bg="gray.700" borderRadius="md" p={4}>
          <VStack spacing={2} align="start">
            <Text color="orange.300" fontWeight="semibold" fontSize="sm">
              💡 Gebruikstips
            </Text>
            <VStack spacing={1} align="start" fontSize="xs" color="gray.300">
              <Text>• Klik op een kaart om de labelgenerator te openen</Text>
              <Text>• Kies uit verschillende standaard labelformaten (Avery, etc.)</Text>
              <Text>• Pas lettergrootte, uitlijning en andere opties aan</Text>
              <Text>• Preview functie toont hoe labels eruit zien voor het printen</Text>
              <Text>• Export naar PDF voor printen of CSV/Excel voor verdere bewerking</Text>
              <Text>• Start positie instelling voor gedeeltelijk gebruikte labelvellen</Text>
            </VStack>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
};

export default AddressLabelsSection;