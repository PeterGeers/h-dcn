import React, { useState, useEffect } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import {
  Box,
  Container,
  Heading,
  Text,
  Image,
  Button,
  SimpleGrid,
  VStack,
  HStack,
  Spinner,
  Center,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { API_CONFIG } from '../../config/api';
import { useAuth } from '../../context/AuthProvider';

// --- Types ---

interface LogoItem {
  name: string;
  logo_url: string;
}

interface TextSection {
  type: 'text';
  title: string;
  content: string;
}

interface LogosSection {
  type: 'logos';
  title: string;
  items: LogoItem[];
}

type LandingSection = TextSection | LogosSection;

interface LandingPageData {
  enabled?: boolean;
  slug: string;
  hero_image_url?: string;
  tagline?: string;
  registration_label?: string;
  logos: LogoItem[];
  sections: LandingSection[];
}

interface PublicEventData {
  event_id: string;
  name: string;
  event_type: string;
  start_date: string;
  end_date: string;
  location: string;
  description?: string;
  participation?: string;
  linked_regio?: string;
  poster_url?: string;
  slug?: string;
  registration_status: string;
  landing_page_enabled?: boolean;
  landing_page?: LandingPageData;
}

// --- Component ---

const EventLandingPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const { t } = useTranslation(['eventBooking', 'events']);
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [event, setEvent] = useState<PublicEventData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;

    const fetchEvent = async () => {
      try {
        setLoading(true);
        setError(null);
        const baseUrl = API_CONFIG.BASE_URL;
        const response = await fetch(`${baseUrl}/events/public/${slug}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data: PublicEventData = await response.json();
        setEvent(data);
      } catch (err) {
        console.error('Failed to fetch event landing page:', err);
        setError(t('page.error_loading'));
      } finally {
        setLoading(false);
      }
    };

    fetchEvent();
  }, [slug, t]);

  if (loading) {
    return (
      <Center minH="100vh" bg="black">
        <Spinner size="xl" color="orange.400" />
      </Center>
    );
  }

  if (error || !event) {
    return (
      <Box minH="100vh" bg="black" p={8}>
        <Container maxW="container.md">
          <Alert status="error" bg="red.900" color="white" borderRadius="md">
            <AlertIcon />
            {error || t('page.error_loading')}
          </Alert>
        </Container>
      </Box>
    );
  }

  const { landing_page, registration_status, landing_page_enabled } = event;
  const hasLandingPage = landing_page_enabled === true && landing_page != null;
  const isOpen = registration_status === 'open';
  const ctaLabel = (hasLandingPage && landing_page!.registration_label) || t('landing.registerButton');

  const pageUrl = window.location.href;

  /**
   * Determine CTA destination and label based on auth state.
   * Always link to register page — EventRegisterPage handles the logic:
   * - If user has event access → auto-redirect to booking
   * - If not → onboarding flow (PasswordGate → RegistrySelector → ClaimAction)
   */
  const getCtaProps = () => {
    if (authLoading) {
      return { to: '#', label: '', isLoading: true };
    }
    if (isAuthenticated) {
      return { to: `/events/${slug}/register`, label: t('landing.goToBooking'), isLoading: false };
    }
    return { to: `/events/${slug}/register`, label: ctaLabel, isLoading: false };
  };

  const ctaProps = getCtaProps();

  const formatDateRange = (start: string, end: string): string => {
    try {
      const startDate = new Date(start);
      const endDate = new Date(end);
      const options: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long', year: 'numeric' };
      return `${startDate.toLocaleDateString(undefined, options)} – ${endDate.toLocaleDateString(undefined, options)}`;
    } catch {
      return `${start} – ${end}`;
    }
  };

  // --- Poster-view mode (without landing page) ---
  if (!hasLandingPage) {
    return (
      <Box minH="100vh" bg="black" color="white">
        <Helmet>
          <title>{event.name} | H-DCN</title>
          <meta name="description" content={event.description || event.name} />
          <meta property="og:title" content={event.name} />
          <meta property="og:description" content={event.description || event.name} />
          {event.poster_url && <meta property="og:image" content={event.poster_url} />}
          <meta property="og:url" content={pageUrl} />
          <meta property="og:type" content="website" />
        </Helmet>

        <Container maxW="container.lg" py={{ base: 4, md: 8 }}>
          <VStack spacing={6} align="stretch">
            {/* Poster (large) — only shown when available */}
            {event.poster_url && (
              <Image
                src={event.poster_url}
                alt={event.name}
                w="100%"
                maxH="80vh"
                objectFit="contain"
                borderRadius="md"
              />
            )}

            {/* Event details */}
            <VStack align="flex-start" spacing={4}>
              <Heading as="h1" size="xl" color="orange.400">
                {event.name}
              </Heading>

              {event.description && (
                <Text color="gray.300" fontSize="md" whiteSpace="pre-wrap">
                  {event.description}
                </Text>
              )}

              <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={3} w="100%">
                <HStack>
                  <Text color="gray.500" fontSize="sm" fontWeight="bold">
                    {t('landing.posterView.dates')}:
                  </Text>
                  <Text color="gray.300" fontSize="sm">
                    {formatDateRange(event.start_date, event.end_date)}
                  </Text>
                </HStack>

                {event.location && (
                  <HStack>
                    <Text color="gray.500" fontSize="sm" fontWeight="bold">
                      {t('landing.posterView.location')}:
                    </Text>
                    <Text color="gray.300" fontSize="sm">
                      {event.location}
                    </Text>
                  </HStack>
                )}

                {event.event_type && (
                  <HStack>
                    <Text color="gray.500" fontSize="sm" fontWeight="bold">
                      {t('landing.posterView.type')}:
                    </Text>
                    <Text color="gray.300" fontSize="sm">
                      {t(`events:event_types.${event.event_type}`, event.event_type)}
                    </Text>
                  </HStack>
                )}

                {event.participation && (
                  <HStack>
                    <Text color="gray.500" fontSize="sm" fontWeight="bold">
                      {t('landing.posterView.participation')}:
                    </Text>
                    <Text color="gray.300" fontSize="sm">
                      {t(`events:participation_modes.${event.participation}`, event.participation)}
                    </Text>
                  </HStack>
                )}

                {event.linked_regio && (
                  <HStack>
                    <Text color="gray.500" fontSize="sm" fontWeight="bold">
                      {t('landing.posterView.region')}:
                    </Text>
                    <Text color="gray.300" fontSize="sm">
                      {event.linked_regio}
                    </Text>
                  </HStack>
                )}
              </SimpleGrid>

              {/* CTA button only when booking flow is defined */}
              {isOpen && (
                <Box pt={4}>
                  {ctaProps.isLoading ? (
                    <Button size="lg" colorScheme="orange" isLoading>
                      {ctaLabel}
                    </Button>
                  ) : (
                    <Button
                      as={RouterLink}
                      to={ctaProps.to}
                      size="lg"
                      colorScheme="orange"
                    >
                      {ctaProps.label}
                    </Button>
                  )}
                </Box>
              )}
            </VStack>
          </VStack>
        </Container>
      </Box>
    );
  }

  // --- Full landing page mode ---

  return (
    <Box minH="100vh" bg="black" color="white">
      <Helmet>
        <title>{event.name} | H-DCN</title>
        <meta name="description" content={landing_page.tagline || event.name} />
        <meta property="og:title" content={event.name} />
        <meta property="og:description" content={landing_page.tagline || event.name} />
        {landing_page.hero_image_url && (
          <meta property="og:image" content={landing_page.hero_image_url} />
        )}
        <meta property="og:url" content={pageUrl} />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={event.name} />
        <meta name="twitter:description" content={landing_page.tagline || event.name} />
        {landing_page.hero_image_url && (
          <meta name="twitter:image" content={landing_page.hero_image_url} />
        )}
      </Helmet>

      {/* Hero Section */}
      <Box position="relative" w="100%" minH={{ base: '60vh', md: '70vh' }} overflow="hidden">
        {landing_page.hero_image_url && (
          <Image
            src={landing_page.hero_image_url}
            alt={event.name}
            position="absolute"
            top={0}
            left={0}
            w="100%"
            h="100%"
            objectFit="cover"
            opacity={0.5}
          />
        )}
        <Box
          position="absolute"
          top={0}
          left={0}
          w="100%"
          h="100%"
          bgGradient="linear(to-t, blackAlpha.900, blackAlpha.400)"
        />
        <Container
          maxW="container.lg"
          position="relative"
          zIndex={1}
          h="100%"
          display="flex"
          alignItems="flex-end"
          pb={{ base: 10, md: 16 }}
          pt={{ base: 24, md: 32 }}
        >
          <VStack align="flex-start" spacing={4} maxW="700px">
            <Heading
              as="h1"
              size={{ base: 'xl', md: '2xl' }}
              color="orange.400"
              lineHeight="shorter"
            >
              {event.name}
            </Heading>
            {landing_page.tagline && (
              <Text fontSize={{ base: 'lg', md: 'xl' }} color="gray.200">
                {landing_page.tagline}
              </Text>
            )}
            <HStack spacing={4} flexWrap="wrap" color="gray.300" fontSize="sm">
              <Text>{formatDateRange(event.start_date, event.end_date)}</Text>
              <Text>•</Text>
              <Text>{event.location}</Text>
            </HStack>
            {/* CTA in hero */}
            <Box pt={4}>
              {isOpen ? (
                ctaProps.isLoading ? (
                  <Button size="lg" colorScheme="orange" px={8} isLoading>
                    {ctaLabel}
                  </Button>
                ) : (
                  <VStack align="flex-start" spacing={2}>
                    <Button
                      as={RouterLink}
                      to={ctaProps.to}
                      size="lg"
                      colorScheme="orange"
                      px={8}
                    >
                      {ctaProps.label}
                    </Button>
                  </VStack>
                )
              ) : (
                <Button size="lg" colorScheme="gray" isDisabled>
                  {t('landing.registrationClosed')}
                </Button>
              )}
            </Box>
          </VStack>
        </Container>
      </Box>

      {/* Content Sections */}
      {landing_page.sections && landing_page.sections.length > 0 && (
        <Container maxW="container.lg" py={{ base: 10, md: 16 }}>
          <VStack spacing={{ base: 10, md: 14 }} align="stretch">
            {landing_page.sections.map((section, idx) => (
              <Box key={idx}>
                {section.type === 'text' && (
                  <VStack align="flex-start" spacing={4}>
                    <Heading as="h2" size="lg" color="orange.300">
                      {section.title}
                    </Heading>
                    <Text
                      color="gray.300"
                      fontSize="md"
                      lineHeight="tall"
                      whiteSpace="pre-wrap"
                      dangerouslySetInnerHTML={{ __html: section.content }}
                    />
                  </VStack>
                )}
                {section.type === 'logos' && (
                  <VStack align="flex-start" spacing={6}>
                    <Heading as="h2" size="lg" color="orange.300">
                      {section.title}
                    </Heading>
                    <SimpleGrid
                      columns={{ base: 2, sm: 3, md: 4, lg: 5 }}
                      spacing={6}
                      w="100%"
                    >
                      {section.items.map((item, itemIdx) => (
                        <VStack key={itemIdx} spacing={2}>
                          <Box
                            bg="whiteAlpha.100"
                            borderRadius="md"
                            p={3}
                            w="100%"
                            display="flex"
                            alignItems="center"
                            justifyContent="center"
                            minH="80px"
                          >
                            <Image
                              src={item.logo_url}
                              alt={item.name}
                              maxH="60px"
                              maxW="100%"
                              objectFit="contain"
                            />
                          </Box>
                          <Text fontSize="xs" color="gray.400" textAlign="center" noOfLines={2}>
                            {item.name}
                          </Text>
                        </VStack>
                      ))}
                    </SimpleGrid>
                  </VStack>
                )}
              </Box>
            ))}
          </VStack>
        </Container>
      )}

      {/* Logos Bar (organizing clubs) */}
      {landing_page.logos && landing_page.logos.length > 0 && (
        <Box bg="whiteAlpha.50" py={{ base: 8, md: 12 }}>
          <Container maxW="container.lg">
            <HStack
              spacing={{ base: 6, md: 10 }}
              justify="center"
              flexWrap="wrap"
              gap={4}
            >
              {landing_page.logos.map((logo, idx) => (
                <VStack key={idx} spacing={2}>
                  <Box
                    bg="whiteAlpha.100"
                    borderRadius="md"
                    p={3}
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                  >
                    <Image
                      src={logo.logo_url}
                      alt={logo.name}
                      maxH="50px"
                      maxW="120px"
                      objectFit="contain"
                    />
                  </Box>
                  <Text fontSize="xs" color="gray.500">
                    {logo.name}
                  </Text>
                </VStack>
              ))}
            </HStack>
          </Container>
        </Box>
      )}

      {/* Bottom CTA */}
      <Container maxW="container.lg" py={{ base: 10, md: 16 }}>
        <Center>
          <VStack spacing={2}>
            {isOpen ? (
              ctaProps.isLoading ? (
                <Button size="lg" colorScheme="orange" px={10} isLoading>
                  {ctaLabel}
                </Button>
              ) : (
                <Button
                  as={RouterLink}
                  to={ctaProps.to}
                  size="lg"
                  colorScheme="orange"
                  px={10}
                >
                  {ctaProps.label}
                </Button>
              )
            ) : (
              <Button size="lg" colorScheme="gray" isDisabled>
                {t('landing.registrationClosed')}
              </Button>
            )}
          </VStack>
        </Center>
      </Container>
    </Box>
  );
};

export default EventLandingPage;
