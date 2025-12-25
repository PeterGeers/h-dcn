import React from 'react';
import { Box, VStack, Text, Button } from '@chakra-ui/react';

interface App {
  id?: string;
  icon: string;
  title: string;
  description: string;
  path?: string;
}

interface AppCardProps {
  app: App;
  onClick?: () => void;
}

function AppCard({ app, onClick }: AppCardProps) {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  return (
    <Box
      bg="white"
      p={{ base: 4, md: 6 }}
      borderRadius="lg"
      shadow="md"
      cursor="pointer"
      onClick={handleClick}
      _hover={{ transform: 'translateY(-2px)', shadow: 'lg' }}
      transition="all 0.2s"
      minH={{ base: '200px', md: 'auto' }}
    >
      <VStack spacing={{ base: 3, md: 4 }} h="full" justify="space-between">
        <Text fontSize={{ base: '3xl', md: '4xl' }}>{app.icon}</Text>
        <Text 
          fontSize={{ base: 'lg', md: 'xl' }} 
          fontWeight="bold" 
          color="orange.500"
          textAlign="center"
          lineHeight="shorter"
        >
          {app.title}
        </Text>
        <Text 
          color="gray.600" 
          textAlign="center"
          fontSize={{ base: 'sm', md: 'md' }}
          flex="1"
          display="flex"
          alignItems="center"
        >
          {app.description}
        </Text>
        <Button 
          colorScheme="orange" 
          size={{ base: 'sm', md: 'md' }}
          w={{ base: 'full', md: 'auto' }}
          onClick={(e) => {
            e.stopPropagation();
            handleClick();
          }}
        >
          Openen
        </Button>
      </VStack>
    </Box>
  );
}

export default AppCard;