import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  Button,
  Text,
  Alert,
  AlertIcon,
  Spinner,
  Box,
  Select,
  HStack
} from '@chakra-ui/react';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { getStripe } from '../services/stripe';
import { parameterService } from '../services/api';
import { processDeliveryOptions, getDefaultDeliveryOptions } from '../utils/deliveryOptionsProcessor';

interface CartItem {
  product_id?: string;
  name?: string;
  naam?: string;
  price?: number;
  quantity: number;
  selectedOption?: string;
}

interface DeliveryOption {
  value: string;
  label: string;
  cost?: string;
}

interface ShippingAddress {
  name: string;
  straat: string;
  postcode: string;
  woonplaats: string;
}

interface PaymentData {
  paymentMethodId: string;
  amount: number;
  items: CartItem[];
  deliveryOption: DeliveryOption | null;
  shippingAddress: ShippingAddress | null;
}

interface CheckoutFormProps {
  cartItems: CartItem[];
  totalAmount: number;
  deliveryOptions: DeliveryOption[];
  selectedDelivery: string;
  onDeliveryChange: (value: string) => void;
  onSuccess: (paymentData: PaymentData) => void;
  onError: (error: string) => void;
  userEmail: string;
}

interface CheckoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  cartItems: CartItem[];
  onPaymentSuccess: (paymentData: PaymentData) => void;
  userEmail: string;
}

const CheckoutForm: React.FC<CheckoutFormProps> = ({ 
  cartItems, 
  totalAmount, 
  deliveryOptions, 
  selectedDelivery, 
  onDeliveryChange, 
  onSuccess, 
  onError, 
  userEmail 
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [sameAsUserAddress, setSameAsUserAddress] = useState<boolean>(true);
  const [shippingAddress, setShippingAddress] = useState<ShippingAddress>({
    name: '',
    straat: '',
    postcode: '',
    woonplaats: ''
  });
  
  const deliveryOption = deliveryOptions.find(opt => opt.value === selectedDelivery);
  const deliveryCost = deliveryOption ? parseFloat(deliveryOption.cost || '0') : 0;
  const finalTotal = totalAmount + deliveryCost;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!stripe || !elements) return;
    
    setIsProcessing(true);
    
    try {
      const cardElement = elements.getElement(CardElement);
      
      console.log('Creating payment method with email:', userEmail);
      
      const { error, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement!,
        billing_details: {
          email: userEmail
        }
      });
      
      console.log('Payment method created:', paymentMethod);

      if (error) {
        onError(error.message || 'Payment error');
        setIsProcessing(false);
        return;
      }

      setTimeout(() => {
        onSuccess({
          paymentMethodId: paymentMethod!.id,
          amount: finalTotal,
          items: cartItems,
          deliveryOption: deliveryOption || null,
          shippingAddress: sameAsUserAddress ? null : shippingAddress
        });
        setIsProcessing(false);
      }, 2000);

    } catch (error) {
      onError('Er is een fout opgetreden bij de betaling');
      setIsProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <VStack spacing={4}>
        <Box width="full">
          <Text mb={2} color="white" fontWeight="medium">Leveroptie:</Text>
          <Select
            value={selectedDelivery}
            onChange={(e) => onDeliveryChange(e.target.value)}
            bg="white"
            color="black"
          >
            {deliveryOptions.map((option, index) => (
              <option key={index} value={option.value}>
                {option.label} - €{parseFloat(option.cost || '0').toFixed(2)}
              </option>
            ))}
          </Select>
        </Box>
        
        <Box width="full">
          <Text mb={2} color="white" fontWeight="medium">Verzendadres:</Text>
          <VStack spacing={3} align="stretch">
            <HStack>
              <input
                type="checkbox"
                id="sameAddress"
                checked={sameAsUserAddress}
                onChange={(e) => setSameAsUserAddress(e.target.checked)}
              />
              <Text color="white" fontSize="sm">Verzendadres is gelijk aan mijn adres</Text>
            </HStack>
            
            {!sameAsUserAddress && (
              <VStack spacing={2} align="stretch">
                <input
                  type="text"
                  placeholder="Naam"
                  value={shippingAddress.name}
                  onChange={(e) => setShippingAddress({...shippingAddress, name: e.target.value})}
                  style={{
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    width: '100%',
                    color: 'black',
                    backgroundColor: 'white'
                  }}
                />
                <input
                  type="text"
                  placeholder="Straat en huisnummer"
                  value={shippingAddress.straat}
                  onChange={(e) => setShippingAddress({...shippingAddress, straat: e.target.value})}
                  style={{
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    width: '100%',
                    color: 'black',
                    backgroundColor: 'white'
                  }}
                />
                <HStack>
                  <input
                    type="text"
                    placeholder="Postcode"
                    value={shippingAddress.postcode}
                    onChange={(e) => setShippingAddress({...shippingAddress, postcode: e.target.value})}
                    style={{
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                      width: '100%',
                      color: 'black',
                      backgroundColor: 'white'
                    }}
                  />
                  <input
                    type="text"
                    placeholder="Woonplaats"
                    value={shippingAddress.woonplaats}
                    onChange={(e) => setShippingAddress({...shippingAddress, woonplaats: e.target.value})}
                    style={{
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                      width: '100%',
                      color: 'black',
                      backgroundColor: 'white'
                    }}
                  />
                </HStack>
              </VStack>
            )}
          </VStack>
        </Box>
        
        <Box
          p={4}
          borderWidth={1}
          borderColor="gray.300"
          borderRadius="md"
          width="full"
          bg="white"
        >
          <CardElement
            options={{
              style: {
                base: {
                  fontSize: '16px',
                  color: '#424770',
                  '::placeholder': {
                    color: '#aab7c4',
                  },
                },
              },
            }}
          />
        </Box>
        
        <VStack spacing={2} width="full">
          <HStack justify="space-between" width="full">
            <Text color="white">Subtotaal:</Text>
            <Text color="white">€{totalAmount.toFixed(2)}</Text>
          </HStack>
          <HStack justify="space-between" width="full">
            <Text color="white">Verzending:</Text>
            <Text color="white">€{deliveryCost.toFixed(2)}</Text>
          </HStack>
          <HStack justify="space-between" width="full">
            <Text fontSize="lg" fontWeight="bold" color="white">Totaal:</Text>
            <Text fontSize="lg" fontWeight="bold" color="white">€{finalTotal.toFixed(2)}</Text>
          </HStack>
        </VStack>
        
        <Button
          type="submit"
          bg="orange.500"
          color="white"
          _hover={{ bg: "orange.500", opacity: 0.8 }}
          width="full"
          size="lg"
          isLoading={isProcessing}
          loadingText="Verwerken..."
          disabled={!stripe || isProcessing || !selectedDelivery}
        >
          {isProcessing ? <Spinner size="sm" /> : `Betaal €${finalTotal.toFixed(2)}`}
        </Button>
        
        <Box bg="blue.900" p={3} borderRadius="md" width="full">
          <Text fontSize="sm" color="blue.200" fontWeight="bold" mb={2}>
            🧪 Testmodus - Gebruik testgegevens:
          </Text>
          <VStack align="start" spacing={1} fontSize="xs" color="blue.100">
            <Text>• Kaartnummer: 4242 4242 4242 4242</Text>
            <Text>• Vervaldatum: Elke toekomstige datum (bijv. 12/34)</Text>
            <Text>• CVC: Elke 3 cijfers (bijv. 123)</Text>
            <Text>• Naam: Elke naam (bijv. Test Gebruiker)</Text>
            <Text>• Postcode: Elk formaat (bijv. 1234AB)</Text>
          </VStack>
        </Box>
      </VStack>
    </form>
  );
};

const CheckoutModal: React.FC<CheckoutModalProps> = ({ isOpen, onClose, cartItems, onPaymentSuccess, userEmail }) => {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  const [deliveryOptions, setDeliveryOptions] = useState<DeliveryOption[]>([]);
  const [selectedDelivery, setSelectedDelivery] = useState<string>('');
  
  const totalAmount = cartItems.reduce((sum, item) => sum + (Number(item.price || 0) * item.quantity), 0);
  const stripePromise = getStripe();
  
  useEffect(() => {
    const loadDeliveryOptions = async () => {
      try {
        console.log('Loading delivery options from API...');
        const response = await parameterService.getParameter('leveropties');
        console.log('Leveropties API response:', response);
        console.log('Response data:', response.data);
        
        const optionsString = response.data.value || response.data || '[]';
        console.log('Options string:', optionsString);
        
        const processedOptions = processDeliveryOptions(optionsString);
        
        console.log('Processed options:', processedOptions);
        
        setDeliveryOptions(processedOptions);
        if (processedOptions.length > 0) {
          setSelectedDelivery(processedOptions[0].value);
        }
      } catch (error) {
        console.log('Delivery options API error:', error);
        console.log('Using default options');
        const defaultOptions = getDefaultDeliveryOptions();
        setDeliveryOptions(defaultOptions);
        setSelectedDelivery(defaultOptions[0]?.value || 'standard');
      }
    };
    
    if (isOpen) {
      loadDeliveryOptions();
    }
  }, [isOpen]);

  const handleSuccess = (paymentData: PaymentData) => {
    setSuccess(true);
    setError(null);
    setTimeout(() => {
      const sanitizedPaymentData: PaymentData = {
        paymentMethodId: String(paymentData.paymentMethodId || '').replace(/[^a-zA-Z0-9_-]/g, ''),
        amount: Number(paymentData.amount) || 0,
        items: Array.isArray(paymentData.items) ? paymentData.items.map(item => ({
          name: String(item.name || '').replace(/[<>"'&]/g, ''),
          quantity: Number(item.quantity) || 0,
          price: Number(item.price) || 0,
          selectedOption: String(item.selectedOption || '').replace(/[<>"'&]/g, '')
        })) : [],
        deliveryOption: paymentData.deliveryOption ? {
          value: String(paymentData.deliveryOption.value || '').replace(/[^a-zA-Z0-9_-]/g, ''),
          label: String(paymentData.deliveryOption.label || '').replace(/[<>"'&]/g, ''),
          cost: String(paymentData.deliveryOption.cost || '0').replace(/[^0-9.]/g, '')
        } : null,
        shippingAddress: paymentData.shippingAddress
      };
      
      onPaymentSuccess(sanitizedPaymentData);
      onClose();
      setSuccess(false);
    }, 2000);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    setSuccess(false);
  };

  const handleClose = () => {
    setError(null);
    setSuccess(false);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
      <ModalOverlay />
      <ModalContent bg="black" color="white" borderWidth="3px" borderColor="orange.500">
        <ModalHeader>Betaling</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {error && (
            <Alert status="error" mb={4} bg="red.600" color="white">
              <AlertIcon />
              {error}
            </Alert>
          )}
          
          {success && (
            <Alert status="success" mb={4} bg="green.600" color="white">
              <AlertIcon />
              Betaling succesvol! Bestelling wordt verwerkt...
            </Alert>
          )}
          
          {!success && (
            <Elements stripe={stripePromise}>
              <CheckoutForm
                cartItems={cartItems}
                totalAmount={totalAmount}
                deliveryOptions={deliveryOptions}
                selectedDelivery={selectedDelivery}
                onDeliveryChange={setSelectedDelivery}
                onSuccess={handleSuccess}
                onError={handleError}
                userEmail={userEmail}
              />
            </Elements>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default CheckoutModal;