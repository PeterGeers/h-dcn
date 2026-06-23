import React, { useState, useCallback } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Text,
  Heading,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Select,
  Radio,
  RadioGroup,
  Stack,
  useToast,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Alert,
  AlertIcon,
  Spinner,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { Product } from '../types/eventBooking.types';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

interface AdminPaymentAndPdfProps {
  eventId: string;
  products: Product[];
}

/**
 * Admin panel for recording manual payments and downloading preparation PDFs.
 *
 * Requirements: 11.3, 11.4, 15.1, 15.4, 15.7, 15.8
 */
const AdminPaymentAndPdf: React.FC<AdminPaymentAndPdfProps> = ({
  eventId,
  products,
}) => {
  return (
    <VStack spacing={6} align="stretch">
      <PaymentRecorder eventId={eventId} />
      <PreparationPdfDownload eventId={eventId} products={products} />
    </VStack>
  );
};

// --- Payment Recorder ---

interface PaymentRecorderProps {
  eventId: string;
}

/**
 * Form to record a manual payment for a specific order.
 * Calls POST /admin/payments with order_id, amount, date, description.
 *
 * Requirements: 11.3, 11.4
 */
const PaymentRecorder: React.FC<PaymentRecorderProps> = ({ eventId }) => {
  const { t } = useTranslation('eventBooking');
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const [orderId, setOrderId] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const resetForm = useCallback(() => {
    setOrderId('');
    setAmount('');
    setPaymentDate('');
    setDescription('');
  }, []);

  const handleRecordPayment = async () => {
    if (!orderId || !amount || !paymentDate) {
      toast({
        title: t('admin.payment_recording.fields_required'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      toast({
        title: t('admin.payment_recording.invalid_amount'),
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setSubmitting(true);
    try {
      const authHeaders = await getAuthHeaders();
      await axios.post(
        `${BASE_URL}/admin/payments`,
        {
          order_id: orderId,
          amount: parsedAmount,
          date: paymentDate,
          description: description || undefined,
        },
        { headers: { 'Content-Type': 'application/json', ...authHeaders } }
      );

      toast({
        title: t('admin.payment_recording.success'),
        status: 'success',
        duration: 3000,
      });
      resetForm();
      onClose();
    } catch (error: any) {
      const message =
        error?.response?.data?.message ||
        error?.response?.data?.error ||
        t('admin.payment_recording.failed');
      toast({
        title: t('admin.payment_recording.failed'),
        description: message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
      <HStack justify="space-between">
        <Heading size="md">{t('admin.payment_recording.title')}</Heading>
        <Button colorScheme="purple" onClick={onOpen}>
          {t('admin.payment_recording.record_button')}
        </Button>
      </HStack>
      <Text fontSize="sm" color="gray.600" mt={2}>
        {t('admin.payment_recording.description')}
      </Text>

      <Modal isOpen={isOpen} onClose={onClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>{t('admin.payment_recording.modal_title')}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>{t('admin.payment_recording.order_id')}</FormLabel>
                <Input
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                  placeholder={t('admin.payment_recording.order_id_placeholder')}
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>{t('admin.payment_recording.amount')}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>{t('admin.payment_recording.date')}</FormLabel>
                <Input
                  type="date"
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                />
              </FormControl>
              <FormControl>
                <FormLabel>{t('admin.payment_recording.description_label')}</FormLabel>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t('admin.payment_recording.description_placeholder')}
                  maxLength={255}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              {t('admin.payment_recording.cancel')}
            </Button>
            <Button
              colorScheme="purple"
              onClick={handleRecordPayment}
              isLoading={submitting}
              loadingText={t('admin.payment_recording.recording')}
            >
              {t('admin.payment_recording.confirm')}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

// --- Preparation PDF Download ---

interface PreparationPdfDownloadProps {
  eventId: string;
  products: Product[];
}

/**
 * UI to download preparation PDFs in by_order or by_guest mode
 * with an optional product filter.
 *
 * Requirements: 15.1, 15.4, 15.7, 15.8
 */
const PreparationPdfDownload: React.FC<PreparationPdfDownloadProps> = ({
  eventId,
  products,
}) => {
  const { t } = useTranslation('eventBooking');
  const toast = useToast();

  const [mode, setMode] = useState<'by_order' | 'by_guest'>('by_order');
  const [productFilter, setProductFilter] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [emptyMessage, setEmptyMessage] = useState<string | null>(null);

  const handleDownload = async () => {
    if (!eventId) return;

    setDownloading(true);
    setEmptyMessage(null);

    try {
      const authHeaders = await getAuthHeaders();
      const params: Record<string, string> = { mode };
      if (productFilter) {
        params.product_filter = productFilter;
      }

      const response = await axios.get(
        `${BASE_URL}/admin/events/${encodeURIComponent(eventId)}/preparation-pdf`,
        {
          params,
          headers: { ...authHeaders },
          responseType: 'arraybuffer',
        }
      );

      // Check if the response is JSON (empty-state message) or PDF binary
      const contentType = response.headers['content-type'] || '';

      if (contentType.includes('application/json')) {
        // The response is JSON with an empty-state message
        const text = new TextDecoder().decode(response.data);
        const json = JSON.parse(text);
        const body = json.body ? JSON.parse(json.body) : json;
        setEmptyMessage(body.message || t('admin.preparation_pdf.no_orders'));
        return;
      }

      // PDF binary response — trigger download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `preparation-${mode}-${eventId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast({
        title: t('admin.preparation_pdf.download_success'),
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      // Check if the error response is JSON with an empty-state message
      if (error?.response?.data) {
        try {
          const text =
            error.response.data instanceof ArrayBuffer
              ? new TextDecoder().decode(error.response.data)
              : JSON.stringify(error.response.data);
          const json = JSON.parse(text);
          const body = json.body ? JSON.parse(json.body) : json;
          if (body.message && !body.pdf) {
            setEmptyMessage(body.message);
            return;
          }
        } catch {
          // Not JSON — fall through to generic error
        }
      }

      toast({
        title: t('admin.preparation_pdf.download_failed'),
        status: 'error',
        duration: 5000,
      });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
      <Heading size="md" mb={4}>
        {t('admin.preparation_pdf.title')}
      </Heading>
      <Text fontSize="sm" color="gray.600" mb={4}>
        {t('admin.preparation_pdf.description')}
      </Text>

      <VStack spacing={4} align="stretch">
        {/* Mode selector */}
        <FormControl>
          <FormLabel>{t('admin.preparation_pdf.mode_label')}</FormLabel>
          <RadioGroup
            value={mode}
            onChange={(val) => setMode(val as 'by_order' | 'by_guest')}
          >
            <Stack direction="row" spacing={6}>
              <Radio value="by_order">
                {t('admin.preparation_pdf.mode_by_order')}
              </Radio>
              <Radio value="by_guest">
                {t('admin.preparation_pdf.mode_by_guest')}
              </Radio>
            </Stack>
          </RadioGroup>
        </FormControl>

        {/* Product filter */}
        <FormControl>
          <FormLabel>{t('admin.preparation_pdf.product_filter_label')}</FormLabel>
          <Select
            placeholder={t('admin.preparation_pdf.all_products')}
            value={productFilter}
            onChange={(e) => setProductFilter(e.target.value)}
            maxW="400px"
          >
            {products.map((product) => (
              <option key={product.product_id} value={product.product_id}>
                {product.naam}
              </option>
            ))}
          </Select>
        </FormControl>

        {/* Empty-state message */}
        {emptyMessage && (
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            <Text>{emptyMessage}</Text>
          </Alert>
        )}

        {/* Download button */}
        <HStack>
          <Button
            colorScheme="blue"
            onClick={handleDownload}
            isLoading={downloading}
            loadingText={t('admin.preparation_pdf.downloading')}
            isDisabled={!eventId}
            leftIcon={downloading ? <Spinner size="sm" /> : undefined}
          >
            {t('admin.preparation_pdf.download_button')}
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
};

export default AdminPaymentAndPdf;
