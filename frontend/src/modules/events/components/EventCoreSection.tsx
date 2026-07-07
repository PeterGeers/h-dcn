import React from 'react';
import {
  SimpleGrid, FormControl, FormLabel, Input, Select, HStack, Button, Text, Textarea,
} from '@chakra-ui/react';
import {
  EVENT_TYPES_BY_CATEGORY,
  EVENT_TYPE_LABELS,
  EVENT_CATEGORY_LABELS,
  PARTICIPATION_MODE_LABELS,
  EventType,
  EventCategory,
} from '../../../config/eventFields/eventTypes';

// ============================================================================
// TYPES
// ============================================================================

interface EventCoreSectionProps {
  formData: {
    name: string;
    event_type: string;
    participation: string;
    status: string;
    linked_regio: string;
    start_date: string;
    end_date: string;
    location: string;
    poster_url: string;
    description: string;
  };
  availableRegions: string[];
  allowedRegions: string[];
  isUploading: boolean;
  onChange: (field: string, value: string) => void;
  onPosterUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

function EventCoreSection({
  formData,
  availableRegions,
  allowedRegions,
  isUploading,
  onChange,
  onPosterUpload,
}: EventCoreSectionProps) {
  return (
    <SimpleGrid columns={2} spacing={4} w="full">
      <FormControl isRequired>
        <FormLabel color="orange.300">Eventnaam</FormLabel>
        <Input
          value={formData.name}
          onChange={(e) => onChange('name', e.target.value)}
          placeholder="Naam van het evenement"
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>

      <FormControl isRequired>
        <FormLabel color="orange.300">Type</FormLabel>
        <Select
          value={formData.event_type}
          onChange={(e) => onChange('event_type', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
          placeholder="Selecteer type..."
        >
          {(Object.entries(EVENT_TYPES_BY_CATEGORY) as [EventCategory, readonly string[]][]).map(
            ([category, types]) => (
              <optgroup key={category} label={EVENT_CATEGORY_LABELS[category]}>
                {types.map((type) => (
                  <option key={type} value={type} style={{ backgroundColor: '#2D3748', color: 'white' }}>
                    {EVENT_TYPE_LABELS[type as EventType]}
                  </option>
                ))}
              </optgroup>
            )
          )}
        </Select>
      </FormControl>

      <FormControl isRequired>
        <FormLabel color="orange.300">Deelname</FormLabel>
        <Select
          value={formData.participation}
          onChange={(e) => onChange('participation', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        >
          {Object.entries(PARTICIPATION_MODE_LABELS).map(([value, label]) => (
            <option key={value} value={value} style={{ backgroundColor: '#2D3748', color: 'white' }}>
              {label}
            </option>
          ))}
        </Select>
      </FormControl>

      <FormControl>
        <FormLabel color="orange.300">Publicatiestatus</FormLabel>
        <Select
          value={formData.status || 'draft'}
          onChange={(e) => onChange('status', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        >
          <option value="draft" style={{ backgroundColor: '#2D3748', color: 'white' }}>Draft (niet zichtbaar)</option>
          <option value="published" style={{ backgroundColor: '#2D3748', color: 'white' }}>Published (live)</option>
          <option value="archived" style={{ backgroundColor: '#2D3748', color: 'white' }}>Archived (niet meer actief)</option>
        </Select>
      </FormControl>

      <FormControl isRequired>
        <FormLabel color="orange.300">Regio</FormLabel>
        <Select
          value={formData.linked_regio}
          onChange={(e) => onChange('linked_regio', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
          placeholder="Selecteer regio..."
          isDisabled={allowedRegions.length === 1}
        >
          {availableRegions.map((region) => (
            <option key={region} value={region} style={{ backgroundColor: '#2D3748', color: 'white' }}>
              {region === 'regio_all' ? 'Alle regio\'s (landelijk)' : region}
            </option>
          ))}
        </Select>
      </FormControl>

      <FormControl isRequired>
        <FormLabel color="orange.300">Startdatum</FormLabel>
        <Input
          type="datetime-local"
          value={formData.start_date}
          onChange={(e) => onChange('start_date', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>

      <FormControl isRequired>
        <FormLabel color="orange.300">Einddatum</FormLabel>
        <Input
          type="datetime-local"
          value={formData.end_date}
          onChange={(e) => onChange('end_date', e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>

      <FormControl>
        <FormLabel color="orange.300">Locatie</FormLabel>
        <Input
          value={formData.location}
          onChange={(e) => onChange('location', e.target.value)}
          placeholder="Bijv. Clubhuis H-DCN, Amsterdam"
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>

      <FormControl>
        <FormLabel color="orange.300">Poster / Afbeelding</FormLabel>
        <HStack>
          <Input
            value={formData.poster_url}
            onChange={(e) => onChange('poster_url', e.target.value)}
            placeholder="URL of upload een bestand"
            bg="gray.700"
            borderColor="orange.400"
            flex={1}
          />
          <Button
            size="sm"
            colorScheme="orange"
            variant="outline"
            onClick={() => document.getElementById('poster-upload')?.click()}
            isLoading={isUploading}
          >
            Upload
          </Button>
          <Input
            id="poster-upload"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            display="none"
            onChange={onPosterUpload}
          />
        </HStack>
        {formData.poster_url && (
          <Text fontSize="xs" color="gray.400" mt={1} isTruncated>
            {formData.poster_url}
          </Text>
        )}
      </FormControl>

      <FormControl gridColumn="1 / -1">
        <FormLabel color="orange.300">Beschrijving</FormLabel>
        <Textarea
          value={formData.description}
          onChange={(e) => onChange('description', e.target.value)}
          placeholder="Korte beschrijving van het evenement"
          bg="gray.700"
          borderColor="orange.400"
          rows={3}
        />
      </FormControl>
    </SimpleGrid>
  );
}

export default EventCoreSection;
