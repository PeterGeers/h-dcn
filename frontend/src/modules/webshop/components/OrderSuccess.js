import React, { useEffect, useState } from 'react';
import { Box, Button, Text, VStack } from '@chakra-ui/react';
import OrderConfirmation from './OrderConfirmation';

const OrderSuccess = ({ onClose }) => {
  const [orderData, setOrderData] = useState(null);

  useEffect(() => {
    const latestOrder = localStorage.getItem('latest_order');
    if (latestOrder) {
      const parsedOrder = JSON.parse(latestOrder);
      console.log('Order data:', parsedOrder);
      setOrderData(parsedOrder);
    }
  }, []);

  if (!orderData) {
    return (
      <Box p={6} textAlign="center">
        <Text>Geen ordergegevens gevonden.</Text>
        <Button onClick={onClose} mt={4}>Sluiten</Button>
      </Box>
    );
  }

  return (
    <VStack spacing={4} p={6}>
      <Text fontSize="xl" fontWeight="bold" color="green.500">
        Bestelling succesvol geplaatst!
      </Text>
      <Text>Ordernummer: {orderData.orderId}</Text>
      
      <Box border="1px solid #ddd" p={4}>
        <OrderConfirmation orderData={orderData} />
      </Box>
      
      <Button onClick={onClose} colorScheme="blue">
        Terug naar webshop
      </Button>
    </VStack>
  );
};

export default OrderSuccess;