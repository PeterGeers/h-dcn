import jsPDF from 'jspdf';
import { FALLBACK_LOGO_BASE64 } from './logoBase64';

interface OrderItem {
  name?: string;
  naam?: string;
  selectedOption?: string;
  quantity: number;
  price?: number;
  [key: string]: any;
}

interface CustomerInfo {
  name: string;
  straat: string;
  postcode: string;
  woonplaats: string;
  email?: string;
  phone?: string;
  [key: string]: any;
}

interface DeliveryOption {
  label: string;
  [key: string]: any;
}

interface OrderData {
  orderId: string;
  timestamp: string;
  items: OrderItem[];
  customer_info?: CustomerInfo;
  delivery_option?: DeliveryOption;
  delivery_cost?: string;
  subtotal_amount: string;
  total_amount: string;
  [key: string]: any;
}

const escapeHtml = (text: any): string => {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
};

const validateOrderData = (orderData: any): boolean => {
  if (!orderData || typeof orderData !== 'object') {
    throw new Error('Invalid order data');
  }
  if (!orderData.orderId || !orderData.timestamp || !Array.isArray(orderData.items)) {
    throw new Error('Missing required order fields');
  }
  return true;
};

export const generateOrderConfirmationHTML = (orderData: OrderData, logoBase64: string = FALLBACK_LOGO_BASE64): string => {
  validateOrderData(orderData);
  const formatDate = (timestamp: string): string => {
    return new Date(timestamp).toLocaleDateString('nl-NL', {
      year: 'numeric',
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const itemsHTML = orderData.items.map((item: OrderItem) => `
    <tr>
      <td style="padding: 8px; border-bottom: 1px solid #eee;">${escapeHtml(item.name || item.naam)}</td>
      <td style="padding: 8px; border-bottom: 1px solid #eee;">${escapeHtml(item.selectedOption) || '-'}</td>
      <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">${Number(item.quantity || 0)}</td>
      <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">€${Number(item.price || 0).toFixed(2)}</td>
      <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">€${(Number(item.quantity || 0) * Number(item.price || 0)).toFixed(2)}</td>
    </tr>
  `).join('');

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Orderbevestiging ${orderData.orderId}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 15px; background-color: white; color: #000000; }
    .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; color: #000000; }
    .header { text-align: center; margin-bottom: 20px; }
    .logo { width: 60px; height: 60px; margin-bottom: 10px; display: block; }
    .title { color: #FF6B35 !important; font-size: 20px; font-weight: bold; margin-bottom: 5px; }
    .subtitle { font-size: 16px; font-weight: bold; margin-bottom: 15px; color: #000000; }
    .info-row { display: flex; justify-content: space-between; margin-bottom: 5px; color: #000000; }
    .section-title { font-size: 14px; font-weight: bold; margin: 15px 0 8px 0; color: #000000; }
    .divider { border-top: 1px solid #333; margin: 12px 0; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 12px; color: #000000; }
    th { background-color: #f0f0f0; padding: 6px; text-align: left; font-weight: bold; color: #000000; }
    td { padding: 6px; color: #000000; }
    .text-right { text-align: right; }
    .total-row { font-weight: bold; font-size: 14px; color: #000000; }
    .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #000000; }
    * { color: #000000 !important; }
    div, span, p { color: #000000 !important; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="${logoBase64}" alt="H-DCN Logo" style="width: 60px; height: 60px; margin: 0 auto 10px auto; display: block;">
      <div class="title">H-DCN Webshop</div>
      <div class="subtitle">Orderbevestiging</div>
    </div>

    <div class="info-row">
      <span><strong>Ordernummer:</strong></span>
      <span>${escapeHtml(orderData.orderId)}</span>
    </div>
    <div class="info-row">
      <span><strong>Datum:</strong></span>
      <span>${formatDate(orderData.timestamp)}</span>
    </div>
    <div class="info-row">
      <span style="color: #000000;"><strong>Status:</strong></span>
      <span style="color: #008000 !important; font-weight: bold;">Betaald</span>
    </div>

    <div class="divider"></div>

    ${orderData.customer_info ? `
    <div class="section-title">Klantgegevens</div>
    <div style="color: #000000;">${escapeHtml(orderData.customer_info.name)}</div>
    <div style="color: #000000;">${escapeHtml(orderData.customer_info.straat)}</div>
    <div style="color: #000000;">${escapeHtml(orderData.customer_info.postcode)} ${escapeHtml(orderData.customer_info.woonplaats)}</div>
    ${orderData.customer_info.email ? `<div style="color: #000000;">${escapeHtml(orderData.customer_info.email)}</div>` : ''}
    ${orderData.customer_info.phone ? `<div style="color: #000000;">${escapeHtml(orderData.customer_info.phone)}</div>` : ''}
    <div class="divider"></div>
    ` : ''}

    ${orderData.delivery_option ? `
    <div class="section-title">Levering</div>
    <div class="info-row">
      <span>${escapeHtml(orderData.delivery_option.label)}</span>
      <span>€${orderData.delivery_cost}</span>
    </div>
    <div class="divider"></div>
    ` : ''}

    <div class="section-title">Bestelde producten</div>
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
        ${itemsHTML}
      </tbody>
    </table>

    <div class="divider"></div>

    <div class="info-row">
      <span style="color: #000000;">Subtotaal:</span>
      <span style="color: #000000;">€${orderData.subtotal_amount}</span>
    </div>
    ${orderData.delivery_cost ? `
    <div class="info-row">
      <span style="color: #000000;">Verzendkosten:</span>
      <span style="color: #000000;">€${orderData.delivery_cost}</span>
    </div>
    ` : ''}
    <div class="divider"></div>
    <div class="info-row total-row">
      <span style="color: #000000;">Totaal betaald:</span>
      <span style="color: #000000;">€${orderData.total_amount}</span>
    </div>

    <div class="divider"></div>

    <div class="footer">
      <p>Bedankt voor uw bestelling bij H-DCN Webshop!</p>
      <p>Voor vragen over uw bestelling kunt u contact opnemen via email of telefoon.</p>
      <p><strong>Ordernummer: ${orderData.orderId}</strong></p>
    </div>
  </div>
</body>
</html>
  `;
};

export const generateOrderConfirmationPDF = async (orderData: OrderData): Promise<boolean> => {
  try {
    validateOrderData(orderData);
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageWidth = 210;
    const pageHeight = 297;
    const margin = 15;
    let yPosition = margin;
    
    const addHeader = (): number => {
      pdf.setFontSize(10);
      pdf.setTextColor(0, 0, 0);
      pdf.text(`Ordernummer: ${orderData.orderId}`, margin, 20);
      return 35;
    };
    
    const addFooter = (pageNum: number): void => {
      pdf.setFontSize(8);
      pdf.setTextColor(100, 100, 100);
      pdf.text(`Pagina ${pageNum}`, pageWidth - margin, pageHeight - 10, { align: 'right' });
      pdf.text(`H-DCN Webshop - Orderbevestiging ${orderData.orderId}`, margin, pageHeight - 10);
    };
    
    const checkNewPage = (neededHeight: number): boolean => {
      if (yPosition + neededHeight > pageHeight - 30) {
        addFooter((pdf as any).internal.getNumberOfPages());
        pdf.addPage();
        yPosition = addHeader();
        return true;
      }
      return false;
    };
    
    pdf.setFontSize(20);
    pdf.setTextColor(255, 107, 53);
    pdf.text('H-DCN Webshop', pageWidth / 2, yPosition + 10, { align: 'center' });
    
    pdf.setFontSize(16);
    pdf.setTextColor(0, 0, 0);
    pdf.text('Orderbevestiging', pageWidth / 2, yPosition + 20, { align: 'center' });
    yPosition += 35;
    
    pdf.setFontSize(12);
    pdf.text(`Ordernummer: ${orderData.orderId}`, margin, yPosition);
    yPosition += 8;
    
    const formatDate = (timestamp: string): string => {
      return new Date(timestamp).toLocaleDateString('nl-NL', {
        year: 'numeric', month: 'long', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    };
    
    pdf.text(`Datum: ${formatDate(orderData.timestamp)}`, margin, yPosition);
    yPosition += 8;
    
    pdf.setTextColor(0, 128, 0);
    pdf.text('Status: Betaald', margin, yPosition);
    pdf.setTextColor(0, 0, 0);
    yPosition += 15;
    
    if (orderData.customer_info) {
      checkNewPage(40);
      pdf.setFontSize(14);
      pdf.setFont(undefined, 'bold');
      pdf.text('Klantgegevens', margin, yPosition);
      pdf.setFont(undefined, 'normal');
      yPosition += 10;
      
      pdf.setFontSize(10);
      pdf.text(orderData.customer_info.name, margin, yPosition);
      yPosition += 6;
      pdf.text(orderData.customer_info.straat, margin, yPosition);
      yPosition += 6;
      pdf.text(`${orderData.customer_info.postcode} ${orderData.customer_info.woonplaats}`, margin, yPosition);
      yPosition += 6;
      if (orderData.customer_info.email) {
        pdf.text(orderData.customer_info.email, margin, yPosition);
        yPosition += 6;
      }
      if (orderData.customer_info.phone) {
        pdf.text(orderData.customer_info.phone, margin, yPosition);
        yPosition += 6;
      }
      yPosition += 10;
    }
    
    if (orderData.delivery_option) {
      checkNewPage(25);
      pdf.setFontSize(14);
      pdf.setFont(undefined, 'bold');
      pdf.text('Levering', margin, yPosition);
      pdf.setFont(undefined, 'normal');
      yPosition += 10;
      
      pdf.setFontSize(10);
      pdf.text(`${orderData.delivery_option.label}: €${orderData.delivery_cost}`, margin, yPosition);
      yPosition += 15;
    }
    
    checkNewPage(50);
    pdf.setFontSize(14);
    pdf.setFont(undefined, 'bold');
    pdf.text('Bestelde producten', margin, yPosition);
    yPosition += 15;
    
    pdf.setFontSize(9);
    pdf.setFont(undefined, 'bold');
    const colWidths = [80, 30, 20, 25, 25];
    let xPos = margin;
    
    pdf.text('Product', xPos, yPosition);
    xPos += colWidths[0];
    pdf.text('Optie', xPos, yPosition);
    xPos += colWidths[1];
    pdf.text('Aantal', xPos + colWidths[2], yPosition, { align: 'right' });
    xPos += colWidths[2];
    pdf.text('Prijs', xPos + colWidths[3], yPosition, { align: 'right' });
    xPos += colWidths[3];
    pdf.text('Totaal', xPos + colWidths[4], yPosition, { align: 'right' });
    yPosition += 8;
    
    pdf.setFont(undefined, 'normal');
    orderData.items.forEach((item: OrderItem) => {
      checkNewPage(12);
      xPos = margin;
      
      const productName = (item.name || item.naam).substring(0, 35);
      pdf.text(productName, xPos, yPosition);
      xPos += colWidths[0];
      
      pdf.text(item.selectedOption || '-', xPos, yPosition);
      xPos += colWidths[1];
      
      pdf.text(item.quantity.toString(), xPos + colWidths[2], yPosition, { align: 'right' });
      xPos += colWidths[2];
      
      pdf.text(`€${Number(item.price || 0).toFixed(2)}`, xPos + colWidths[3], yPosition, { align: 'right' });
      xPos += colWidths[3];
      
      pdf.text(`€${(item.quantity * Number(item.price || 0)).toFixed(2)}`, xPos + colWidths[4], yPosition, { align: 'right' });
      yPosition += 8;
    });
    
    yPosition += 10;
    
    checkNewPage(35);
    pdf.setFontSize(10);
    const totalsX = pageWidth - margin - 50;
    
    pdf.text(`Subtotaal: €${orderData.subtotal_amount}`, totalsX, yPosition);
    yPosition += 8;
    
    if (orderData.delivery_cost) {
      pdf.text(`Verzending: €${orderData.delivery_cost}`, totalsX, yPosition);
      yPosition += 8;
    }
    
    pdf.setFont(undefined, 'bold');
    pdf.text(`Totaal: €${orderData.total_amount}`, totalsX, yPosition);
    
    addFooter((pdf as any).internal.getNumberOfPages());
    
    pdf.save(`orderbevestiging-${orderData.orderId}.pdf`);
    
    return true;
  } catch (error) {
    console.error('PDF generation failed:', error);
    return false;
  }
};