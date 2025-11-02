import React, { useState } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Input,
  FormControl,
  FormLabel,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  useToast
} from '@chakra-ui/react';

interface ColorEnhanceToolProps {
  onClose: () => void;
}

export default function ColorEnhanceTool({ onClose }: ColorEnhanceToolProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [brightness, setBrightness] = useState(1);
  const [contrast, setContrast] = useState(1);
  const [saturation, setSaturation] = useState(1);
  const [fileName, setFileName] = useState('enhanced-image');
  const toast = useToast();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImageUrl(url);
    }
  };

  const enhanceColors = () => {
    if (!selectedFile) return;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      
      ctx.drawImage(img, 0, 0);
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imageData.data;

      for (let i = 0; i < data.length; i += 4) {
        let r = data[i] / 255;
        let g = data[i + 1] / 255;
        let b = data[i + 2] / 255;

        // Apply brightness
        r *= brightness;
        g *= brightness;
        b *= brightness;

        // Apply contrast
        r = (r - 0.5) * contrast + 0.5;
        g = (g - 0.5) * contrast + 0.5;
        b = (b - 0.5) * contrast + 0.5;

        // Apply saturation
        const gray = 0.299 * r + 0.587 * g + 0.114 * b;
        r = gray + saturation * (r - gray);
        g = gray + saturation * (g - gray);
        b = gray + saturation * (b - gray);

        // Convert back and clamp
        data[i] = Math.max(0, Math.min(255, Math.round(r * 255)));
        data[i + 1] = Math.max(0, Math.min(255, Math.round(g * 255)));
        data[i + 2] = Math.max(0, Math.min(255, Math.round(b * 255)));
      }
      
      ctx.putImageData(imageData, 0, 0);

      canvas.toBlob((blob: Blob | null) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${fileName}.jpg`;
        a.click();
        URL.revokeObjectURL(url);
        
        toast({
          title: 'Kleur-verbeterde afbeelding opgeslagen!',
          status: 'success',
          duration: 3000,
        });
      }, 'image/jpeg', 0.9);
    };
    
    img.src = imageUrl;
  };

  return (
    <Box p={6} bg="black" minHeight="100vh">
      <VStack spacing={6} align="center">
        <HStack>
          <Button onClick={onClose} variant="ghost" color="orange.300" _hover={{ bg: "gray.800" }}>
            ← Terug
          </Button>
          <Text fontSize="2xl" fontWeight="bold" color="orange.400">
            🎨 Kleur Verbeteren
          </Text>
        </HStack>

        <VStack spacing={4}>
          <FormControl>
            <FormLabel color="orange.300">Selecteer afbeelding</FormLabel>
            <Input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              bg="gray.800"
              color="orange.200"
              borderColor="orange.400"
            />
          </FormControl>

          {imageUrl && (
            <Box textAlign="center">
              <img
                src={imageUrl}
                alt="Preview"
                style={{
                  maxWidth: '400px',
                  maxHeight: '400px',
                  border: '2px solid #e2e8f0',
                  borderRadius: '8px'
                }}
              />
            </Box>
          )}

          {imageUrl && (
            <VStack spacing={4} width="400px">
              <FormControl>
                <FormLabel color="orange.300">Helderheid: {brightness.toFixed(1)}</FormLabel>
                <Slider
                  value={brightness}
                  onChange={setBrightness}
                  min={0.1}
                  max={3}
                  step={0.1}
                  colorScheme="orange"
                >
                  <SliderTrack>
                    <SliderFilledTrack />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Contrast: {contrast.toFixed(1)}</FormLabel>
                <Slider
                  value={contrast}
                  onChange={setContrast}
                  min={0.1}
                  max={3}
                  step={0.1}
                  colorScheme="orange"
                >
                  <SliderTrack>
                    <SliderFilledTrack />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Verzadiging: {saturation.toFixed(1)}</FormLabel>
                <Slider
                  value={saturation}
                  onChange={setSaturation}
                  min={0}
                  max={3}
                  step={0.1}
                  colorScheme="orange"
                >
                  <SliderTrack>
                    <SliderFilledTrack />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
              </FormControl>

              <HStack spacing={4}>
                <FormControl width="200px">
                  <FormLabel color="orange.300">Bestandsnaam</FormLabel>
                  <Input
                    value={fileName}
                    onChange={(e) => setFileName(e.target.value)}
                    bg="gray.800"
                    color="orange.200"
                    borderColor="orange.400"
                  />
                </FormControl>
                <Button
                  colorScheme="orange"
                  onClick={enhanceColors}
                  size="lg"
                >
                  Verbeteren & Opslaan
                </Button>
              </HStack>
            </VStack>
          )}
        </VStack>
      </VStack>
    </Box>
  );
}