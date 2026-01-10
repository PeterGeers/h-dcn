/**
 * Address Label Card Component for H-DCN Reporting Dashboard
 * 
 * This component provides a card interface for accessing address label
 * generation functionality from the main reporting dashboard.
 */

import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Badge,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalCloseButton,
  useDisclosure,
  Icon
} from '@chakra-ui/react';
import { EmailIcon, EditIcon } from '@chakra-ui/icons';
import { Member } from '../../types/index';
import AddressLabelGenerator from './AddressLabelGenerator';

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface AddressLabelCardProps {
  members: Member[];
  title: string;
  description: string;
  viewName: string;
  icon?: React.ComponentType;
  colorScheme?: string;
  filterDescription?: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AddressLabelCard: React.FC<AddressLabelCardProps> = ({
  members,
  title,
  description,
  viewName,
  icon: IconComponent = EditIcon,
  colorScheme = 'orange',
  filterDescription
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Filter members based on view requirements
  const filteredMembers = React.useMemo(() => {
    switch (viewName) {
      case 'addressStickersPaper':
        return members.filter(m => 
          m.status === 'Actief' && 
          m.clubblad === 'Papier' &&
          m.korte_naam && m.straat && m.postcode && m.woonplaats
        );
      case 'addressStickersRegional':
        return members.filter(m => 
          m.status === 'Actief' &&
          m.korte_naam && m.straat && m.postcode && m.woonplaats
        );
      default:
        return members.filter(m => 
          m.korte_naam && m.straat && m.postcode && m.woonplaats
        );
    }
  }, [members, viewName]);

  const validAddressCount = filteredMembers.length;
  const totalMembers = members.length;

  return (
    <>
      <Box
        bg="gray.800"
        borderColor={`${colorScheme}.400`}
        border="1px"
        borderRadius="lg"
        p={6}
        cursor="pointer"
        transition="all 0.2s"
        _hover={{
          borderColor: `${colorScheme}.300`,
          transform: 'translateY(-2px)',
          shadow: 'lg'
        }}
        onClick={onOpen}
      >
        <VStack spacing={4} align="stretch">
          {/* Header */}
          <HStack justify="space-between" align="start">
            <HStack spacing={3}>
              <Icon as={IconComponent} boxSize={6} color={`${colorScheme}.400`} />
              <VStack align="start" spacing={1}>
                <Heading size="md" color={`${colorScheme}.300`}>
                  {title}
                </Heading>
                <Text color="gray.300" fontSize="sm">
                  {description}
                </Text>
              </VStack>
            </HStack>
          </HStack>

          {/* Statistics */}
          <HStack justify="space-between" wrap="wrap" spacing={2}>
            <HStack spacing={2}>
              <Badge colorScheme="blue" fontSize="xs">
                {validAddressCount} geldige adressen
              </Badge>
              {validAddressCount < totalMembers && (
                <Badge colorScheme="yellow" fontSize="xs">
                  {totalMembers - validAddressCount} uitgefilterd
                </Badge>
              )}
            </HStack>
          </HStack>

          {/* Filter Description */}
          {filterDescription && (
            <Text color="gray.400" fontSize="xs">
              {filterDescription}
            </Text>
          )}

          {/* Action Button */}
          <Button
            colorScheme={colorScheme}
            size="sm"
            leftIcon={<Icon as={EditIcon} />}
            onClick={(e) => {
              e.stopPropagation();
              onOpen();
            }}
          >
            Labels Genereren
          </Button>
        </VStack>
      </Box>

      {/* Address Label Generator Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="6xl">
        <ModalOverlay />
        <ModalContent bg="gray.900" maxW="90vw" maxH="90vh">
          <ModalCloseButton color="white" />
          <AddressLabelGenerator
            members={filteredMembers}
            viewName={viewName}
            onClose={onClose}
          />
        </ModalContent>
      </Modal>
    </>
  );
};

export default AddressLabelCard;