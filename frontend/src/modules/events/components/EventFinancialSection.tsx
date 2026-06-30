import React from 'react';
import { SimpleGrid, FormControl, FormLabel, Input, Textarea } from '@chakra-ui/react';

// ============================================================================
// TYPES
// ============================================================================

interface EventFinancialSectionProps {
  formData: {
    participants: string;
    cost: string;
    revenue: string;
    notes: string;
  };
  onChange: (field: string, value: string) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

function EventFinancialSection({ formData, onChange }: EventFinancialSectionProps) {
  return (
    <>
      <SimpleGrid columns={2} spacing={4}>
        <FormControl>
          <FormLabel color="orange.300">Aantal deelnemers</FormLabel>
          <Input
            type="number"
            value={formData.participants}
            onChange={(e) => onChange('participants', e.target.value)}
            placeholder="0"
            bg="gray.700"
            borderColor="orange.400"
          />
        </FormControl>

        <FormControl>
          <FormLabel color="orange.300">Kosten (€)</FormLabel>
          <Input
            type="number"
            step="0.01"
            value={formData.cost}
            onChange={(e) => onChange('cost', e.target.value)}
            placeholder="0.00"
            bg="gray.700"
            borderColor="orange.400"
          />
        </FormControl>

        <FormControl>
          <FormLabel color="orange.300">Inkomsten (€)</FormLabel>
          <Input
            type="number"
            step="0.01"
            value={formData.revenue}
            onChange={(e) => onChange('revenue', e.target.value)}
            placeholder="0.00"
            bg="gray.700"
            borderColor="orange.400"
          />
        </FormControl>
      </SimpleGrid>

      <FormControl mt={4}>
        <FormLabel color="orange.300">Opmerkingen</FormLabel>
        <Textarea
          value={formData.notes}
          onChange={(e) => onChange('notes', e.target.value)}
          placeholder="Interne notities over kosten, afspraken, etc."
          bg="gray.700"
          borderColor="orange.400"
          rows={3}
        />
      </FormControl>
    </>
  );
}

export default EventFinancialSection;
