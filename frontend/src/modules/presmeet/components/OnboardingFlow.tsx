import React, { useEffect, useState } from 'react';
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Image,
  Button,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  VStack,
  HStack,
  useToast,
  Center,
} from '@chakra-ui/react';
import { ClubRegistryEntry, ClubRegistry } from '../types/presmeet';
import { presmeetService } from '../services/presmeetApi';

export interface OnboardingFlowProps {
  onComplete: (clubId: string) => void;
}

const OnboardingFlow: React.FC<OnboardingFlowProps> = ({ onComplete }) => {
  const toast = useToast();

  // State
  const [registry, setRegistry] = useState<ClubRegistry | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [selectedClubId, setSelectedClubId] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [conflictInfo, setConflictInfo] = useState<{
    clubName: string;
    contact: string;
  } | null>(null);

  // Fetch club registry on mount
  useEffect(() => {
    const fetchRegistry = async () => {
      setLoading(true);
      setFetchError(null);

      const response = await presmeetService.getClubRegistry();

      if (response.success && response.data) {
        setRegistry(response.data);
      } else {
        setFetchError(response.error || 'Failed to load club registry');
      }

      setLoading(false);
    };

    fetchRegistry();
  }, []);

  // Handle club selection and assignment
  const handleSelectClub = async (club: ClubRegistryEntry) => {
    setSelectedClubId(club.club_id);
    setConflictInfo(null);
    setAssigning(true);

    const response = await presmeetService.assignClub(club.club_id);

    if (response.success && response.data) {
      toast({
        title: 'Club assigned',
        description: `You are now registered as the representative for ${club.club_name}.`,
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
      onComplete(club.club_id);
    } else if ((response as any).data?.assigned_contact || response.error?.includes('already assigned')) {
      // 409 conflict — club already assigned
      const contact = (response as any).data?.assigned_contact || 'the current representative';
      setConflictInfo({
        clubName: club.club_name,
        contact: typeof contact === 'string' ? contact : 'Contact admin',
      });
    } else {
      toast({
        title: 'Assignment failed',
        description: response.error || 'An unexpected error occurred. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }

    setAssigning(false);
  };

  const handleDismissConflict = () => {
    setConflictInfo(null);
    setSelectedClubId(null);
  };

  // --- Loading state ---
  if (loading) {
    return (
      <Center py={12}>
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" />
          <Text color="gray.600">Loading available clubs...</Text>
        </VStack>
      </Center>
    );
  }

  // --- Fetch error state ---
  if (fetchError) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        <Box>
          <AlertTitle>Failed to load clubs</AlertTitle>
          <AlertDescription>{fetchError}</AlertDescription>
        </Box>
      </Alert>
    );
  }

  // --- Conflict state (409) ---
  if (conflictInfo) {
    return (
      <Box maxW="lg" mx="auto" py={8}>
        <Alert status="warning" borderRadius="md" flexDirection="column" textAlign="center" py={6}>
          <AlertIcon boxSize="40px" mr={0} mb={4} />
          <AlertTitle mb={2}>Club Already Assigned</AlertTitle>
          <AlertDescription mb={4}>
            <Text mb={2}>
              <strong>{conflictInfo.clubName}</strong> already has a registered representative.
            </Text>
            <Text mb={2}>
              Current contact: <strong>{conflictInfo.contact}</strong>
            </Text>
            <Text fontSize="sm" color="gray.600">
              If you believe this is incorrect, please contact the PresMeet administrator to reassign the club.
            </Text>
          </AlertDescription>
          <Button size="sm" onClick={handleDismissConflict}>
            Choose a different club
          </Button>
        </Alert>
      </Box>
    );
  }

  // --- Club selection list ---
  const clubs = registry?.clubs ?? [];

  return (
    <Box py={6}>
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Heading size="lg" mb={2}>
            Select Your Club
          </Heading>
          <Text color="gray.600">
            Choose the club you represent for the Presidents' Meeting.
          </Text>
        </Box>

        {clubs.length === 0 ? (
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            No clubs are currently available. Please contact the administrator.
          </Alert>
        ) : (
          <SimpleGrid columns={{ base: 1, sm: 2, md: 3 }} spacing={4}>
            {clubs.map((club) => {
              const isAssigned = !!club.assigned_member_id;
              const isSelected = selectedClubId === club.club_id;

              return (
                <Box
                  key={club.club_id}
                  borderWidth="2px"
                  borderColor={isSelected ? 'blue.500' : 'gray.200'}
                  borderRadius="lg"
                  p={4}
                  cursor={assigning ? 'not-allowed' : 'pointer'}
                  opacity={assigning && !isSelected ? 0.6 : 1}
                  _hover={
                    !assigning
                      ? { borderColor: 'blue.400', shadow: 'md' }
                      : undefined
                  }
                  transition="all 0.2s"
                  onClick={() => !assigning && handleSelectClub(club)}
                >
                  <VStack spacing={3}>
                    {club.logo_url ? (
                      <Image
                        src={club.logo_url}
                        alt={`${club.club_name} logo`}
                        boxSize="60px"
                        objectFit="contain"
                        fallback={
                          <Box
                            boxSize="60px"
                            bg="gray.100"
                            borderRadius="md"
                            display="flex"
                            alignItems="center"
                            justifyContent="center"
                          >
                            <Text fontSize="xs" color="gray.500">
                              No logo
                            </Text>
                          </Box>
                        }
                      />
                    ) : (
                      <Box
                        boxSize="60px"
                        bg="gray.100"
                        borderRadius="md"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                      >
                        <Text fontSize="xs" color="gray.500">
                          No logo
                        </Text>
                      </Box>
                    )}

                    <Text fontWeight="semibold" textAlign="center" fontSize="sm">
                      {club.club_name}
                    </Text>

                    {isAssigned && (
                      <Text fontSize="xs" color="orange.600">
                        Already assigned
                      </Text>
                    )}

                    {isSelected && assigning && (
                      <HStack spacing={2}>
                        <Spinner size="xs" />
                        <Text fontSize="xs" color="blue.600">
                          Assigning...
                        </Text>
                      </HStack>
                    )}
                  </VStack>
                </Box>
              );
            })}
          </SimpleGrid>
        )}
      </VStack>
    </Box>
  );
};

export default OnboardingFlow;
