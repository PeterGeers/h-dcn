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

export default function BackgroundRemovalTool({ onClose }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [tolerance, setTolerance] = useState(20);
  const [fileName, setFileName] = useState('no-background');
  const toast = useToast();

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImageUrl(url);
    }
  };

  const removeBackground = () => {
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
      
      // Get corner colors for background detection
      const corners = [
        [0, 0], // top-left
        [canvas.width - 1, 0], // top-right
        [0, canvas.height - 1], // bottom-left
        [canvas.width - 1, canvas.height - 1] // bottom-right
      ];
      
      let avgR = 0, avgG = 0, avgB = 0;
      corners.forEach(([x, y]) => {
        const index = (y * canvas.width + x) * 4;
        avgR += data[index];
        avgG += data[index + 1];
        avgB += data[index + 2];
      });
      
      const bgR = avgR / 4;
      const bgG = avgG / 4;
      const bgB = avgB / 4;

      // Remove background
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];

        const distance = Math.sqrt(
          Math.pow(r - bgR, 2) +
          Math.pow(g - bgG, 2) +
          Math.pow(b - bgB, 2)
        );

        if (distance <= tolerance) {
          data[i + 3] = 0; // Make transparent
        }
      }
      
      ctx.putImageData(imageData, 0, 0);

      canvas.toBlob((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${fileName}.png`;
        a.click();
        URL.revokeObjectURL(url);
        
        toast({
          title: 'Achtergrond verwijderd en opgeslagen als PNG!',
          status: 'success',
          duration: 3000,
        });
      }, 'image/png');
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
            🎭 Achtergrond Verwijderen
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
              <Text fontSize="sm" color="orange.300" mt={2}>
                Achtergrond wordt automatisch gedetecteerd aan de hoeken
              </Text>
            </Box>
          )}

          {imageUrl && (
            <VStack spacing={4} width="400px">
              <FormControl>
                <FormLabel color="orange.300">Tolerantie: {tolerance}</FormLabel>
                <Slider
                  value={tolerance}
                  onChange={setTolerance}
                  min={0}
                  max={100}
                  step={5}
                  colorScheme="purple"
                >
                  <SliderTrack>
                    <SliderFilledTrack />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
                <Text fontSize="xs" color="orange.300">
                  Hogere waarde = meer achtergrond wordt verwijderd
                </Text>
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
                  colorScheme="purple"
                  onClick={removeBackground}
                  size="lg"
                >
                  Verwijderen & Opslaan PNG
                </Button>
              </HStack>
            </VStack>
          )}
        </VStack>
      </VStack>
    </Box>
  );
}