import React from 'react';
import {
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Button,
  IconButton,
  Text,
  Box,
  Divider,
} from '@chakra-ui/react';
import { DeleteIcon, AddIcon } from '@chakra-ui/icons';
import LogosEditor, { LogoEntry } from './LogosEditor';

export interface SectionEntry {
  type: string;
  title: string;
  content?: string;
  items?: LogoEntry[];
}

interface SectionsEditorProps {
  sections: SectionEntry[];
  onChange: (sections: SectionEntry[]) => void;
}

function SectionsEditor({ sections, onChange }: SectionsEditorProps) {
  const handleAdd = (type: string) => {
    const newSection: SectionEntry = type === 'logos'
      ? { type: 'logos', title: '', items: [] }
      : { type: 'text', title: '', content: '' };
    onChange([...sections, newSection]);
  };

  const handleRemove = (index: number) => {
    onChange(sections.filter((_, i) => i !== index));
  };

  const handleFieldChange = (index: number, field: string, value: string) => {
    const updated = sections.map((section, i) =>
      i === index ? { ...section, [field]: value } : section
    );
    onChange(updated);
  };

  const handleItemsChange = (index: number, items: LogoEntry[]) => {
    const updated = sections.map((section, i) =>
      i === index ? { ...section, items } : section
    );
    onChange(updated);
  };

  return (
    <Box>
      <FormLabel color="orange.300" mb={2}>Secties</FormLabel>
      <VStack spacing={3} align="stretch">
        {sections.length === 0 && (
          <Text fontSize="sm" color="gray.500" fontStyle="italic">
            Geen secties toegevoegd.
          </Text>
        )}
        {sections.map((section, index) => (
          <Box
            key={index}
            p={3}
            borderWidth="1px"
            borderColor="gray.600"
            borderRadius="md"
            bg="gray.800"
          >
            <HStack justify="space-between" mb={2}>
              <Text fontSize="sm" color="orange.200" fontWeight="medium">
                Sectie {index + 1} — {section.type === 'logos' ? "Logo's" : 'Tekst'}
              </Text>
              <IconButton
                aria-label="Verwijder sectie"
                icon={<DeleteIcon />}
                size="xs"
                colorScheme="red"
                variant="ghost"
                onClick={() => handleRemove(index)}
              />
            </HStack>

            <VStack spacing={2} align="stretch">
              <FormControl>
                <Input
                  value={section.title}
                  onChange={(e) => handleFieldChange(index, 'title', e.target.value)}
                  placeholder="Titel"
                  bg="gray.700"
                  borderColor="orange.400"
                  size="sm"
                />
              </FormControl>

              {section.type === 'text' && (
                <FormControl>
                  <Textarea
                    value={section.content || ''}
                    onChange={(e) => handleFieldChange(index, 'content', e.target.value)}
                    placeholder="Inhoud (tekst of HTML)"
                    bg="gray.700"
                    borderColor="orange.400"
                    size="sm"
                    rows={3}
                  />
                </FormControl>
              )}

              {section.type === 'logos' && (
                <LogosEditor
                  logos={section.items || []}
                  onChange={(items) => handleItemsChange(index, items)}
                  label="Items"
                />
              )}
            </VStack>
          </Box>
        ))}

        <Divider borderColor="gray.600" />

        <HStack spacing={2}>
          <Button
            leftIcon={<AddIcon />}
            size="sm"
            variant="outline"
            colorScheme="orange"
            onClick={() => handleAdd('text')}
          >
            Tekstsectie toevoegen
          </Button>
          <Button
            leftIcon={<AddIcon />}
            size="sm"
            variant="outline"
            colorScheme="orange"
            onClick={() => handleAdd('logos')}
          >
            Logo-sectie toevoegen
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}

export default SectionsEditor;
