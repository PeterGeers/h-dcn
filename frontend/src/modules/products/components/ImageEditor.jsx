import React, { useState } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Input,
  Text,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Checkbox,
  FormControl,
  FormLabel,
  Image,
  Select,
  useToast
} from '@chakra-ui/react';
import { ImageProcessor } from '../services/imageProcessor';

export default function ImageEditor() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [processedUrl, setProcessedUrl] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [downloadFilename, setDownloadFilename] = useState('processed-image');
  const [downloadFormat, setDownloadFormat] = useState('jpg');
  const toast = useToast();

  // Processing parameters
  const [params, setParams] = useState({
    // Resize
    enableResize: false,
    resizeMode: 'pixels', // 'pixels' or 'percentage'
    resizeWidth: 800,
    resizeHeight: 600,
    resizePercentage: 50,
    
    // Crop
    enableCrop: false,
    cropX: 0,
    cropY: 0,
    cropWidth: 400,
    cropHeight: 300,
    
    // Transparency
    enableTransparency: false,
    transparencyColor: '#ffffff',
    tolerance: 10,
    removeBackground: false,
    
    // Color adjustment
    enableColorAdjust: false,
    brightness: 1,
    saturation: 1,
    contrast: 1,
    
    // Rotation
    enableRotation: false,
    rotation: 0,
    
    // Output
    outputFormat: 'png',
    quality: 0.9
  });

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setProcessedUrl(null);
      
      // Get image dimensions using window.Image to avoid Chakra UI conflict
      const img = new window.Image();
      img.onload = () => {
        console.log('Image loaded:', img.width, 'x', img.height);
        setImageDimensions({ width: img.width, height: img.height });
        // Auto-fill resize fields with current dimensions
        setParams(prev => ({
          ...prev,
          resizeWidth: img.width,
          resizeHeight: img.height,
          cropWidth: Math.min(400, img.width),
          cropHeight: Math.min(300, img.height)
        }));
      };
      img.onerror = (e) => console.error('Image load error:', e);
      img.src = url;
    }
  };

  const processImage = async () => {
    if (!selectedFile) {
      toast({
        title: 'Geen bestand geselecteerd',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setProcessing(true);
    try {
      const processor = new ImageProcessor();
      
      const options = {};
      
      // Resize
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
      
      // Crop
      if (params.enableCrop) {
        options.crop = {
          x: params.cropX,
          y: params.cropY,
          width: params.cropWidth,
          height: params.cropHeight
        };
      }
      
      // Transparency
      if (params.enableTransparency) {
        options.transparency = {
          color: params.transparencyColor,
          tolerance: params.tolerance,
          removeBackground: params.removeBackground
        };
      }
      
      // Color adjustment
      if (params.enableColorAdjust) {
        options.colorAdjust = {
          brightness: params.brightness,
          saturation: params.saturation,
          contrast: params.contrast
        };
      }
      
      // Rotation
      if (params.enableRotation && params.rotation !== 0) {
        options.rotation = params.rotation;
      }
      
      options.outputFormat = params.outputFormat;
      options.quality = params.quality;

      const processedBlob = await processor.processImage(selectedFile, options);
      const url = URL.createObjectURL(processedBlob);
      setProcessedUrl(url);

      toast({
        title: 'Afbeelding succesvol bewerkt!',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Processing error:', error);
      toast({
        title: 'Fout bij bewerken',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setProcessing(false);
    }
  };

  const downloadImage = () => {
    if (processedUrl) {
      const a = document.createElement('a');
      a.href = processedUrl;
      a.download = `${downloadFilename}.${downloadFormat}`;
      a.click();
    }
  };

  return (
    <Box p={6} maxWidth="1200px" mx="auto">
      <HStack mb={6}>
        <Image 
          src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" 
          alt="H-DCN Logo" 
          boxSize="40px" 
        />
        <Text fontSize="2xl" fontWeight="bold">
          Image Editor
        </Text>
      </HStack>

      {/* File Upload */}
      <VStack spacing={6} align="stretch">
        <FormControl>
          <FormLabel>Selecteer afbeelding</FormLabel>
          <Input
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            p={1}
          />
        </FormControl>

        {/* Preview */}
        {previewUrl && (
          <HStack spacing={6} align="start">
            <Box>
              <Text fontWeight="bold" mb={2}>Origineel</Text>
              <Box position="relative" display="inline-block">
                <Image src={previewUrl} maxH="300px" border="1px solid gray" />
                {params.enableCrop && (
                  <Box
                    position="absolute"
                    top={0}
                    left={0}
                    width="100%"
                    height="100%"
                    pointerEvents="none"
                  >
                    <Box
                      position="absolute"
                      border="2px solid red"
                      backgroundColor="rgba(255,0,0,0.1)"
                      style={{
                        left: `${(params.cropX / imageDimensions.width) * 100}%`,
                        top: `${(params.cropY / imageDimensions.height) * 100}%`,
                        width: `${(params.cropWidth / imageDimensions.width) * 100}%`,
                        height: `${(params.cropHeight / imageDimensions.height) * 100}%`
                      }}
                    />
                  </Box>
                )}
              </Box>
            </Box>
            {processedUrl && (
              <Box>
                <Text fontWeight="bold" mb={2}>Bewerkt</Text>
                <Image src={processedUrl} maxH="300px" border="1px solid gray" />
              </Box>
            )}
          </HStack>
        )}

        {/* Processing Options */}
        <VStack spacing={4} align="stretch">
          {/* Resize */}
          <Box p={4} border="1px solid gray" borderRadius="md">
            <Checkbox
              isChecked={params.enableResize}
              onChange={(e) => setParams({...params, enableResize: e.target.checked})}
              mb={3}
            >
              <Text fontWeight="bold">Verkleinen</Text>
            </Checkbox>
            <Text fontSize="sm" color="gray.400" mb={2}>
              {imageDimensions.width > 0 
                ? `Huidige afmetingen: ${imageDimensions.width} x ${imageDimensions.height} pixels`
                : `Debug: width=${imageDimensions.width}, height=${imageDimensions.height}`
              }
            </Text>
            {params.enableResize && (
              <VStack spacing={3}>
                <HStack>
                  <Button
                    size="sm"
                    colorScheme={params.resizeMode === 'pixels' ? 'blue' : 'gray'}
                    onClick={() => setParams({...params, resizeMode: 'pixels'})}
                  >
                    Pixels
                  </Button>
                  <Button
                    size="sm"
                    colorScheme={params.resizeMode === 'percentage' ? 'blue' : 'gray'}
                    onClick={() => setParams({...params, resizeMode: 'percentage'})}
                  >
                    Percentage
                  </Button>
                </HStack>
                
                {params.resizeMode === 'pixels' ? (
                  <HStack>
                    <FormControl>
                      <FormLabel>Breedte</FormLabel>
                      <Input
                        type="number"
                        value={params.resizeWidth}
                        onChange={(e) => setParams({...params, resizeWidth: parseInt(e.target.value)})}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel>Hoogte</FormLabel>
                      <Input
                        type="number"
                        value={params.resizeHeight}
                        onChange={(e) => setParams({...params, resizeHeight: parseInt(e.target.value)})}
                      />
                    </FormControl>
                  </HStack>
                ) : (
                  <FormControl>
                    <FormLabel>Schaal: {params.resizePercentage}%</FormLabel>
                    <HStack>
                      <Slider
                        value={params.resizePercentage}
                        onChange={(val) => setParams({...params, resizePercentage: val})}
                        min={10}
                        max={200}
                        step={5}
                        flex={1}
                      >
                        <SliderTrack>
                          <SliderFilledTrack />
                        </SliderTrack>
                        <SliderThumb />
                      </Slider>
                      <Input
                        type="number"
                        value={params.resizePercentage}
                        onChange={(e) => setParams({...params, resizePercentage: parseInt(e.target.value)})}
                        width="80px"
                        min={10}
                        max={200}
                      />
                    </HStack>
                    {imageDimensions.width > 0 && (
                      <Text fontSize="sm" color="gray.600" mt={1}>
                        Nieuwe afmetingen: {Math.round(imageDimensions.width * params.resizePercentage / 100)} x {Math.round(imageDimensions.height * params.resizePercentage / 100)} pixels
                      </Text>
                    )}
                  </FormControl>
                )}
              </VStack>
            )}
          </Box>

          {/* Crop */}
          <Box p={4} border="1px solid gray" borderRadius="md">
            <Checkbox
              isChecked={params.enableCrop}
              onChange={(e) => setParams({...params, enableCrop: e.target.checked})}
              mb={3}
            >
              <Text fontWeight="bold">Bijsnijden</Text>
            </Checkbox>
            {params.enableCrop && (
              <HStack spacing={4}>
                <FormControl flex={1}>
                  <FormLabel>X-as: {params.cropX}</FormLabel>
                  <Slider
                    value={params.cropX}
                    onChange={(val) => setParams({...params, cropX: val})}
                    min={0}
                    max={imageDimensions.width - params.cropWidth}
                  >
                    <SliderTrack><SliderFilledTrack /></SliderTrack>
                    <SliderThumb />
                  </Slider>
                </FormControl>
                <FormControl flex={1}>
                  <FormLabel>Y-as: {params.cropY}</FormLabel>
                  <Slider
                    value={params.cropY}
                    onChange={(val) => setParams({...params, cropY: val})}
                    min={0}
                    max={imageDimensions.height - params.cropHeight}
                  >
                    <SliderTrack><SliderFilledTrack /></SliderTrack>
                    <SliderThumb />
                  </Slider>
                </FormControl>
                <FormControl flex={1}>
                  <FormLabel>Breedte: {params.cropWidth}</FormLabel>
                  <Slider
                    value={params.cropWidth}
                    onChange={(val) => setParams({...params, cropWidth: val})}
                    min={50}
                    max={imageDimensions.width - params.cropX}
                  >
                    <SliderTrack><SliderFilledTrack /></SliderTrack>
                    <SliderThumb />
                  </Slider>
                </FormControl>
                <FormControl flex={1}>
                  <FormLabel>Hoogte: {params.cropHeight}</FormLabel>
                  <Slider
                    value={params.cropHeight}
                    onChange={(val) => setParams({...params, cropHeight: val})}
                    min={50}
                    max={imageDimensions.height - params.cropY}
                  >
                    <SliderTrack><SliderFilledTrack /></SliderTrack>
                    <SliderThumb />
                  </Slider>
                </FormControl>
              </HStack>
            )}
          </Box>

          {/* Transparency */}
          <Box p={4} border="1px solid gray" borderRadius="md">
            <Checkbox
              isChecked={params.enableTransparency}
              onChange={(e) => setParams({...params, enableTransparency: e.target.checked})}
              mb={3}
            >
              <Text fontWeight="bold">Transparantie</Text>
            </Checkbox>
            {params.enableTransparency && (
              <VStack spacing={3}>
                <HStack>
                  <FormControl>
                    <FormLabel>Kleur</FormLabel>
                    <Input
                      type="color"
                      value={params.transparencyColor}
                      onChange={(e) => setParams({...params, transparencyColor: e.target.value})}
                    />
                  </FormControl>
                  <FormControl>
                    <FormLabel>Tolerantie: {params.tolerance}</FormLabel>
                    <Slider
                      value={params.tolerance}
                      onChange={(val) => setParams({...params, tolerance: val})}
                      min={0}
                      max={50}
                    >
                      <SliderTrack>
                        <SliderFilledTrack />
                      </SliderTrack>
                      <SliderThumb />
                    </Slider>
                  </FormControl>
                </HStack>
                <Checkbox
                  isChecked={params.removeBackground}
                  onChange={(e) => setParams({...params, removeBackground: e.target.checked})}
                >
                  Achtergrond verwijderen
                </Checkbox>
              </VStack>
            )}
          </Box>

          {/* Rotation */}
          <Box p={4} border="1px solid gray" borderRadius="md">
            <Checkbox
              isChecked={params.enableRotation}
              onChange={(e) => setParams({...params, enableRotation: e.target.checked})}
              mb={3}
            >
              <Text fontWeight="bold">Rotatie</Text>
            </Checkbox>
            {params.enableRotation && (
              <VStack spacing={3}>
                <FormControl>
                  <FormLabel>Rotatie: {params.rotation}°</FormLabel>
                  <HStack>
                    <Slider
                      value={params.rotation}
                      onChange={(val) => setParams({...params, rotation: val})}
                      min={-180}
                      max={180}
                      step={1}
                      flex={1}
                    >
                      <SliderTrack>
                        <SliderFilledTrack />
                      </SliderTrack>
                      <SliderThumb />
                    </Slider>
                    <Input
                      type="number"
                      value={params.rotation}
                      onChange={(e) => setParams({...params, rotation: parseInt(e.target.value) || 0})}
                      width="80px"
                      min={-180}
                      max={180}
                    />
                  </HStack>
                </FormControl>
                <Button
                  size="sm"
                  onClick={() => setParams({...params, rotation: 0})}
                >
                  Reset
                </Button>
              </VStack>
            )}
          </Box>

          {/* Color Adjustment */}
          <Box p={4} border="1px solid gray" borderRadius="md">
            <Checkbox
              isChecked={params.enableColorAdjust}
              onChange={(e) => setParams({...params, enableColorAdjust: e.target.checked})}
              mb={3}
            >
              <Text fontWeight="bold">Kleurcorrectie</Text>
            </Checkbox>
            {params.enableColorAdjust && (
              <VStack spacing={3}>
                <FormControl>
                  <FormLabel>Helderheid: {params.brightness.toFixed(1)}</FormLabel>
                  <Slider
                    value={params.brightness}
                    onChange={(val) => setParams({...params, brightness: val})}
                    min={0.1}
                    max={3}
                    step={0.1}
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                </FormControl>
                <FormControl>
                  <FormLabel>Verzadiging: {params.saturation.toFixed(1)}</FormLabel>
                  <Slider
                    value={params.saturation}
                    onChange={(val) => setParams({...params, saturation: val})}
                    min={0}
                    max={3}
                    step={0.1}
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                </FormControl>
                <FormControl>
                  <FormLabel>Contrast: {params.contrast.toFixed(1)}</FormLabel>
                  <Slider
                    value={params.contrast}
                    onChange={(val) => setParams({...params, contrast: val})}
                    min={0.1}
                    max={3}
                    step={0.1}
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                </FormControl>
              </VStack>
            )}
          </Box>
        </VStack>

        {/* Download Options */}
        {processedUrl && (
          <Box p={4} border="1px solid gray" borderRadius="md">
            <Text fontWeight="bold" mb={3}>Download Opties</Text>
            <VStack spacing={3}>
              <HStack width="100%">
                <FormControl>
                  <FormLabel>Bestandsnaam</FormLabel>
                  <Input
                    value={downloadFilename}
                    onChange={(e) => setDownloadFilename(e.target.value)}
                    placeholder="processed-image"
                  />
                </FormControl>
                <FormControl width="120px">
                  <FormLabel>Formaat</FormLabel>
                  <Select
                    value={downloadFormat}
                    onChange={(e) => setDownloadFormat(e.target.value)}
                  >
                    <option value="jpg">JPG</option>
                    <option value="png">PNG</option>
                  </Select>
                </FormControl>
              </HStack>
            </VStack>
          </Box>
        )}

        {/* Action Buttons */}
        <HStack spacing={4}>
          <Button
            colorScheme="blue"
            onClick={processImage}
            isLoading={processing}
            loadingText="Bewerken..."
            isDisabled={!selectedFile}
          >
            Bewerk Afbeelding
          </Button>
          <Button
            colorScheme="green"
            onClick={downloadImage}
            isDisabled={!processedUrl}
          >
            Opslaan
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}