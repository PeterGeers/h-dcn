import React from 'react';

interface OrderItem {
  name?: string;
  naam?: string;
  selectedOption?: string;
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
  if (!orderData) return null;

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

  const escapeHtml = (text: any): string => {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  const generateHTML = (): string => {
    return `<!DOCTYPE html>
<html>
<head>
    <title>Orderbevestiging ${orderData.orderId}</title>
    <style>
        @media print { .no-print { display: none; } }
        body { font-family: Arial, sans-serif; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 24px; background: white; color: black; }
        .header { display: flex; align-items: center; margin-bottom: 24px; gap: 20px; }
        .logo { width: 80px; height: 80px; background: #ddd; display: flex; align-items: center; justify-content: center; }
        .title { font-size: 24px; font-weight: bold; color: #FF6B35; margin: 0 0 8px 0; }
        .subtitle { font-size: 20px; font-weight: bold; margin: 0; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .bold { font-weight: bold; }
        .status { color: #22C55E; font-weight: bold; }
        .divider { margin: 24px 0; border: none; border-top: 1px solid #E5E7EB; }
        .address-section { display: flex; gap: 40px; margin-bottom: 24px; }
        .address { flex: 1; }
        .section-title { font-size: 18px; font-weight: bold; margin-bottom: 12px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
        th, td { padding: 8px; border-bottom: 1px solid #E5E7EB; }
        th { background-color: #F9FAFB; font-weight: bold; }
        .text-right { text-align: right; }
        .total { font-size: 18px; font-weight: bold; }
        .btn { padding: 10px 20px; margin: 20px 0; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="no-print">
        <button class="btn" onclick="window.print()">Opslaan als PDF</button>
    </div>
    
    <div class="container">
        <div class="header">
            <img src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" 
                 width="80" height="80" alt="H-DCN Logo" 
                 onerror="this.style.display='none'" />
            <div>
                <h1 class="title">H-DCN Webshop</h1>
                <h2 class="subtitle">Orderbevestiging</h2>
            </div>
        </div>

        <div>
            <div class="info-row">
                <span class="bold">Ordernummer:</span>
                <span>${escapeHtml(orderData.orderId)}</span>
            </div>
            <div class="info-row">
                <span class="bold">Datum:</span>
                <span>${escapeHtml(formatDate(orderData.timestamp))}</span>
            </div>
            <div class="info-row">
                <span class="bold">Klant:</span>
                <span>${escapeHtml(orderData.customer_info?.name || '')}</span>
            </div>
            <div class="info-row">
                <span class="bold">Status:</span>
                <span class="status">Betaald</span>
            </div>
        </div>

        <hr class="divider" />

        ${orderData.customer_info ? `
        <div class="address-section">
            <div class="address">
                <h3 class="section-title">Factuuradres</h3>
                <div>${escapeHtml(orderData.customer_info.name)}</div>
                <div>${escapeHtml(orderData.customer_info.straat)}</div>
                <div>${escapeHtml(orderData.customer_info.postcode)} ${escapeHtml(orderData.customer_info.woonplaats)}</div>
                ${orderData.customer_info.email ? `<div>${escapeHtml(orderData.customer_info.email)}</div>` : ''}
                ${orderData.customer_info.phone ? `<div>${escapeHtml(orderData.customer_info.phone)}</div>` : ''}
            </div>
            <div class="address">
                <h3 class="section-title">Verzendadres</h3>
                <div>${escapeHtml(orderData.shipping_address?.name || orderData.customer_info.name)}</div>
                <div>${escapeHtml(orderData.shipping_address?.straat || orderData.customer_info.straat)}</div>
                <div>${escapeHtml(orderData.shipping_address?.postcode || orderData.customer_info.postcode)} ${escapeHtml(orderData.shipping_address?.woonplaats || orderData.customer_info.woonplaats)}</div>
            </div>
        </div>
        <hr class="divider" />` : ''}

        ${orderData.delivery_option ? `
        <h3 class="section-title">Levering</h3>
        <div class="info-row">
            <span>${orderData.delivery_option.label}</span>
            <span>€${orderData.delivery_cost}</span>
        </div>
        <hr class="divider" />` : ''}

        <h3 class="section-title">Bestelde producten</h3>
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Optie</th>
                    <th class="text-right">Aantal</th>
                    <th class="text-right">Prijs</th>
                    <th class="text-right">Totaal</th>
                </tr>
            </thead>
            <tbody>
                ${orderData.items.map(item => `
                <tr>
                    <td>${escapeHtml(item.name || item.naam)}</td>
                    <td>${escapeHtml(item.selectedOption || '-')}</td>
                    <td class="text-right">${escapeHtml(item.quantity)}</td>
                    <td class="text-right">€${Number(item.price || 0).toFixed(2)}</td>
                    <td class="text-right">€${(item.quantity * Number(item.price || 0)).toFixed(2)}</td>
                </tr>`).join('')}
            </tbody>
        </table>

        <div>
            <div class="info-row">
                <span>Subtotaal:</span>
                <span>€${orderData.subtotal_amount}</span>
            </div>
            ${orderData.delivery_cost ? `
            <div class="info-row">
                <span>Verzendkosten:</span>
                <span>€${orderData.delivery_cost}</span>
            </div>` : ''}
            <hr style="margin: 8px 0; border: none; border-top: 1px solid #E5E7EB;" />
            <div class="info-row total">
                <span>Totaal betaald:</span>
                <span>€${orderData.total_amount}</span>
            </div>
        </div>
    </div>
</body>
</html>`;
  };

  const openInNewWindow = (): void => {
    const htmlContent = generateHTML();
    const newWindow = window.open('', '_blank');
    if (newWindow) {
      newWindow.document.write(htmlContent);
      newWindow.document.close();
    }
  };

  const downloadHTML = (): void => {
    const htmlContent = generateHTML();
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `orderbevestiging-${orderData.orderId}.html`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }, 100);
  };

  const saveAsFile = (): void => {
    try {
      downloadHTML();
    } catch (error) {
      navigator.clipboard.writeText(generateHTML()).then(() => {
        alert('HTML gekopieerd naar klembord. Plak in een .html bestand.');
      }).catch(() => {
        openInNewWindow();
      });
    }
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
        <button 
          onClick={saveAsFile}
          style={{
            padding: '10px 20px',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            borderRadius: '4px'
          }}
        >
          Download Orderbevestiging
        </button>
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
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: '0' }}>Orderbevestiging</h2>
        </div>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>Ordernummer:</span>
          <span>{orderData.orderId}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>Datum:</span>
          <span>{formatDate(orderData.timestamp)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>Klant:</span>
          <span>{orderData.customer_info?.name || 'Niet beschikbaar'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontWeight: 'bold' }}>Status:</span>
          <span style={{ color: '#22C55E', fontWeight: 'bold' }}>Betaald</span>
        </div>
      </div>

      <hr style={{ margin: '24px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />

      <div style={{ display: 'flex', gap: '40px', marginBottom: '24px' }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>Factuuradres</h3>
          {orderData.customer_info ? (
            <>
              <div>{orderData.customer_info.name || (orderData.customer_info.voornaam + ' ' + orderData.customer_info.achternaam) || 'Naam niet beschikbaar'}</div>
              <div>{orderData.customer_info.straat || 'Adres niet beschikbaar'}</div>
              <div>{(orderData.customer_info.postcode || '') + ' ' + (orderData.customer_info.woonplaats || '') || 'Postcode/plaats niet beschikbaar'}</div>
              {orderData.customer_info.email && <div>{orderData.customer_info.email}</div>}
              {orderData.customer_info.phone && <div>{orderData.customer_info.phone}</div>}
            </>
          ) : (
            <div>Geen adresgegevens beschikbaar</div>
          )}
        </div>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>Verzendadres</h3>
          {orderData.shipping_address || orderData.customer_info ? (
            <>
              <div>{orderData.shipping_address?.name || orderData.customer_info?.name || (orderData.customer_info?.voornaam + ' ' + orderData.customer_info?.achternaam) || 'Naam niet beschikbaar'}</div>
              <div>{orderData.shipping_address?.straat || orderData.customer_info?.straat || 'Adres niet beschikbaar'}</div>
              <div>{(orderData.shipping_address?.postcode || orderData.customer_info?.postcode || '') + ' ' + (orderData.shipping_address?.woonplaats || orderData.customer_info?.woonplaats || '') || 'Postcode/plaats niet beschikbaar'}</div>
            </>
          ) : (
            <div>Geen adresgegevens beschikbaar</div>
          )}
        </div>
      </div>
      <hr style={{ margin: '24px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />

      {orderData.delivery_option && (
        <>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>Levering</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
            <span>{orderData.delivery_option.label}</span>
            <span>€{orderData.delivery_cost}</span>
          </div>
          <hr style={{ margin: '24px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />
        </>
      )}

      <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>Bestelde producten</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '24px' }}>
        <thead>
          <tr style={{ backgroundColor: '#F9FAFB' }}>
            <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>Product</th>
            <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>Optie</th>
            <th style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>Aantal</th>
            <th style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>Prijs</th>
            <th style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB', fontWeight: 'bold' }}>Totaal</th>
          </tr>
        </thead>
        <tbody>
          {orderData.items.map((item, index) => (
            <tr key={index}>
              <td style={{ padding: '8px', borderBottom: '1px solid #E5E7EB' }}>{item.name || item.naam}</td>
              <td style={{ padding: '8px', borderBottom: '1px solid #E5E7EB' }}>{item.selectedOption || '-'}</td>
              <td style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB' }}>{item.quantity}</td>
              <td style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB' }}>€{Number(item.price || 0).toFixed(2)}</td>
              <td style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #E5E7EB' }}>€{(item.quantity * Number(item.price || 0)).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span>Subtotaal:</span>
          <span>€{orderData.subtotal_amount}</span>
        </div>
        {orderData.delivery_cost && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span>Verzendkosten:</span>
            <span>€{orderData.delivery_cost}</span>
          </div>
        )}
        <hr style={{ margin: '8px 0', border: 'none', borderTop: '1px solid #E5E7EB' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '18px', fontWeight: 'bold' }}>
          <span>Totaal betaald:</span>
          <span>€{orderData.total_amount}</span>
        </div>
      </div>
    </div>
    </>
  );
};

export default OrderConfirmation;