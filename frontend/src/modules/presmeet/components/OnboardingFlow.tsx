import React, { useCallback, useEffect, useRef, useState } from 'react';
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
  Input,
  useToast,
  Center,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { ClubRegistryEntry, ClubRegistry } from '../types/presmeet';
import { presmeetService } from '../services/presmeetApi';

// TODO: Replace with actual logo paths once branding assets are added to /public/assets/presmeet/
const PRESMEET_LOGO_SRC = '/assets/presmeet/presmeet-logo.png';
const FH_DCE_LOGO_SRC = '/assets/presmeet/fh-dce-logo.png';

/** Duration (ms) after which logos shrink automatically if user hasn't scrolled. */
const LOGO_ANIMATION_DELAY_MS = 3000;
/** Minimum CSS transition duration for logo size change. */
const LOGO_TRANSITION_DURATION = '400ms';

/**
 * Filters clubs by name using case-insensitive matching.
 * Returns all clubs when search text is empty.
 * Exported for testability (used in property tests).
 */
export function filterClubs(
  clubs: ClubRegistryEntry[],
  search: string
): ClubRegistryEntry[] {
  const trimmed = search.trim();
  if (!trimmed) {
    return clubs;
  }
  const lowerSearch = trimmed.toLowerCase();
  return clubs.filter((club) =>
    club.club_name.toLowerCase().includes(lowerSearch)
  );
}

export interface OnboardingFlowProps {
  onComplete: (clubId: string) => void;
}

const OnboardingFlow: React.FC<OnboardingFlowProps> = ({ onComplete }) => {
  const { t } = useTranslation('presmeet');
  const toast = useToast();

  // State
  const [registry, setRegistry] = useState<ClubRegistry | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [selectedClubId, setSelectedClubId] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [logosSmall, setLogosSmall] = useState(false);
  const [conflictInfo, setConflictInfo] = useState<{
    clubName: string;
    contact: string;
  } | null>(null);

  const logosTransitioned = useRef(false);

  // Shrink logos on scroll or after a timer
  const shrinkLogos = useCallback(() => {
    if (!logosTransitioned.current) {
      logosTransitioned.current = true;
      setLogosSmall(true);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(shrinkLogos, LOGO_ANIMATION_DELAY_MS);

    const handleScroll = () => {
      if (window.scrollY > 20) {
        shrinkLogos();
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('scroll', handleScroll);
    };
  }, [shrinkLogos]);

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
        title: t('onboarding.club_assigned'),
        description: t('onboarding.club_assigned_desc', { clubName: club.club_name }),
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
        title: t('onboarding.assignment_failed'),
        description: response.error || t('onboarding.assignment_failed_desc'),
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
          <Text color="gray.600">{t('onboarding.loading_clubs')}</Text>
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
          <AlertTitle>{t('onboarding.load_failed')}</AlertTitle>
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
          <AlertTitle mb={2}>{t('onboarding.club_already_assigned')}</AlertTitle>
          <AlertDescription mb={4}>
            <Text mb={2}>
              {t('onboarding.already_assigned_desc', { clubName: conflictInfo.clubName })}
            </Text>
            <Text mb={2}>
              {t('onboarding.current_contact')}: <strong>{conflictInfo.contact}</strong>
            </Text>
            <Text fontSize="sm" color="gray.600">
              {t('onboarding.contact_admin')}
            </Text>
          </AlertDescription>
          <Button size="sm" onClick={handleDismissConflict}>
            {t('onboarding.choose_different')}
          </Button>
        </Alert>
      </Box>
    );
  }

  // --- Club selection list ---
  const clubs = registry?.clubs ?? [];
  const filteredClubs = filterClubs(clubs, searchText);

  return (
    <Box py={6}>
      <VStack spacing={6} align="stretch">
        {/* Presmeet + FH-DCE logos with animated size transition */}
        <HStack
          justify="center"
          spacing={6}
          position={logosSmall ? 'sticky' : 'relative'}
          top={logosSmall ? 0 : undefined}
          zIndex={logosSmall ? 10 : undefined}
          bg={logosSmall ? 'white' : 'transparent'}
          py={logosSmall ? 2 : 6}
          transition={`all ${LOGO_TRANSITION_DURATION} ease-in-out`}
        >
          <Image
            src={PRESMEET_LOGO_SRC}
            alt="Presmeet logo"
            height={logosSmall ? '40px' : '120px'}
            objectFit="contain"
            transition={`height ${LOGO_TRANSITION_DURATION} ease-in-out`}
            fallback={
              <Box
                height={logosSmall ? '40px' : '120px'}
                width={logosSmall ? '40px' : '120px'}
                bg="gray.100"
                borderRadius="md"
                display="flex"
                alignItems="center"
                justifyContent="center"
                transition={`all ${LOGO_TRANSITION_DURATION} ease-in-out`}
              >
                <Text fontSize="xs" color="gray.500">Presmeet</Text>
              </Box>
            }
          />
          <Image
            src={FH_DCE_LOGO_SRC}
            alt="FH-DCE logo"
            height={logosSmall ? '40px' : '120px'}
            objectFit="contain"
            transition={`height ${LOGO_TRANSITION_DURATION} ease-in-out`}
            fallback={
              <Box
                height={logosSmall ? '40px' : '120px'}
                width={logosSmall ? '40px' : '120px'}
                bg="gray.100"
                borderRadius="md"
                display="flex"
                alignItems="center"
                justifyContent="center"
                transition={`all ${LOGO_TRANSITION_DURATION} ease-in-out`}
              >
                <Text fontSize="xs" color="gray.500">FH-DCE</Text>
              </Box>
            }
          />
        </HStack>

        <Box textAlign="center">
          <Heading size="lg" mb={2}>
            {t('onboarding.select_club')}
          </Heading>
          <Text color="gray.600">
            {t('onboarding.select_club_desc')}
          </Text>
        </Box>

        {clubs.length === 0 ? (
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            {t('onboarding.no_clubs')}
          </Alert>
        ) : (
          <>
            <Input
              placeholder={t('onboarding.search_clubs')}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              size="md"
              aria-label={t('onboarding.search_clubs')}
            />

            {filteredClubs.length === 0 ? (
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                {t('onboarding.no_search_results')}
              </Alert>
            ) : (
              <SimpleGrid columns={{ base: 1, sm: 2, md: 3 }} spacing={4}>
                {filteredClubs.map((club) => {
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
                              {t('onboarding.no_logo')}
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
                          {t('onboarding.no_logo')}
                        </Text>
                      </Box>
                    )}

                    <Text fontWeight="semibold" textAlign="center" fontSize="sm">
                      {club.club_name}
                    </Text>

                    {isAssigned && (
                      <Text fontSize="xs" color="orange.600">
                        {t('onboarding.already_assigned')}
                      </Text>
                    )}

                    {isSelected && assigning && (
                      <HStack spacing={2}>
                        <Spinner size="xs" />
                        <Text fontSize="xs" color="blue.600">
                          {t('onboarding.assigning')}
                        </Text>
                      </HStack>
                    )}
                  </VStack>
                </Box>
              );
            })}
          </SimpleGrid>
            )}
          </>
        )}
      </VStack>
    </Box>
  );
};

export default OnboardingFlow;
