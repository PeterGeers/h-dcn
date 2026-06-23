import React, { useRef, useState } from 'react';
import {
  VStack,
  HStack,
  FormLabel,
  Input,
  Button,
  IconButton,
  Text,
  Box,
  Spinner,
} from '@chakra-ui/react';
import { DeleteIcon, AddIcon } from '@chakra-ui/icons';
import { uploadEventPoster } from '../services/eventPosterUpload';

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
  const [uploadingIndex, setUploadingIndex] = useState<number | null>(null);
  const fileInputRefs = useRef<Record<number, HTMLInputElement | null>>({});

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

  const handleLogoUpload = async (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    setUploadingIndex(index);
    try {
      const logoName = logos[index].name || `logo-${index}`;
      const result = await uploadEventPoster(file, `landing-logo-${logoName.replace(/[^a-zA-Z0-9]/g, '-')}`);
      handleChange(index, 'logo_url', result.url);
    } catch (error: any) {
      alert(error.message || 'Upload mislukt');
    } finally {
      setUploadingIndex(null);
    }
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
              placeholder="URL of upload →"
              bg="gray.700"
              borderColor="orange.400"
              size="sm"
              flex={2}
            />
            <Button
              size="sm"
              colorScheme="orange"
              variant="outline"
              onClick={() => fileInputRefs.current[index]?.click()}
              isLoading={uploadingIndex === index}
              minW="70px"
            >
              {uploadingIndex === index ? <Spinner size="xs" /> : 'Upload'}
            </Button>
            <input
              ref={(el) => { fileInputRefs.current[index] = el; }}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              style={{ display: 'none' }}
              onChange={(e) => handleLogoUpload(index, e)}
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
