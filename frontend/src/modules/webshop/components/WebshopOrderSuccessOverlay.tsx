import React from 'react';
import { Box } from '@chakra-ui/react';
import OrderSuccess from './OrderSuccess';

interface WebshopOrderSuccessOverlayProps {
  onClose: () => void;
}

function WebshopOrderSuccessOverlay({ onClose }: WebshopOrderSuccessOverlayProps) {
  return (
    <Box
      position="fixed"
      top={0}
      left={0}
      right={0}
      bottom={0}
      bg="blackAlpha.600"
      display="flex"
      alignItems="center"
      justifyContent="center"
      zIndex={1000}
    >
      <Box
        bg="white"
        borderRadius="md"
        maxW="800px"
        maxH="90vh"
        overflow="auto"
        boxShadow="xl"
      >
        <OrderSuccess onClose={onClose} />
      </Box>
    </Box>
  );
}

export default WebshopOrderSuccessOverlay;
