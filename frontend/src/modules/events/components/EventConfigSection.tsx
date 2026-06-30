import React from 'react';
import {
  FormControl, FormLabel, Input, Select, Text, SimpleGrid, Box, HStack,
  Checkbox, Spinner, Stack,
} from '@chakra-ui/react';

// ============================================================================
// TYPES
// ============================================================================

interface ProductOption {
  product_id: string;
  naam: string;
  groep?: string;
}

interface EventConfigSectionProps {
  formData: {
    product_ids: string[];
    event_password: string;
    registry_s3_path: string;
    registry_row_label: string;
    registry_claim_mode: string;
    registry_allow_logo_upload: boolean;
  };
  availableProducts: ProductOption[];
  productsLoading: boolean;
  isEditing: boolean;
  onChange: (field: string, value: string) => void;
  onProductIdsChange: (productIds: string[]) => void;
  onRegistryLogoToggle: (checked: boolean) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

function EventConfigSection({
  formData,
  availableProducts,
  productsLoading,
  isEditing,
  onChange,
  onProductIdsChange,
  onRegistryLogoToggle,
}: EventConfigSectionProps) {
  return (
    <>
      <FormControl>
        <FormLabel color="orange.300">Producten koppelen</FormLabel>
        {productsLoading ? (
          <HStack spacing={2}>
            <Spinner size="sm" color="orange.300" />
            <Text color="gray.400" fontSize="sm">Producten laden...</Text>
          </HStack>
        ) : availableProducts.length === 0 ? (
          <Text color="gray.400" fontSize="sm">Geen producten beschikbaar</Text>
        ) : (
          <Box maxH="200px" overflowY="auto" p={2} bg="gray.700" borderRadius="md" borderColor="orange.400" borderWidth="1px">
            <Stack spacing={1}>
              {availableProducts.map(product => (
                <Checkbox
                  key={product.product_id}
                  isChecked={formData.product_ids.includes(product.product_id)}
                  onChange={(e) => {
                    const newIds = e.target.checked
                      ? [...formData.product_ids, product.product_id]
                      : formData.product_ids.filter(id => id !== product.product_id);
                    onProductIdsChange(newIds);
                  }}
                  colorScheme="orange"
                  size="sm"
                >
                  <Text fontSize="sm" color="white">
                    {product.naam}
                    {product.groep && <Text as="span" color="gray.400"> ({product.groep})</Text>}
                  </Text>
                </Checkbox>
              ))}
            </Stack>
          </Box>
        )}
        {formData.product_ids.length > 0 && (
          <Text fontSize="xs" color="gray.400" mt={1}>
            {formData.product_ids.length} product(en) geselecteerd
          </Text>
        )}
      </FormControl>

      <FormControl mt={4}>
        <FormLabel color="orange.300">Event Wachtwoord</FormLabel>
        <Input
          type="password"
          value={formData.event_password}
          onChange={(e) => onChange('event_password', e.target.value)}
          placeholder={isEditing ? '••••••• (laat leeg om niet te wijzigen)' : 'Wachtwoord voor deelnemers'}
          bg="gray.700"
          borderColor="orange.400"
        />
        <Text fontSize="xs" color="gray.400" mt={1}>
          Gedeeld wachtwoord dat deelnemers moeten invoeren om te boeken. Wordt versleuteld opgeslagen.
        </Text>
      </FormControl>

      <Text fontWeight="bold" color="orange.300" mt={6} mb={2}>
        Registry Configuratie
      </Text>

      <SimpleGrid columns={2} spacing={4}>
        <FormControl>
          <FormLabel color="orange.300">S3 Pad (registry JSON)</FormLabel>
          <Input
            value={formData.registry_s3_path}
            onChange={(e) => onChange('registry_s3_path', e.target.value)}
            placeholder="events/{event_id}/invitee_registry.json"
            bg="gray.700"
            borderColor="orange.400"
          />
          <Text fontSize="xs" color="gray.400" mt={1}>
            S3 key naar het JSON bestand met de uitgenodigde rijen.
          </Text>
        </FormControl>

        <FormControl>
          <FormLabel color="orange.300">Rij label</FormLabel>
          <Input
            value={formData.registry_row_label}
            onChange={(e) => onChange('registry_row_label', e.target.value)}
            placeholder="club"
            bg="gray.700"
            borderColor="orange.400"
          />
          <Text fontSize="xs" color="gray.400" mt={1}>
            Hoe een rij heet in de UI (bijv. "club", "team", "chapter").
          </Text>
        </FormControl>

        <FormControl>
          <FormLabel color="orange.300">Claim modus</FormLabel>
          <Select
            value={formData.registry_claim_mode}
            onChange={(e) => onChange('registry_claim_mode', e.target.value)}
            bg="gray.700"
            borderColor="orange.400"
          >
            <option value="first_come_first_served" style={{ backgroundColor: '#2D3748', color: 'white' }}>
              First come, first served
            </option>
            <option value="email_restricted" style={{ backgroundColor: '#2D3748', color: 'white' }}>
              E-mail restricted
            </option>
          </Select>
        </FormControl>

        <FormControl display="flex" alignItems="center" pt={8}>
          <Checkbox
            isChecked={formData.registry_allow_logo_upload}
            onChange={(e) => onRegistryLogoToggle(e.target.checked)}
            colorScheme="orange"
          >
            <Text fontSize="sm" color="white">Logo upload toestaan</Text>
          </Checkbox>
        </FormControl>
      </SimpleGrid>
    </>
  );
}

export default EventConfigSection;
