import React, { useState } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Image
} from '@chakra-ui/react';
import CropTool from './CropTool';
import BackgroundRemovalTool from './BackgroundRemovalTool';
import ColorEnhanceTool from './ColorEnhanceTool';
import ResizeTool from './ResizeTool';

export default function ImageTools() {
  const [activeTool, setActiveTool] = useState(null);

  const tools = [
    {
      id: 'crop',
      name: 'Bijsnijden',
      description: 'Snijd afbeeldingen bij naar gewenste grootte',
      icon: '✂️',
      color: 'green'
    },
    {
      id: 'background',
      name: 'Achtergrond Verwijderen',
      description: 'Verwijder achtergrond en sla op als PNG',
      icon: '🎭',
      color: 'purple'
    },
    {
      id: 'color',
      name: 'Kleur Verbeteren',
      description: 'Pas helderheid, contrast en verzadiging aan',
      icon: '🎨',
      color: 'orange'
    },
    {
      id: 'resize',
      name: 'Verkleinen',
      description: 'Verklein of vergroot afbeeldingen',
      icon: '📏',
      color: 'blue'
    }
  ];

  const renderTool = () => {
    switch (activeTool) {
      case 'crop':
        return <CropTool onClose={() => setActiveTool(null)} />;
      case 'background':
        return <BackgroundRemovalTool onClose={() => setActiveTool(null)} />;
      case 'color':
        return <ColorEnhanceTool onClose={() => setActiveTool(null)} />;
      case 'resize':
        return <ResizeTool onClose={() => setActiveTool(null)} />;
      default:
        return null;
    }
  };

  if (activeTool) {
    return renderTool();
  }

  return (
    <Box p={8} bg="black" minHeight="100vh">
      <VStack spacing={8} align="center">
        <Box textAlign="center">
          <HStack justify="center" mb={4}>
            <Image 
              src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" 
              alt="H-DCN Logo" 
              boxSize="40px" 
            />
            <Text fontSize="3xl" fontWeight="bold" color="orange.400">
              Image Tools
            </Text>
          </HStack>
          <Text fontSize="lg" color="orange.200">
            Kies een tool om afbeeldingen te bewerken
          </Text>
        </Box>

        {/* Image Preview Area */}
        <Box
          width="600px"
          height="400px"
          bg="gray.900"
          borderRadius="lg"
          boxShadow="xl"
          border="3px dashed"
          borderColor="orange.400"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <VStack spacing={4}>
            <Text fontSize="6xl" color="orange.300">🖼️</Text>
            <Text fontSize="lg" color="orange.200" textAlign="center">
              Afbeelding preview verschijnt hier
            </Text>
            <Text fontSize="sm" color="orange.300">
              Selecteer een tool om te beginnen
            </Text>
          </VStack>
        </Box>

        {/* Tool Buttons */}
        <HStack spacing={6} wrap="wrap" justify="center">
          {tools.map((tool) => (
            <Button
              key={tool.id}
              onClick={() => setActiveTool(tool.id)}
              colorScheme={tool.color}
              size="lg"
              height="80px"
              width="180px"
              flexDirection="column"
              gap={2}
            >
              <Text fontSize="2xl">{tool.icon}</Text>
              <Text fontSize="md" fontWeight="bold">
                {tool.name}
              </Text>
            </Button>
          ))}
        </HStack>

        <Text fontSize="sm" color="orange.300" textAlign="center" maxWidth="600px">
          Elke tool kan afbeeldingen openen van je computer, bewerken en opslaan met een naam naar keuze.
          De laatste gebruikte map wordt onthouden voor gemakkelijk gebruik.
        </Text>
      </VStack>
    </Box>
  );
}