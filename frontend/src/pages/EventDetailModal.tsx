import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthProvider';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalCloseButton,
  ModalBody,
  Image,
  Heading,
  Text,
  VStack,
  SimpleGrid,
  Button,
  Box,
} from '@chakra-ui/react';

// --- Types ---

export interface PublicEvent {
  event_id: string;
  name: string;
  slug: string;
  event_type: string;
  location: string;
  start_date: string;
  end_date: string;
  poster_url?: string;
  description?: string;
  linked_regio?: string;
  landing_page?: Record<string, any>;
  registration_open?: string;
  registration_close?: string;
  payment_deadline?: string;
}

interface EventDetailModalProps {
  event: PublicEvent | null;
  isOpen: boolean;
  onClose: () => void;
}

// --- Helpers ---

function isBookable(event: PublicEvent): boolean {
  return !!(
    event.registration_open ||
    event.registration_close ||
    event.payment_deadline
  );
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

// --- Component ---

const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, isOpen, onClose }) => {
  const { t } = useTranslation('events');
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  if (!event) return null;

  const bookable = isBookable(event);

  const handleBook = () => {
    onClose();
    navigate(`/events/${event.event_id}/booking`);
  };

  const handleRegister = () => {
    window.open(`/events/${event.slug}/register`, '_blank');
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" blockScrollOnMount={true} scrollBehavior="inside">
      <ModalOverlay bg="blackAlpha.800" />
      <ModalContent
        bg="gray.900"
        color="white"
        maxH="85vh"
        mt={8}
        mb="auto"
      >
        <ModalCloseButton color="gray.400" zIndex={1} />
        <ModalBody p={6} overflowY="auto">
          <VStack spacing={5} align="stretch">
            {/* Poster */}
            {event.poster_url && (
              <Image
                src={event.poster_url}
                alt={event.name}
                w="100%"
                objectFit="contain"
                borderRadius="md"
                bg="gray.800"
              />
            )}

            {/* Event name */}
            <Heading as="h2" size="lg" color="orange.400">
              {event.name}
            </Heading>

            {/* Description */}
            {event.description && (
              <Text whiteSpace="pre-wrap" color="gray.300">
                {event.description}
              </Text>
            )}

            {/* Details grid */}
            <SimpleGrid columns={2} spacing={3}>
              <Box>
                <Text fontSize="xs" color="gray.500" textTransform="uppercase">
                  {t('calendar.modal.dates')}
                </Text>
                <Text fontSize="sm" color="gray.200">
                  {formatDate(event.start_date)}
                  {event.end_date !== event.start_date && ` – ${formatDate(event.end_date)}`}
                </Text>
              </Box>

              <Box>
                <Text fontSize="xs" color="gray.500" textTransform="uppercase">
                  {t('calendar.modal.location')}
                </Text>
                <Text fontSize="sm" color="gray.200">
                  {event.location || '—'}
                </Text>
              </Box>

              <Box>
                <Text fontSize="xs" color="gray.500" textTransform="uppercase">
                  {t('calendar.modal.type')}
                </Text>
                <Text fontSize="sm" color="gray.200">
                  {t(`event_types.${event.event_type}`, event.event_type)}
                </Text>
              </Box>

              {event.linked_regio && (
                <Box>
                  <Text fontSize="xs" color="gray.500" textTransform="uppercase">
                    {t('calendar.modal.region')}
                  </Text>
                  <Text fontSize="sm" color="gray.200">
                    {event.linked_regio}
                  </Text>
                </Box>
              )}
            </SimpleGrid>

            {/* CTA button */}
            {bookable && isAuthenticated && (
              <Button
                colorScheme="orange"
                size="lg"
                onClick={handleBook}
              >
                {t('calendar.modal.book')}
              </Button>
            )}

            {bookable && !isAuthenticated && (
              <Button
                colorScheme="orange"
                size="lg"
                onClick={handleRegister}
              >
                {t('calendar.modal.register')}
              </Button>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default EventDetailModal;
