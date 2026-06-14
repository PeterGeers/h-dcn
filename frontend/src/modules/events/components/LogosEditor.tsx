import React from 'react';
import {
  VStack,
  HStack,
  FormLabel,
  Input,
  Button,
  IconButton,
  Text,
  Box,
} from '@chakra-ui/react';
import { DeleteIcon, AddIcon } from '@chakra-ui/icons';

export interface LogoEntry {
  name: string;
  logo_url: string;
}

interface LogosEditorProps {
  logos: LogoEntry[];
  onChange: (logos: LogoEntry[]) => void;
  label?: string;
}

function LogosEditor({ logos, onChange, label = "Logo's" }: LogosEditorProps) {
  const handleAdd = () => {
    onChange([...logos, { name: '', logo_url: '' }]);
  };

  const handleRemove = (index: number) => {
    onChange(logos.filter((_, i) => i !== index));
  };

  const handleChange = (index: number, field: keyof LogoEntry, value: string) => {
    const updated = logos.map((logo, i) =>
      i === index ? { ...logo, [field]: value } : logo
    );
    onChange(updated);
  };

  return (
    <Box>
      <FormLabel color="orange.300" mb={2}>{label}</FormLabel>
      <VStack spacing={2} align="stretch">
        {logos.length === 0 && (
          <Text fontSize="sm" color="gray.500" fontStyle="italic">
            Geen logo's toegevoegd.
          </Text>
        )}
        {logos.map((logo, index) => (
          <HStack key={index} spacing={2}>
            <Input
              value={logo.name}
              onChange={(e) => handleChange(index, 'name', e.target.value)}
              placeholder="Naam"
              bg="gray.700"
              borderColor="orange.400"
              size="sm"
              flex={1}
            />
            <Input
              value={logo.logo_url}
              onChange={(e) => handleChange(index, 'logo_url', e.target.value)}
              placeholder="Logo URL"
              bg="gray.700"
              borderColor="orange.400"
              size="sm"
              flex={2}
            />
            <IconButton
              aria-label="Verwijder logo"
              icon={<DeleteIcon />}
              size="sm"
              colorScheme="red"
              variant="ghost"
              onClick={() => handleRemove(index)}
            />
          </HStack>
        ))}
        <Button
          leftIcon={<AddIcon />}
          size="sm"
          variant="outline"
          colorScheme="orange"
          onClick={handleAdd}
          alignSelf="flex-start"
        >
          Logo toevoegen
        </Button>
      </VStack>
    </Box>
  );
}

export default LogosEditor;
