import React from 'react';
import { SimpleGrid, FormControl, FormLabel, Input } from '@chakra-ui/react';

// ============================================================================
// TYPES
// ============================================================================

interface EventRegistrationSectionProps {
  formData: {
    registration_open: string;
    registration_close: string;
    payment_deadline: string;
    slug: string;
  };
  onChange: (field: string, value: string) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

function EventRegistrationSection({ formData, onChange }: EventRegistrationSectionProps) {
  return (
    <SimpleGrid columns={2} spacing={4}>
      <FormControl>
        <FormLabel color="orange.300">Registratie open</FormLabel>
        <Input
          type="datetime-local"
          value={formData.registration_open}
          onChange={(e) => onChange('registration_open', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>

      <FormControl>
        <FormLabel color="orange.300">Registratie sluit</FormLabel>
        <Input
          type="datetime-local"
          value={formData.registration_close}
          onChange={(e) => onChange('registration_close', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>

      <FormControl>
        <FormLabel color="orange.300">Betaaldeadline</FormLabel>
        <Input
          type="datetime-local"
          value={formData.payment_deadline}
          onChange={(e) => onChange('payment_deadline', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>

      <FormControl>
        <FormLabel color="orange.300">URL Slug</FormLabel>
        <Input
          value={formData.slug}
          onChange={(e) => onChange('slug', e.target.value)}
          placeholder="bijv. presmeet-2026"
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>
    </SimpleGrid>
  );
}

export default EventRegistrationSection;
