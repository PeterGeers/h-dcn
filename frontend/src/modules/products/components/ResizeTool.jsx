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

export default function ResizeTool({ onClose }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [resizePercentage, setResizePercentage] = useState(100);
  const [fileName, setFileName] = useState('resized-image');
  const toast = useToast();

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImageUrl(url);
      
      const img = new Image();
      img.onload = () => {
        setImageDimensions({ width: img.width, height: img.height });
      };
      img.src = url;
    }
  };

  const applyResize = () => {
    if (!selectedFile) return;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
      const newWidth = Math.round(img.width * resizePercentage / 100);
      const newHeight = Math.round(img.height * resizePercentage / 100);
      
      canvas.width = newWidth;
      canvas.height = newHeight;
      
      ctx.drawImage(img, 0, 0, newWidth, newHeight);

      canvas.toBlob((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${fileName}.jpg`;
        a.click();
        URL.revokeObjectURL(url);
        
        toast({
          title: 'Verkleinde afbeelding opgeslagen!',
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
            📏 Verkleinen
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
                Origineel: {imageDimensions.width} x {imageDimensions.height} pixels
              </Text>
              <Text fontSize="sm" color="orange.200">
                Nieuw: {Math.round(imageDimensions.width * resizePercentage / 100)} x {Math.round(imageDimensions.height * resizePercentage / 100)} pixels
              </Text>
            </Box>
          )}

          {imageUrl && (
            <VStack spacing={4} width="400px">
              <FormControl>
                <FormLabel color="orange.300">Schaal: {resizePercentage}%</FormLabel>
                <Slider
                  value={resizePercentage}
                  onChange={setResizePercentage}
                  min={10}
                  max={200}
                  step={5}
                  colorScheme="blue"
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
                  colorScheme="blue"
                  onClick={applyResize}
                  size="lg"
                >
                  Verkleinen & Opslaan
                </Button>
              </HStack>
            </VStack>
          )}
        </VStack>
      </VStack>
    </Box>
  );
}