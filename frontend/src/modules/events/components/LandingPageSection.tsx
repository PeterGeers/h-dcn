import React, { useRef, useState } from 'react';
import {
  VStack,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  Textarea,
  Switch,
  HStack,
  Text,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Box,
  Button,
  Divider,
  Tooltip,
  Spinner,
} from '@chakra-ui/react';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import LogosEditor, { LogoEntry } from './LogosEditor';
import SectionsEditor, { SectionEntry } from './SectionsEditor';
import { uploadEventPoster } from '../services/eventPosterUpload';

export interface LandingPageFormData {
  enabled: boolean;
  slug: string;
  hero_image_url: string;
  tagline: string;
  registration_label: string;
  logos: LogoEntry[];
  sections: SectionEntry[];
}

export const DEFAULT_LANDING_PAGE: LandingPageFormData = {
  enabled: false,
  slug: '',
  hero_image_url: '',
  tagline: '',
  registration_label: 'Register Now',
  logos: [],
  sections: [],
};

interface LandingPageSectionProps {
  data: LandingPageFormData;
  onChange: (data: LandingPageFormData) => void;
}

function LandingPageSection({ data, onChange }: LandingPageSectionProps) {
  const [isUploadingHero, setIsUploadingHero] = useState(false);
  const heroInputRef = useRef<HTMLInputElement>(null);

  const handleChange = (field: keyof LandingPageFormData, value: string | boolean) => {
    onChange({ ...data, [field]: value });
  };

  const handleHeroUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    setIsUploadingHero(true);
    try {
      const slug = data.slug || 'landing';
      const result = await uploadEventPoster(file, `landing-hero-${slug}`);
      handleChange('hero_image_url', result.url);
    } catch (error: any) {
      alert(error.message || 'Upload mislukt');
    } finally {
      setIsUploadingHero(false);
    }
  };

  return (
    <Accordion allowToggle>
      <AccordionItem border="1px" borderColor="orange.400" borderRadius="md">
        <AccordionButton bg="gray.700" borderRadius="md" _expanded={{ borderBottomRadius: 0 }}>
          <Box flex="1" textAlign="left">
            <Text fontWeight="semibold" color="orange.300">
              Landingspagina
            </Text>
          </Box>
          <AccordionIcon color="orange.300" />
        </AccordionButton>
        <AccordionPanel pb={4} pt={4} bg="gray.750">
          <VStack spacing={4} align="stretch">
            <FormControl>
              <HStack justify="space-between">
                <FormLabel color="orange.300" mb={0}>Ingeschakeld</FormLabel>
                <Switch
                  colorScheme="orange"
                  isChecked={data.enabled}
                  onChange={(e) => handleChange('enabled', e.target.checked)}
                />
              </HStack>
            </FormControl>

            {data.enabled && data.slug.trim() !== '' && (
              <Tooltip label="Opslaan voordat je een voorbeeld bekijkt" hasArrow>
                <Button
                  as="a"
                  href={`/events/${data.slug}/info`}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="sm"
                  variant="outline"
                  colorScheme="orange"
                  rightIcon={<ExternalLinkIcon />}
                >
                  Voorbeeld bekijken
                </Button>
              </Tooltip>
            )}

            <FormControl>
              <FormLabel color="orange.300">URL-slug</FormLabel>
              <Input
                value={data.slug}
                onChange={(e) => handleChange('slug', e.target.value)}
                placeholder="bijv. presmeet-2027"
                bg="gray.700"
                borderColor="orange.400"
              />
              <FormHelperText color="gray.400">
                De slug moet uniek zijn. Gebruikt voor de URL: /events/{data.slug || '{slug}'}/info
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel color="orange.300">Hero afbeelding</FormLabel>
              <HStack>
                <Input
                  value={data.hero_image_url}
                  onChange={(e) => handleChange('hero_image_url', e.target.value)}
                  placeholder="https://... of upload →"
                  bg="gray.700"
                  borderColor="orange.400"
                  flex={1}
                />
                <Button
                  size="sm"
                  colorScheme="orange"
                  variant="outline"
                  onClick={() => heroInputRef.current?.click()}
                  isLoading={isUploadingHero}
                  minW="100px"
                >
                  {isUploadingHero ? <Spinner size="xs" /> : 'Upload'}
                </Button>
                <input
                  ref={heroInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  style={{ display: 'none' }}
                  onChange={handleHeroUpload}
                />
              </HStack>
              <FormHelperText color="gray.400">
                Max 1920×1080px. Grotere afbeeldingen worden automatisch verkleind.
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel color="orange.300">Tagline</FormLabel>
              <Textarea
                value={data.tagline}
                onChange={(e) => handleChange('tagline', e.target.value)}
                placeholder="Korte pakkende tekst voor de landingspagina"
                bg="gray.700"
                borderColor="orange.400"
                rows={2}
              />
            </FormControl>

            <FormControl>
              <FormLabel color="orange.300">Registratie knoptekst</FormLabel>
              <Input
                value={data.registration_label}
                onChange={(e) => handleChange('registration_label', e.target.value)}
                placeholder="Register Now"
                bg="gray.700"
                borderColor="orange.400"
              />
            </FormControl>

            <Divider borderColor="gray.600" />

            <LogosEditor
              logos={data.logos}
              onChange={(logos) => onChange({ ...data, logos })}
            />

            <Divider borderColor="gray.600" />

            <SectionsEditor
              sections={data.sections}
              onChange={(sections) => onChange({ ...data, sections })}
            />
          </VStack>
        </AccordionPanel>
      </AccordionItem>
    </Accordion>
  );
}

export default LandingPageSection;
