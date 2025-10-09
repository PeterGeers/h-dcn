import React, { useState, useRef, useEffect, useCallback } from 'react';
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
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  PopoverCloseButton,
  FormControl,
  FormLabel,
  Image,
  useToast
} from '@chakra-ui/react';
import { ImageProcessor } from '../services/imageProcessor';

export default function AdvancedImageEditor({ isOpen, onClose, imageUrl, onSave }) {
  const [processing, setProcessing] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [currentImageUrl, setCurrentImageUrl] = useState(null);
  const [processedBlob, setProcessedBlob] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const [cropArea, setCropArea] = useState({ x: 0, y: 0, width: 200, height: 200 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragHandle, setDragHandle] = useState(null);
  const [cursorStyle, setCursorStyle] = useState('default');
  const toast = useToast();

  // Processing parameters
  const [params, setParams] = useState({
    resizePercentage: 100,
    brightness: 1,
    saturation: 1,
    contrast: 1,
    tolerance: 10,
    removeBackground: false
  });

  const drawCropOverlay = useCallback((ctx, canvasWidth, canvasHeight, currentCrop = cropArea) => {
    const scaleX = canvasWidth / imageDimensions.width;
    const scaleY = canvasHeight / imageDimensions.height;
    
    const scaledCrop = {
      x: currentCrop.x * scaleX,
      y: currentCrop.y * scaleY,
      width: currentCrop.width * scaleX,
      height: currentCrop.height * scaleY
    };

    // Clear and redraw image
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    if (imageRef.current) {
      ctx.drawImage(imageRef.current, 0, 0, canvasWidth, canvasHeight);
    }

    // Draw overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    
    // Clear crop area
    ctx.clearRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);
    ctx.drawImage(imageRef.current, 
      currentCrop.x, currentCrop.y, currentCrop.width, currentCrop.height,
      scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height
    );

    // Draw crop border
    ctx.strokeStyle = '#ff6b35';
    ctx.lineWidth = 2;
    ctx.strokeRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);

    // Draw corner handles
    const handleSize = 12;
    ctx.fillStyle = '#ff6b35';
    const corners = [
      { x: scaledCrop.x - handleSize/2, y: scaledCrop.y - handleSize/2 },
      { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y - handleSize/2 },
      { x: scaledCrop.x - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2 },
      { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2 }
    ];
    
    corners.forEach(corner => {
      ctx.fillRect(corner.x, corner.y, handleSize, handleSize);
    });
  }, [imageDimensions, cropArea]);

  // Load image and setup canvas
  useEffect(() => {
    if (isOpen && imageUrl) {
      setCurrentImageUrl(imageUrl);
      const img = new window.Image();
      img.onload = () => {
        setImageDimensions({ width: img.width, height: img.height });
        const initialCrop = { 
          x: 0, 
          y: 0, 
          width: Math.min(200, img.width), 
          height: Math.min(200, img.height) 
        };
        setCropArea(initialCrop);
        
        // Draw image on canvas
        const canvas = canvasRef.current;
        if (canvas) {
          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          const scale = Math.min(400 / img.width, 400 / img.height, 1);
          canvas.width = img.width * scale;
          canvas.height = img.height * scale;
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          
          // Draw initial crop overlay inline
          const scaleX = canvas.width / img.width;
          const scaleY = canvas.height / img.height;
          
          const scaledCrop = {
            x: initialCrop.x * scaleX,
            y: initialCrop.y * scaleY,
            width: initialCrop.width * scaleX,
            height: initialCrop.height * scaleY
          };

          // Draw overlay
          ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          
          // Clear crop area
          ctx.clearRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);
          ctx.drawImage(img, 
            initialCrop.x, initialCrop.y, initialCrop.width, initialCrop.height,
            scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height
          );

          // Draw crop border
          ctx.strokeStyle = '#ff6b35';
          ctx.lineWidth = 2;
          ctx.strokeRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);

          // Draw corner handles
          const handleSize = 12;
          ctx.fillStyle = '#ff6b35';
          const corners = [
            { x: scaledCrop.x - handleSize/2, y: scaledCrop.y - handleSize/2 },
            { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y - handleSize/2 },
            { x: scaledCrop.x - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2 },
            { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2 }
          ];
          
          corners.forEach(corner => {
            ctx.fillRect(corner.x, corner.y, handleSize, handleSize);
          });
        }
      };
      img.crossOrigin = 'anonymous';
      img.src = currentImageUrl || imageUrl;
      imageRef.current = img;
    }
  }, [isOpen, imageUrl, currentImageUrl]);

  const handleCanvasMouseDown = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const scaleX = canvas.width / imageDimensions.width;
    const scaleY = canvas.height / imageDimensions.height;
    const scaledCrop = {
      x: cropArea.x * scaleX,
      y: cropArea.y * scaleY,
      width: cropArea.width * scaleX,
      height: cropArea.height * scaleY
    };

    // Check if clicking on corner handles
    const handleSize = 12;
    const corners = [
      { x: scaledCrop.x - handleSize/2, y: scaledCrop.y - handleSize/2, handle: 'tl' },
      { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y - handleSize/2, handle: 'tr' },
      { x: scaledCrop.x - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2, handle: 'bl' },
      { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2, handle: 'br' }
    ];

    for (let corner of corners) {
      if (x >= corner.x && x <= corner.x + handleSize && y >= corner.y && y <= corner.y + handleSize) {
        e.preventDefault();
        setIsDragging(true);
        setDragHandle(corner.handle);
        setCursorStyle('nw-resize');
        return;
      }
    }

    // Check if clicking inside crop area for moving
    if (x >= scaledCrop.x && x <= scaledCrop.x + scaledCrop.width &&
        y >= scaledCrop.y && y <= scaledCrop.y + scaledCrop.height) {
      e.preventDefault();
      setIsDragging(true);
      setDragHandle('move');
      setCursorStyle('move');
    }
  };

  const handleCanvasMouseMove = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    if (!isDragging) {
      // Update cursor based on hover position
      const scaleX = canvas.width / imageDimensions.width;
      const scaleY = canvas.height / imageDimensions.height;
      const scaledCrop = {
        x: cropArea.x * scaleX,
        y: cropArea.y * scaleY,
        width: cropArea.width * scaleX,
        height: cropArea.height * scaleY
      };
      
      const handleSize = 12;
      const corners = [
        { x: scaledCrop.x - handleSize/2, y: scaledCrop.y - handleSize/2 },
        { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y - handleSize/2 },
        { x: scaledCrop.x - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2 },
        { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2 }
      ];
      
      let newCursor = 'default';
      for (let corner of corners) {
        if (x >= corner.x && x <= corner.x + handleSize && y >= corner.y && y <= corner.y + handleSize) {
          newCursor = 'nw-resize';
          break;
        }
      }
      
      if (newCursor === 'default' && x >= scaledCrop.x && x <= scaledCrop.x + scaledCrop.width &&
          y >= scaledCrop.y && y <= scaledCrop.y + scaledCrop.height) {
        newCursor = 'move';
      }
      
      setCursorStyle(newCursor);
      return;
    }

    const scaleX = imageDimensions.width / canvas.width;
    const scaleY = imageDimensions.height / canvas.height;

    const newCrop = { ...cropArea };

    if (dragHandle === 'move') {
      // Move entire crop area
      newCrop.x = Math.max(0, Math.min(x * scaleX - cropArea.width/2, imageDimensions.width - cropArea.width));
      newCrop.y = Math.max(0, Math.min(y * scaleY - cropArea.height/2, imageDimensions.height - cropArea.height));
    } else {
      // Resize crop area
      const realX = x * scaleX;
      const realY = y * scaleY;

      switch (dragHandle) {
        case 'tl':
          newCrop.width = cropArea.x + cropArea.width - realX;
          newCrop.height = cropArea.y + cropArea.height - realY;
          newCrop.x = realX;
          newCrop.y = realY;
          break;
        case 'tr':
          newCrop.width = realX - cropArea.x;
          newCrop.height = cropArea.y + cropArea.height - realY;
          newCrop.y = realY;
          break;
        case 'bl':
          newCrop.width = cropArea.x + cropArea.width - realX;
          newCrop.height = realY - cropArea.y;
          newCrop.x = realX;
          break;
        case 'br':
          newCrop.width = realX - cropArea.x;
          newCrop.height = realY - cropArea.y;
          break;
        default:
          break;
      }

      // Ensure minimum size and bounds
      newCrop.width = Math.max(50, Math.min(newCrop.width, imageDimensions.width - newCrop.x));
      newCrop.height = Math.max(50, Math.min(newCrop.height, imageDimensions.height - newCrop.y));
    }

    setCropArea(newCrop);
    
    // Immediate redraw with new crop area
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    drawCropOverlay(ctx, canvas.width, canvas.height, newCrop);
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
    setDragHandle(null);
    setCursorStyle('default');
  };

  const applyEffect = async (effectType) => {
    if (!currentImageUrl) return;

    setProcessing(true);
    try {
      const processor = new ImageProcessor();
      let options = {};

      switch (effectType) {
        case 'resize':
          options.resize = {
            width: Math.round(imageDimensions.width * params.resizePercentage / 100),
            height: Math.round(imageDimensions.height * params.resizePercentage / 100)
          };
          break;
        case 'crop':
          options.crop = cropArea;
          break;
        case 'color':
          options.colorAdjust = {
            brightness: params.brightness,
            saturation: params.saturation,
            contrast: params.contrast
          };
          break;
        case 'transparency':
          options.transparency = {
            tolerance: params.tolerance,
            removeBackground: params.removeBackground
          };
          break;
        default:
          break;
      }

      let file;
      if (processedBlob) {
        // Use the current processed blob for cumulative effects
        file = new File([processedBlob], 'image.jpg', { type: processedBlob.type });
      } else {
        // First time processing, use original image
        const response = await fetch(currentImageUrl);
        const blob = await response.blob();
        file = new File([blob], 'image.jpg', { type: blob.type });
      }
      
      const newProcessedBlob = await processor.processImage(file, options);
      const newUrl = URL.createObjectURL(newProcessedBlob);
      
      // Update current image to the processed version
      setCurrentImageUrl(newUrl);
      setProcessedBlob(newProcessedBlob);
      setHasChanges(true);
      
      // Update canvas with new image
      const img = new window.Image();
      img.onload = () => {
        setImageDimensions({ width: img.width, height: img.height });
        const canvas = canvasRef.current;
        if (canvas) {
          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          
          // For crop effect, show actual crop result
          if (effectType === 'crop') {
            // Show the cropped image at actual size (up to max)
            const maxSize = 400;
            const scale = Math.min(maxSize / img.width, maxSize / img.height, 1);
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            canvas.style.width = canvas.width + 'px';
            canvas.style.height = canvas.height + 'px';
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          } else {
            // For other effects, show with proportional scaling
            const maxSize = 400;
            const scale = Math.min(maxSize / img.width, maxSize / img.height, 1);
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            canvas.style.width = canvas.width + 'px';
            canvas.style.height = canvas.height + 'px';
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          }
          
          // Update crop area based on effect type
          let newCropArea;
          if (effectType === 'crop') {
            // After crop: reset to cover entire new image
            newCropArea = { 
              x: 0, 
              y: 0, 
              width: img.width, 
              height: img.height 
            };
            setCropArea(newCropArea);
          } else if (effectType === 'resize') {
            // After resize: scale crop area proportionally
            const scaleX = img.width / imageDimensions.width;
            const scaleY = img.height / imageDimensions.height;
            newCropArea = {
              x: Math.round(cropArea.x * scaleX),
              y: Math.round(cropArea.y * scaleY),
              width: Math.round(cropArea.width * scaleX),
              height: Math.round(cropArea.height * scaleY)
            };
            setCropArea(newCropArea);
          } else {
            // For color/transparency: keep current crop area
            newCropArea = cropArea;
          }
          
          // Draw crop overlay with updated crop area
          drawCropOverlay(ctx, canvas.width, canvas.height, newCropArea);
        }
      };
      img.src = newUrl;
      imageRef.current = img;

      toast({
        title: 'Effect toegepast!',
        status: 'success',
        duration: 2000,
      });
    } catch (error) {
      console.error('Processing error:', error);
      toast({
        title: 'Fout bij toepassen effect',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl">
      <ModalOverlay bg="blackAlpha.800" />
      <ModalContent maxHeight="95vh" overflowY="auto" bg="gray.800" color="white" width="800px">
        <ModalHeader bg="gray.700" py={3}>
          <HStack>
            <Image 
              src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" 
              alt="H-DCN Logo" 
              boxSize="24px" 
            />
            <Text color="white" fontSize="lg">Image Editor</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton color="white" />
        <ModalBody pb={4} bg="gray.800">
          <VStack spacing={4} align="stretch">
            {/* Tool Buttons */}
            <HStack spacing={2} justify="center">
              {/* Resize Tool */}
              <Popover placement="bottom-start" closeOnBlur={false}>
                <PopoverTrigger>
                  <Button colorScheme="orange" size="sm">
                    Verkleinen
                  </Button>
                </PopoverTrigger>
                <PopoverContent bg="gray.700" borderColor="gray.600" width="250px">
                  <PopoverCloseButton color="white" size="sm" />
                  <PopoverBody pt={6}>
                    <FormControl>
                      <FormLabel color="white" fontSize="sm">Schaal: {params.resizePercentage}%</FormLabel>
                      <Slider
                        value={params.resizePercentage}
                        onChange={(val) => setParams({...params, resizePercentage: val})}
                        min={10}
                        max={200}
                        step={5}
                        colorScheme="orange"
                        size="sm"
                      >
                        <SliderTrack bg="gray.600">
                          <SliderFilledTrack bg="orange.400" />
                        </SliderTrack>
                        <SliderThumb bg="orange.500" />
                      </Slider>
                      <Button 
                        mt={2} 
                        colorScheme="orange" 
                        size="xs" 
                        onClick={() => applyEffect('resize')}
                        isLoading={processing}
                      >
                        Toepassen
                      </Button>
                    </FormControl>
                  </PopoverBody>
                </PopoverContent>
              </Popover>

              {/* Crop Tool */}
              <Popover placement="right-start" closeOnBlur={false}>
                <PopoverTrigger>
                  <Button colorScheme="orange" size="sm">
                    Bijsnijden
                  </Button>
                </PopoverTrigger>
                <PopoverContent bg="gray.700" borderColor="gray.600" width="180px">
                  <PopoverCloseButton color="white" size="sm" />
                  <PopoverBody pt={6}>
                    <Text color="white" fontSize="xs" mb={2}>
                      Sleep de hoekpunten
                    </Text>
                    <Button 
                      colorScheme="orange" 
                      size="xs" 
                      onClick={() => applyEffect('crop')}
                      isLoading={processing}
                    >
                      Bijsnijden
                    </Button>
                  </PopoverBody>
                </PopoverContent>
              </Popover>

              {/* Color Tool */}
              <Popover placement="bottom" closeOnBlur={false}>
                <PopoverTrigger>
                  <Button colorScheme="orange" size="sm">
                    Kleuren
                  </Button>
                </PopoverTrigger>
                <PopoverContent bg="gray.700" borderColor="gray.600" width="250px">
                  <PopoverCloseButton color="white" size="sm" />
                  <PopoverBody pt={6}>
                    <VStack spacing={2}>
                      <FormControl>
                        <FormLabel color="white" fontSize="xs">Helderheid: {params.brightness.toFixed(1)}</FormLabel>
                        <Slider
                          value={params.brightness}
                          onChange={(val) => setParams({...params, brightness: val})}
                          min={0.1}
                          max={3}
                          step={0.1}
                          colorScheme="orange"
                          size="sm"
                        >
                          <SliderTrack bg="gray.600">
                            <SliderFilledTrack bg="orange.400" />
                          </SliderTrack>
                          <SliderThumb bg="orange.500" />
                        </Slider>
                      </FormControl>
                      <FormControl>
                        <FormLabel color="white" fontSize="xs">Verzadiging: {params.saturation.toFixed(1)}</FormLabel>
                        <Slider
                          value={params.saturation}
                          onChange={(val) => setParams({...params, saturation: val})}
                          min={0}
                          max={3}
                          step={0.1}
                          colorScheme="orange"
                          size="sm"
                        >
                          <SliderTrack bg="gray.600">
                            <SliderFilledTrack bg="orange.400" />
                          </SliderTrack>
                          <SliderThumb bg="orange.500" />
                        </Slider>
                      </FormControl>
                      <Button 
                        colorScheme="orange" 
                        size="xs" 
                        onClick={() => applyEffect('color')}
                        isLoading={processing}
                      >
                        Toepassen
                      </Button>
                    </VStack>
                  </PopoverBody>
                </PopoverContent>
              </Popover>

              {/* Transparency Tool */}
              <Popover placement="bottom-end" closeOnBlur={false}>
                <PopoverTrigger>
                  <Button colorScheme="orange" size="sm">
                    Transparantie
                  </Button>
                </PopoverTrigger>
                <PopoverContent bg="gray.700" borderColor="gray.600" width="220px">
                  <PopoverCloseButton color="white" size="sm" />
                  <PopoverBody pt={6}>
                    <FormControl>
                      <FormLabel color="white" fontSize="xs">Tolerantie: {params.tolerance}</FormLabel>
                      <Slider
                        value={params.tolerance}
                        onChange={(val) => setParams({...params, tolerance: val})}
                        min={0}
                        max={50}
                        colorScheme="orange"
                        size="sm"
                      >
                        <SliderTrack bg="gray.600">
                          <SliderFilledTrack bg="orange.400" />
                        </SliderTrack>
                        <SliderThumb bg="orange.500" />
                      </Slider>
                      <Button 
                        mt={2}
                        colorScheme="orange" 
                        size="xs" 
                        onClick={() => applyEffect('transparency')}
                        isLoading={processing}
                      >
                        Toepassen
                      </Button>
                    </FormControl>
                  </PopoverBody>
                </PopoverContent>
              </Popover>
            </HStack>

            {/* Image Preview */}
            <Box align="center" minHeight="450px" display="flex" alignItems="center" justifyContent="center">
              <canvas
                ref={canvasRef}
                style={{ 
                  border: '2px solid #ff6b35', 
                  cursor: cursorStyle,
                  maxWidth: '600px',
                  maxHeight: '450px',
                  borderRadius: '8px'
                }}
                onMouseDown={handleCanvasMouseDown}
                onMouseMove={handleCanvasMouseMove}
                onMouseUp={handleCanvasMouseUp}
                onMouseLeave={handleCanvasMouseUp}
              />
            </Box>

            {/* Action Buttons */}
            <HStack spacing={3} justify="center">

              <Button
                colorScheme="green"
                onClick={() => {
                  if (processedBlob) {
                    // Use the processed blob instead of URL
                    const processedUrl = URL.createObjectURL(processedBlob);
                    onSave(processedUrl);
                  } else {
                    onSave(currentImageUrl || imageUrl);
                  }
                }}
                isDisabled={!hasChanges}
                size="md"
              >
                Opslaan
              </Button>
              <Button onClick={onClose} size="lg">
                Annuleren
              </Button>
            </HStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}