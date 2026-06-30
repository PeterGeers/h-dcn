/**
 * PaymentRecordForm — Manual payment recording form with Formik + Yup.
 *
 * Fields: order_id (required), amount (0.01-999999.99), date (ISO, required),
 * description (optional, max 255 chars).
 * On failure: preserve inputs, show error toast.
 * On success: reset form, show success toast, refetch handled by parent.
 *
 * Validates: Requirements 5.2
 */

import React from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Input,
  NumberInput,
  NumberInputField,
  SimpleGrid,
  Text,
  useToast,
} from '@chakra-ui/react';
import { Formik, Form, Field, FieldProps, FormikHelpers } from 'formik';
import * as Yup from 'yup';
import { useTranslation } from 'react-i18next';
import { getValidationMessage } from '../../../utils/validationMessages';
import { RecordPaymentRequest } from '../types/admin.types';

interface PaymentRecordFormProps {
  onSubmit: (data: RecordPaymentRequest) => Promise<void>;
}

interface PaymentFormValues {
  order_id: string;
  amount: string;
  date: string;
  description: string;
}

const initialValues: PaymentFormValues = {
  order_id: '',
  amount: '',
  date: new Date().toISOString().split('T')[0],
  description: '',
};

export const PaymentRecordForm: React.FC<PaymentRecordFormProps> = ({ onSubmit }) => {
  const { t } = useTranslation('webshop');
  const toast = useToast();

  const validationSchema = Yup.object().shape({
    order_id: Yup.string().required(() => getValidationMessage(t, 'required', { field: t('payment_record.order_id_label', { defaultValue: 'Bestelling ID' }) })),
    amount: Yup.number()
      .typeError(() => getValidationMessage(t, 'invalid_number'))
      .min(0.01, () => getValidationMessage(t, 'min', { value: 0.01 }))
      .max(999999.99, () => getValidationMessage(t, 'max', { value: 999999.99 }))
      .required(() => getValidationMessage(t, 'required', { field: t('payment_record.amount_label', { defaultValue: 'Bedrag' }) })),
    date: Yup.string()
      .required(() => getValidationMessage(t, 'required', { field: t('payment_record.date_label', { defaultValue: 'Datum' }) }))
      .matches(
        /^\d{4}-\d{2}-\d{2}/,
        () => t('payment_record.date_format_error', { defaultValue: 'Gebruik ISO datumformaat (YYYY-MM-DD)' })
      ),
    description: Yup.string().max(255, () => getValidationMessage(t, 'max_length', { count: 255 })),
  });

  const handleSubmit = async (
    values: PaymentFormValues,
    { resetForm, setSubmitting }: FormikHelpers<PaymentFormValues>
  ) => {
    try {
      const payload: RecordPaymentRequest = {
        order_id: values.order_id.trim(),
        amount: parseFloat(values.amount),
        date: values.date,
        ...(values.description.trim() && { description: values.description.trim() }),
      };
      await onSubmit(payload);
      toast({
        title: t('toast.payment_recorded', { defaultValue: 'Betaling geregistreerd' }),
        description: t('toast.payment_recorded_desc', { amount: payload.amount.toFixed(2), defaultValue: `Betaling van € ${payload.amount.toFixed(2)} is succesvol verwerkt.` }),
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
      resetForm();
    } catch (err: any) {
      toast({
        title: t('toast.payment_record_error', { defaultValue: 'Fout bij registreren' }),
        description: err?.response?.data?.message || err?.message || t('errors.generic', { defaultValue: 'Er ging iets mis.' }),
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      // Do NOT reset form on failure — preserve inputs
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box bg="gray.700" p={4} borderRadius="md">
      <Text fontSize="md" fontWeight="bold" color="white" mb={3}>
        Betaling registreren
      </Text>
      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
      >
        {({ isSubmitting, errors, touched }) => (
          <Form>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3} mb={3}>
              {/* Order ID */}
              <Field name="order_id">
                {({ field, meta }: FieldProps) => (
                  <FormControl isInvalid={!!(meta.touched && meta.error)}>
                    <FormLabel color="gray.300" fontSize="sm">
                      Bestelling ID
                    </FormLabel>
                    <Input
                      {...field}
                      placeholder="order-id..."
                      bg="gray.600"
                      color="white"
                      size="sm"
                    />
                    <FormErrorMessage>{meta.error}</FormErrorMessage>
                  </FormControl>
                )}
              </Field>

              {/* Amount */}
              <Field name="amount">
                {({ field, form, meta }: FieldProps) => (
                  <FormControl isInvalid={!!(meta.touched && meta.error)}>
                    <FormLabel color="gray.300" fontSize="sm">
                      Bedrag (€)
                    </FormLabel>
                    <NumberInput
                      min={0.01}
                      max={999999.99}
                      precision={2}
                      size="sm"
                      value={field.value}
                      onChange={(val) => form.setFieldValue('amount', val)}
                    >
                      <NumberInputField
                        bg="gray.600"
                        color="white"
                        placeholder="0.00"
                      />
                    </NumberInput>
                    <FormErrorMessage>{meta.error}</FormErrorMessage>
                  </FormControl>
                )}
              </Field>

              {/* Date */}
              <Field name="date">
                {({ field, meta }: FieldProps) => (
                  <FormControl isInvalid={!!(meta.touched && meta.error)}>
                    <FormLabel color="gray.300" fontSize="sm">
                      Datum
                    </FormLabel>
                    <Input
                      {...field}
                      type="date"
                      bg="gray.600"
                      color="white"
                      size="sm"
                    />
                    <FormErrorMessage>{meta.error}</FormErrorMessage>
                  </FormControl>
                )}
              </Field>

              {/* Description */}
              <Field name="description">
                {({ field, meta }: FieldProps) => (
                  <FormControl isInvalid={!!(meta.touched && meta.error)}>
                    <FormLabel color="gray.300" fontSize="sm">
                      Omschrijving (optioneel)
                    </FormLabel>
                    <Input
                      {...field}
                      placeholder="Bijv. iDEAL betaling"
                      bg="gray.600"
                      color="white"
                      size="sm"
                      maxLength={255}
                    />
                    <FormErrorMessage>{meta.error}</FormErrorMessage>
                  </FormControl>
                )}
              </Field>
            </SimpleGrid>

            <Button
              type="submit"
              colorScheme="orange"
              size="sm"
              isLoading={isSubmitting}
              loadingText="Verwerken..."
            >
              Betaling registreren
            </Button>
          </Form>
        )}
      </Formik>
    </Box>
  );
};

export default PaymentRecordForm;
