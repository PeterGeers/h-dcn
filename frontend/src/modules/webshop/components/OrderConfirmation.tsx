import React, { useState } from 'react';
import { Button, useToast } from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { downloadOrderPdf } from '../services/pdfDownloadService';
import { formatPrice, toPrice } from '../../../utils/formatPrice';

interface OrderItem {
  name?: string;
  variant_attributes?: Record<string, string>;
  quantity: number;
  price?: number;
}

interface CustomerInfo {
  name?: string;
  voornaam?: string;
  achternaam?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
  email?: string;
  phone?: string;
}

interface ShippingAddress {
  name?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
}

interface DeliveryOption {
  label: string;
}

interface OrderData {
  orderId: string;
  timestamp: string;
  customer_info?: CustomerInfo;
  shipping_address?: ShippingAddress;
  delivery_option?: DeliveryOption;
  delivery_cost?: string;
  items: OrderItem[];
  subtotal_amount: string;
  total_amount: string;
}

interface OrderConfirmationProps {
  orderData: OrderData | null;
}

const OrderConfirmation: React.FC<OrderConfirmationProps> = ({ orderData }) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const toast = useToast();
  const { t } = useTranslation('webshop');

  if (!orderData) return null;

  const handleDownloadPdf = async () => {
    setIsDownloading(true);
    try {
      const result = await downloadOrderPdf(orderData.orderId);
      if (!result.success && result.error) {
        toast({
          title: t('confirmation.download_failed'),
          description: result.error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    } catch {
      toast({
        title: t('confirmation.download_failed'),
        description: t('confirmation.download_error_desc'),
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const formatDate = (timestamp: string): string => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return '-';
    return date.toLocaleDateString('nl-NL', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <>
      <style>{`
        @media print {
          .no-print { display: none !important; }
        }
      `}</style>
      <div style={{
        maxWidth: '600px',
        margin: '0 auto',
        padding: '24px',
        backgroundColor: 'white',
        color: 'black',
        fontFamily: 'Arial, sans-serif'
      }}>
        <div style={{ marginBottom: '20px', textAlign: 'center', backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '4px' }}>
        <Button
          leftIcon={<DownloadIcon />}
          colorScheme="green"
          onClick={handleDownloadPdf}
          isLoading={isDownloading}
          loadingText={t('confirmation.downloading')}
          isDisabled={isDownloading}
        >
          {t('confirmation.download_pdf')}
        </Button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '24px', gap: '20px' }}>
        <img 
          src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" 
          alt="H-DCN Logo"
          style={{ width: '80px', height: '80px', objectFit: 'contain' }}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
          }}
        />
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#FF6B35', margin: '0 0 8px 0' }}>H-DCN Webshop</h1>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: '0' }}>{t('confirmation.title')}</h2>
        </div>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>{t('confirmation.order_number')}:</span>
          <span>{orderData.orderId}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>{t('confirmation.date')}:</span>
          <span>{formatDate(orderData.timestamp)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>{t('confirmation.customer')}:</span>
          <span>{orderData.customer_info?.name || t('confirmation.not_available')}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>{t('confirmation.status')}:</span>
          <span style={{ color: '#22C55E', fontWeight: 'bold' }}>{t('confirmation.status_paid')}</span>
        </div>
      </div>

      <hr style={{ margin: '24px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />

      <div style={{ display: 'flex', gap: '40px', marginBottom: '24px' }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>{t('confirmation.billing_address')}</h3>
          {orderData.customer_info ? (
            <>
              <div>{orderData.customer_info.name || (orderData.customer_info.voornaam + ' ' + orderData.customer_info.achternaam) || t('confirmation.name_not_available')}</div>
              <div>{orderData.customer_info.straat || t('confirmation.address_not_available')}</div>
              <div>{(orderData.customer_info.postcode || '') + ' ' + (orderData.customer_info.woonplaats || '') || t('confirmation.postal_not_available')}</div>
              {orderData.customer_info.email && <div>{orderData.customer_info.email}</div>}
              {orderData.customer_info.phone && <div>{orderData.customer_info.phone}</div>}
            </>
          ) : (
            <div>{t('confirmation.no_address')}</div>
          )}
        </div>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>{t('confirmation.shipping_address')}</h3>
          {orderData.shipping_address || orderData.customer_info ? (
            <>
              <div>{orderData.shipping_address?.name || orderData.customer_info?.name || (orderData.customer_info?.voornaam + ' ' + orderData.customer_info?.achternaam) || t('confirmation.name_not_available')}</div>
              <div>{orderData.shipping_address?.straat || orderData.customer_info?.straat || t('confirmation.address_not_available')}</div>
              <div>{(orderData.shipping_address?.postcode || orderData.customer_info?.postcode || '') + ' ' + (orderData.shipping_address?.woonplaats || orderData.customer_info?.woonplaats || '') || t('confirmation.postal_not_available')}</div>
            </>
          ) : (
            <div>{t('confirmation.no_address')}</div>
          )}
        </div>
      </div>
      <hr style={{ margin: '24px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />

      {orderData.delivery_option && (
        <>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>{t('confirmation.delivery')}</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
            <span>{orderData.delivery_option.label}</span>
            <span>€{orderData.delivery_cost}</span>
          </div>
          <hr style={{ margin: '24px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />
        </>
      )}

      <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>{t('confirmation.ordered_products')}</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '24px' }}>
        <thead>
          <tr style={{ backgroundColor: '#F9FAFB' }}>
            <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>{t('confirmation.col_product')}</th>
            <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>{t('confirmation.col_option')}</th>
            <th style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>{t('confirmation.col_quantity')}</th>
            <th style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>{t('confirmation.col_price')}</th>
            <th style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>{t('confirmation.col_total')}</th>
          </tr>
        </thead>
        <tbody>
          {orderData.items.map((item, index) => (
            <tr key={index}>
              <td style={{ padding: '8px', borderBottom: '1px solid #E5E7EB' }}>{item.name}</td>
              <td style={{ padding: '8px', borderBottom: '1px solid #E5E7EB' }}>
                {item.variant_attributes
                  ? Object.entries(item.variant_attributes).map(([k, v]) => `${k}: ${v}`).join(', ')
                  : '-'}
              </td>
              <td style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB' }}>{item.quantity}</td>
              <td style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB' }}>{formatPrice(item.price)}</td>
              <td style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB' }}>{formatPrice(item.quantity * toPrice(item.price))}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span>{t('confirmation.subtotal')}:</span>
          <span>€{orderData.subtotal_amount}</span>
        </div>
        {orderData.delivery_cost && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span>{t('confirmation.shipping_costs')}:</span>
            <span>€{orderData.delivery_cost}</span>
          </div>
        )}
        <hr style={{ margin: '8px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '18px', fontWeight: 'bold' }}>
          <span>{t('confirmation.total_paid')}:</span>
          <span>€{orderData.total_amount}</span>
        </div>
      </div>
    </div>
    </>
  );
};

export default OrderConfirmation;