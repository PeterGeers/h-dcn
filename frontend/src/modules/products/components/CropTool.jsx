import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Input,
  FormControl,
  FormLabel,
  useToast
} from '@chakra-ui/react';

export default function CropTool({ onClose }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [cropArea, setCropArea] = useState({ x: 50, y: 50, width: 200, height: 200 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragHandle, setDragHandle] = useState(null);
  const [fileName, setFileName] = useState('cropped-image');
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
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
        setCropArea({
          x: 0,
          y: 0,
          width: Math.min(200, img.width),
          height: Math.min(200, img.height)
        });
        drawImageWithCrop(img);
      };
      img.src = url;
      imageRef.current = img;
    }
  };

  const drawImageWithCrop = useCallback((img = imageRef.current) => {
    if (!img || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Scale image to fit canvas (max 500px)
    const maxSize = 500;
    const scale = Math.min(maxSize / img.width, maxSize / img.height, 1);
    canvas.width = img.width * scale;
    canvas.height = img.height * scale;
    
    // Draw image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    
    // Draw crop overlay
    const scaleX = canvas.width / img.width;
    const scaleY = canvas.height / img.height;
    
    const scaledCrop = {
      x: cropArea.x * scaleX,
      y: cropArea.y * scaleY,
      width: cropArea.width * scaleX,
      height: cropArea.height * scaleY
    };

    // Dark overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Clear crop area
    ctx.clearRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);
    
    // Redraw image in crop area
    ctx.drawImage(img, 
      cropArea.x, cropArea.y, cropArea.width, cropArea.height,
      scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height
    );

    // Draw crop border
    ctx.strokeStyle = '#ff6b35';
    ctx.lineWidth = 3;
    ctx.strokeRect(scaledCrop.x, scaledCrop.y, scaledCrop.width, scaledCrop.height);

    // Draw corner handles
    const handleSize = 15;
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
  }, [cropArea]);

  const handleMouseDown = (e) => {
    if (!imageRef.current) return;
    
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

    // Check corner handles
    const handleSize = 15;
    const corners = [
      { x: scaledCrop.x - handleSize/2, y: scaledCrop.y - handleSize/2, handle: 'tl' },
      { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y - handleSize/2, handle: 'tr' },
      { x: scaledCrop.x - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2, handle: 'bl' },
      { x: scaledCrop.x + scaledCrop.width - handleSize/2, y: scaledCrop.y + scaledCrop.height - handleSize/2, handle: 'br' }
    ];

    for (let corner of corners) {
      if (x >= corner.x && x <= corner.x + handleSize && y >= corner.y && y <= corner.y + handleSize) {
        setIsDragging(true);
        setDragHandle(corner.handle);
        return;
      }
    }

    // Check if clicking inside crop area for moving
    if (x >= scaledCrop.x && x <= scaledCrop.x + scaledCrop.width &&
        y >= scaledCrop.y && y <= scaledCrop.y + scaledCrop.height) {
      setIsDragging(true);
      setDragHandle('move');
    }
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !imageRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const scaleX = imageDimensions.width / canvas.width;
    const scaleY = imageDimensions.height / canvas.height;

    const newCrop = { ...cropArea };

    if (dragHandle === 'move') {
      newCrop.x = Math.max(0, Math.min(x * scaleX - cropArea.width/2, imageDimensions.width - cropArea.width));
      newCrop.y = Math.max(0, Math.min(y * scaleY - cropArea.height/2, imageDimensions.height - cropArea.height));
    } else {
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
      newCrop.x = Math.max(0, Math.min(newCrop.x, imageDimensions.width - newCrop.width));
      newCrop.y = Math.max(0, Math.min(newCrop.y, imageDimensions.height - newCrop.height));
    }

    setCropArea(newCrop);
    drawImageWithCrop();
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragHandle(null);
  };

  const applyCrop = () => {
    if (!imageRef.current || !selectedFile) return;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = cropArea.width;
    canvas.height = cropArea.height;
    
    ctx.drawImage(imageRef.current, 
      cropArea.x, cropArea.y, cropArea.width, cropArea.height,
      0, 0, cropArea.width, cropArea.height
    );

    canvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${fileName}.jpg`;
      a.click();
      URL.revokeObjectURL(url);
      
      toast({
        title: 'Bijgesneden afbeelding opgeslagen!',
        status: 'success',
        duration: 3000,
      });
    }, 'image/jpeg', 0.9);
  };

  return (
    <Box p={6} bg="black" minHeight="100vh">
      <VStack spacing={6} align="center">
        <HStack>
          <Button onClick={onClose} variant="ghost" color="orange.300">
            ← Terug
          </Button>
          <Text fontSize="2xl" fontWeight="bold" color="orange.300">
            ✂️ Bijsnijden
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
              <canvas
                ref={canvasRef}
                style={{
                  border: '3px solid #ff6b35',
                  borderRadius: '8px',
                  cursor: isDragging ? 'grabbing' : 'crosshair',
                  maxWidth: '500px',
                  maxHeight: '500px'
                }}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              />
              <Text fontSize="sm" color="orange.200" mt={2}>
                Sleep de oranje hoekpunten om het bijsnijdgebied aan te passen
              </Text>
            </Box>
          )}

          {imageUrl && (
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
                colorScheme="green"
                onClick={applyCrop}
                size="lg"
              >
                Bijsnijden & Opslaan
              </Button>
            </HStack>
          )}
        </VStack>
      </VStack>
    </Box>
  );
}