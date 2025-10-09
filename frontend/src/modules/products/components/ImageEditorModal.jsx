import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Checkbox,
  FormControl,
  FormLabel,
  Image,
  useToast
} from '@chakra-ui/react';
import { ImageProcessor } from '../services/imageProcessor';

export default function ImageEditorModal({ isOpen, onClose, imageUrl, onSave }) {
  const [processedUrl, setProcessedUrl] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const toast = useToast();

  // Processing parameters
  const [params, setParams] = useState({
    enableResize: false,
    resizeMode: 'percentage',
    resizeWidth: 800,
    resizeHeight: 600,
    resizePercentage: 50,
    
    enableCrop: false,
    cropX: 0,
    cropY: 0,
    cropWidth: 400,
    cropHeight: 300,
    
    enableTransparency: false,
    transparencyColor: '#ffffff',
    tolerance: 10,
    removeBackground: false,
    
    enableColorAdjust: false,
    brightness: 1,
    saturation: 1,
    contrast: 1,
    
    outputFormat: 'png',
    quality: 0.9
  });

  // Load image dimensions when modal opens
  useEffect(() => {
    if (isOpen && imageUrl) {
      const img = new window.Image();
      img.onload = () => {
        setImageDimensions({ width: img.width, height: img.height });
        setParams(prev => ({
          ...prev,
          resizeWidth: img.width,
          resizeHeight: img.height,
          cropWidth: Math.min(400, img.width),
          cropHeight: Math.min(300, img.height)
        }));
      };
      img.crossOrigin = 'anonymous';
      img.src = imageUrl;
    }
  }, [isOpen, imageUrl]);

  const processImage = async () => {
    if (!imageUrl) {
      toast({
        title: 'Geen afbeelding gevonden',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    setProcessing(true);
    try {
      // Fetch image as blob to bypass CORS
      const response = await fetch(imageUrl, { mode: 'cors' });
      if (!response.ok) {
        throw new Error('Failed to fetch image');
      }
      const blob = await response.blob();
      const file = new File([blob], 'image.jpg', { type: blob.type });
      
      const processor = new ImageProcessor();
      const options = {};
      
      if (params.enableResize) {
        if (params.resizeMode === 'percentage') {
          const scale = params.resizePercentage / 100;
          options.resize = {
            width: Math.round(imageDimensions.width * scale),
            height: Math.round(imageDimensions.height * scale)
          };
        } else {
          options.resize = {
            width: params.resizeWidth,
            height: params.resizeHeight
          };
        }
      }
      
      if (params.enableCrop) {
        options.crop = {
          x: params.cropX,
          y: params.cropY,
          width: params.cropWidth,
          height: params.cropHeight
        };
      }
      
      if (params.enableTransparency) {
        options.transparency = {
          color: params.transparencyColor,
          tolerance: params.tolerance,
          removeBackground: params.removeBackground
        };
      }
      
      if (params.enableColorAdjust) {
        options.colorAdjust = {
          brightness: params.brightness,
          saturation: params.saturation,
          contrast: params.contrast
        };
      }
      
      options.outputFormat = params.outputFormat;
      options.quality = params.quality;

      const processedBlob = await processor.processImage(file, options);
      const url = URL.createObjectURL(processedBlob);
      setProcessedUrl(url);

      toast({
        title: 'Afbeelding succesvol bewerkt!',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Processing error:', error);
      
      if (error.message.includes('CORS') || error.message.includes('Failed to fetch')) {
        toast({
          title: 'CORS Fout',
          description: 'S3 bucket moet CORS instellingen hebben voor image editing. Neem contact op met de beheerder.',
          status: 'error',
          duration: 8000,
        });
      } else {
        toast({
          title: 'Fout bij bewerken',
          description: error.message || 'Onbekende fout opgetreden',
          status: 'error',
          duration: 5000,
        });
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleSave = () => {
    if (processedUrl && onSave) {
      onSave(processedUrl);
      onClose();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl">
      <ModalOverlay bg="blackAlpha.800" />
      <ModalContent maxHeight="90vh" overflowY="auto" bg="gray.800" color="white">
        <ModalHeader bg="gray.700">
          <HStack>
            <Image 
              src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" 
              alt="H-DCN Logo" 
              boxSize="30px" 
            />
            <Text color="white">Image Editor</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton color="white" />
        <ModalBody pb={6} bg="gray.800">
          <VStack spacing={6} align="stretch">
            {/* Preview */}
            <HStack spacing={6} align="start">
              <Box>
                <Text fontWeight="bold" mb={2}>Origineel</Text>
                <Image src={imageUrl} maxH="200px" border="1px solid gray" />
              </Box>
              {processedUrl && (
                <Box>
                  <Text fontWeight="bold" mb={2}>Bewerkt</Text>
                  <Image src={processedUrl} maxH="200px" border="1px solid gray" />
                </Box>
              )}
            </HStack>

            {/* Resize options */}
            <Box p={4} border="1px solid" borderColor="gray.600" borderRadius="md" bg="gray.700">
              <Checkbox
                isChecked={params.enableResize}
                onChange={(e) => setParams({...params, enableResize: e.target.checked})}
                mb={3}
                colorScheme="orange"
              >
                <Text fontWeight="bold" color="white">Verkleinen</Text>
              </Checkbox>
              <Text fontSize="sm" color="gray.300" mb={2}>
                {imageDimensions.width > 0 
                  ? `Huidige afmetingen: ${imageDimensions.width} x ${imageDimensions.height} pixels`
                  : ''
                }
              </Text>
              {params.enableResize && (
                <FormControl>
                  <FormLabel color="white">Schaal: {params.resizePercentage}%</FormLabel>
                  <Slider
                    value={params.resizePercentage}
                    onChange={(val) => setParams({...params, resizePercentage: val})}
                    min={10}
                    max={200}
                    step={5}
                    colorScheme="orange"
                  >
                    <SliderTrack bg="gray.600">
                      <SliderFilledTrack bg="orange.400" />
                    </SliderTrack>
                    <SliderThumb bg="orange.500" />
                  </Slider>
                  {imageDimensions.width > 0 && (
                    <Text fontSize="sm" color="gray.300" mt={1}>
                      Nieuwe afmetingen: {Math.round(imageDimensions.width * params.resizePercentage / 100)} x {Math.round(imageDimensions.height * params.resizePercentage / 100)} pixels
                    </Text>
                  )}
                </FormControl>
              )}
            </Box>

            {/* Color adjustment */}
            <Box p={4} border="1px solid" borderColor="gray.600" borderRadius="md" bg="gray.700">
              <Checkbox
                isChecked={params.enableColorAdjust}
                onChange={(e) => setParams({...params, enableColorAdjust: e.target.checked})}
                mb={3}
                colorScheme="orange"
              >
                <Text fontWeight="bold" color="white">Kleurcorrectie</Text>
              </Checkbox>
              {params.enableColorAdjust && (
                <VStack spacing={4}>
                  <FormControl>
                    <FormLabel color="white">Helderheid: {params.brightness.toFixed(1)}</FormLabel>
                    <Slider
                      value={params.brightness}
                      onChange={(val) => setParams({...params, brightness: val})}
                      min={0.1}
                      max={3}
                      step={0.1}
                      colorScheme="orange"
                    >
                      <SliderTrack bg="gray.600">
                        <SliderFilledTrack bg="orange.400" />
                      </SliderTrack>
                      <SliderThumb bg="orange.500" />
                    </Slider>
                  </FormControl>
                  <FormControl>
                    <FormLabel color="white">Verzadiging: {params.saturation.toFixed(1)}</FormLabel>
                    <Slider
                      value={params.saturation}
                      onChange={(val) => setParams({...params, saturation: val})}
                      min={0}
                      max={3}
                      step={0.1}
                      colorScheme="orange"
                    >
                      <SliderTrack bg="gray.600">
                        <SliderFilledTrack bg="orange.400" />
                      </SliderTrack>
                      <SliderThumb bg="orange.500" />
                    </Slider>
                  </FormControl>
                  <FormControl>
                    <FormLabel color="white">Contrast: {params.contrast.toFixed(1)}</FormLabel>
                    <Slider
                      value={params.contrast}
                      onChange={(val) => setParams({...params, contrast: val})}
                      min={0.1}
                      max={3}
                      step={0.1}
                      colorScheme="orange"
                    >
                      <SliderTrack bg="gray.600">
                        <SliderFilledTrack bg="orange.400" />
                      </SliderTrack>
                      <SliderThumb bg="orange.500" />
                    </Slider>
                  </FormControl>
                </VStack>
              )}
            </Box>

            {/* Crop */}
            <Box p={4} border="1px solid" borderColor="gray.600" borderRadius="md" bg="gray.700">
              <Checkbox
                isChecked={params.enableCrop}
                onChange={(e) => setParams({...params, enableCrop: e.target.checked})}
                mb={3}
                colorScheme="orange"
              >
                <Text fontWeight="bold" color="white">Bijsnijden</Text>
              </Checkbox>
              {params.enableCrop && (
                <VStack spacing={3}>
                  <HStack>
                    <FormControl>
                      <FormLabel color="white">X: {params.cropX}</FormLabel>
                      <Slider
                        value={params.cropX}
                        onChange={(val) => setParams({...params, cropX: val})}
                        min={0}
                        max={imageDimensions.width || 1000}
                        colorScheme="orange"
                      >
                        <SliderTrack bg="gray.600">
                          <SliderFilledTrack bg="orange.400" />
                        </SliderTrack>
                        <SliderThumb bg="orange.500" />
                      </Slider>
                    </FormControl>
                    <FormControl>
                      <FormLabel color="white">Y: {params.cropY}</FormLabel>
                      <Slider
                        value={params.cropY}
                        onChange={(val) => setParams({...params, cropY: val})}
                        min={0}
                        max={imageDimensions.height || 1000}
                        colorScheme="orange"
                      >
                        <SliderTrack bg="gray.600">
                          <SliderFilledTrack bg="orange.400" />
                        </SliderTrack>
                        <SliderThumb bg="orange.500" />
                      </Slider>
                    </FormControl>
                  </HStack>
                  <HStack>
                    <FormControl>
                      <FormLabel color="white">Breedte: {params.cropWidth}</FormLabel>
                      <Slider
                        value={params.cropWidth}
                        onChange={(val) => setParams({...params, cropWidth: val})}
                        min={50}
                        max={imageDimensions.width || 1000}
                        colorScheme="orange"
                      >
                        <SliderTrack bg="gray.600">
                          <SliderFilledTrack bg="orange.400" />
                        </SliderTrack>
                        <SliderThumb bg="orange.500" />
                      </Slider>
                    </FormControl>
                    <FormControl>
                      <FormLabel color="white">Hoogte: {params.cropHeight}</FormLabel>
                      <Slider
                        value={params.cropHeight}
                        onChange={(val) => setParams({...params, cropHeight: val})}
                        min={50}
                        max={imageDimensions.height || 1000}
                        colorScheme="orange"
                      >
                        <SliderTrack bg="gray.600">
                          <SliderFilledTrack bg="orange.400" />
                        </SliderTrack>
                        <SliderThumb bg="orange.500" />
                      </Slider>
                    </FormControl>
                  </HStack>
                </VStack>
              )}
            </Box>

            {/* Transparency */}
            <Box p={4} border="1px solid" borderColor="gray.600" borderRadius="md" bg="gray.700">
              <Checkbox
                isChecked={params.enableTransparency}
                onChange={(e) => setParams({...params, enableTransparency: e.target.checked})}
                mb={3}
                colorScheme="orange"
              >
                <Text fontWeight="bold" color="white">Transparantie</Text>
              </Checkbox>
              {params.enableTransparency && (
                <VStack spacing={3}>
                  <FormControl>
                    <FormLabel color="white">Tolerantie: {params.tolerance}</FormLabel>
                    <Slider
                      value={params.tolerance}
                      onChange={(val) => setParams({...params, tolerance: val})}
                      min={0}
                      max={50}
                      colorScheme="orange"
                    >
                      <SliderTrack bg="gray.600">
                        <SliderFilledTrack bg="orange.400" />
                      </SliderTrack>
                      <SliderThumb bg="orange.500" />
                    </Slider>
                  </FormControl>
                  <Checkbox
                    isChecked={params.removeBackground}
                    onChange={(e) => setParams({...params, removeBackground: e.target.checked})}
                    colorScheme="orange"
                  >
                    <Text color="white">Achtergrond verwijderen</Text>
                  </Checkbox>
                </VStack>
              )}
            </Box>

            {/* Action Buttons */}
            <HStack spacing={4} justify="center">
              <Button
                colorScheme="blue"
                onClick={processImage}
                isLoading={processing}
                loadingText="Bewerken..."
              >
                Bewerk Afbeelding
              </Button>
              <Button
                colorScheme="green"
                onClick={handleSave}
                isDisabled={!processedUrl}
              >
                Opslaan
              </Button>
              <Button onClick={onClose}>
                Annuleren
              </Button>
            </HStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}