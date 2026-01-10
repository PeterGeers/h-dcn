/**
 * Address Label Service for H-DCN Reporting
 * 
 * This service handles the generation of address labels in various formats
 * with support for different label sheet layouts and printing options.
 */

import jsPDF from 'jspdf';
import { Member } from '../types/index';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface LabelFormat {
  id: string;
  name: string;
  description: string;
  columns: number;
  rows: number;
  labelWidth: number; // in mm
  labelHeight: number; // in mm
  marginTop: number; // in mm
  marginLeft: number; // in mm
  marginRight: number; // in mm
  marginBottom: number; // in mm
  gapHorizontal: number; // in mm
  gapVertical: number; // in mm
  pageWidth: number; // in mm (A4 = 210)
  pageHeight: number; // in mm (A4 = 297)
}

export interface LabelStyle {
  fontSize: number;
  fontFamily: string;
  lineHeight: number;
  padding: number; // in mm
  alignment: 'left' | 'center' | 'right';
  includeBorder: boolean;
  borderWidth: number; // in mm
}

export interface AddressLabelOptions {
  format: LabelFormat;
  style: LabelStyle;
  includeCountry: boolean;
  countryFilter: string;
  sortBy: 'name' | 'postcode' | 'region';
  startPosition: number;
}

export interface LabelGenerationResult {
  success: boolean;
  filename?: string;
  error?: string;
  labelCount?: number;
  pageCount?: number;
}

// ============================================================================
// PREDEFINED LABEL FORMATS
// ============================================================================

export const STANDARD_LABEL_FORMATS: LabelFormat[] = [
  {
    id: 'avery-l7160',
    name: 'Avery L7160 (21 labels)',
    description: '63.5 x 38.1mm - 3 columns, 7 rows',
    columns: 3,
    rows: 7,
    labelWidth: 63.5,
    labelHeight: 38.1,
    marginTop: 15.5,
    marginLeft: 7,
    marginRight: 7,
    marginBottom: 13,
    gapHorizontal: 2.5,
    gapVertical: 0,
    pageWidth: 210,
    pageHeight: 297
  },
  {
    id: 'avery-l7163',
    name: 'Avery L7163 (14 labels)',
    description: '99.1 x 38.1mm - 2 columns, 7 rows',
    columns: 2,
    rows: 7,
    labelWidth: 99.1,
    labelHeight: 38.1,
    marginTop: 15.5,
    marginLeft: 4.65,
    marginRight: 4.65,
    marginBottom: 13,
    gapHorizontal: 2.3,
    gapVertical: 0,
    pageWidth: 210,
    pageHeight: 297
  },
  {
    id: 'avery-l7162',
    name: 'Avery L7162 (16 labels)',
    description: '99.1 x 33.9mm - 2 columns, 8 rows',
    columns: 2,
    rows: 8,
    labelWidth: 99.1,
    labelHeight: 33.9,
    marginTop: 15.5,
    marginLeft: 4.65,
    marginRight: 4.65,
    marginBottom: 13,
    gapHorizontal: 2.3,
    gapVertical: 0,
    pageWidth: 210,
    pageHeight: 297
  },
  {
    id: 'avery-l7161',
    name: 'Avery L7161 (18 labels)',
    description: '63.5 x 46.6mm - 3 columns, 6 rows',
    columns: 3,
    rows: 6,
    labelWidth: 63.5,
    labelHeight: 46.6,
    marginTop: 15.5,
    marginLeft: 7,
    marginRight: 7,
    marginBottom: 13,
    gapHorizontal: 2.5,
    gapVertical: 0,
    pageWidth: 210,
    pageHeight: 297
  },
  {
    id: 'custom-large',
    name: 'Large Labels (8 labels)',
    description: '105 x 74mm - 2 columns, 4 rows',
    columns: 2,
    rows: 4,
    labelWidth: 105,
    labelHeight: 74,
    marginTop: 13,
    marginLeft: 0,
    marginRight: 0,
    marginBottom: 13,
    gapHorizontal: 0,
    gapVertical: 0,
    pageWidth: 210,
    pageHeight: 297
  }
];

export const DEFAULT_LABEL_STYLE: LabelStyle = {
  fontSize: 10,
  fontFamily: 'Arial, sans-serif',
  lineHeight: 1.2,
  padding: 2,
  alignment: 'left',
  includeBorder: false,
  borderWidth: 0.1
};

// ============================================================================
// ADDRESS LABEL SERVICE CLASS
// ============================================================================

export class AddressLabelService {
  private static instance: AddressLabelService;

  private constructor() {}

  public static getInstance(): AddressLabelService {
    if (!AddressLabelService.instance) {
      AddressLabelService.instance = new AddressLabelService();
    }
    return AddressLabelService.instance;
  }

  // ============================================================================
  // MEMBER PROCESSING METHODS
  // ============================================================================

  /**
   * Filter and sort members for label generation
   */
  public processMembers(
    members: Member[],
    options: Partial<AddressLabelOptions>
  ): Member[] {
    let filtered = members.filter(member => this.isValidAddress(member));

    // Apply country filter
    if (options.countryFilter && options.countryFilter !== 'all') {
      filtered = filtered.filter(member => {
        const memberCountry = member.land || 'Nederland';
        return memberCountry === options.countryFilter;
      });
    }

    // Sort members
    const sortBy = options.sortBy || 'name';
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'postcode':
          return (a.postcode || '').localeCompare(b.postcode || '');
        case 'region':
          return (a.regio || '').localeCompare(b.regio || '');
        case 'name':
        default:
          return (a.korte_naam || '').localeCompare(b.korte_naam || '');
      }
    });

    return filtered;
  }

  /**
   * Check if member has valid address data
   */
  public isValidAddress(member: Member): boolean {
    return !!(
      member.korte_naam &&
      member.straat &&
      member.postcode &&
      member.woonplaats
    );
  }

  /**
   * Format member address for label printing
   */
  public formatAddress(member: Member, includeCountry: boolean = false): string[] {
    const lines: string[] = [];
    
    // Name
    if (member.korte_naam) {
      lines.push(member.korte_naam);
    }
    
    // Street address
    if (member.straat) {
      lines.push(member.straat);
    }
    
    // Postal code and city
    const postalLine = [member.postcode, member.woonplaats].filter(Boolean).join('  ');
    if (postalLine) {
      lines.push(postalLine);
    }
    
    // Country (if enabled and not Netherlands)
    if (includeCountry && member.land && member.land !== 'Nederland') {
      lines.push(member.land.toUpperCase());
    }
    
    return lines;
  }

  // ============================================================================
  // PDF GENERATION METHODS
  // ============================================================================

  /**
   * Generate PDF with address labels
   */
  public async generateLabelsPDF(
    members: Member[],
    options: AddressLabelOptions
  ): Promise<LabelGenerationResult> {
    try {
      // Process members
      const processedMembers = this.processMembers(members, options);
      
      if (processedMembers.length === 0) {
        return {
          success: false,
          error: 'No valid addresses found for label generation'
        };
      }

      // Create PDF
      const doc = new jsPDF('p', 'mm', 'a4');
      const { format, style } = options;
      
      let labelIndex = options.startPosition || 0;
      let currentPage = 1;
      
      // Generate labels
      processedMembers.forEach((member, memberIndex) => {
        const addressLines = this.formatAddress(member, options.includeCountry);
        if (addressLines.length === 0) return;
        
        // Calculate position on page
        const pagePosition = labelIndex % (format.columns * format.rows);
        const row = Math.floor(pagePosition / format.columns);
        const col = pagePosition % format.columns;
        
        // Add new page if needed
        if (labelIndex > options.startPosition && pagePosition === 0) {
          doc.addPage();
          currentPage++;
        }
        
        // Calculate coordinates
        const x = format.marginLeft + col * (format.labelWidth + format.gapHorizontal);
        const y = format.marginTop + row * (format.labelHeight + format.gapVertical);
        
        // Draw label
        this.drawLabel(doc, addressLines, x, y, format, style);
        
        labelIndex++;
      });
      
      // Calculate final page count
      const totalLabels = processedMembers.length + (options.startPosition || 0);
      const pageCount = Math.ceil(totalLabels / (format.columns * format.rows));
      
      // Generate filename
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `hdcn-address-labels-${format.id}-${timestamp}.pdf`;
      
      // Save PDF
      doc.save(filename);
      
      return {
        success: true,
        filename,
        labelCount: processedMembers.length,
        pageCount
      };
      
    } catch (error) {
      console.error('Error generating labels PDF:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  /**
   * Draw a single label on the PDF
   */
  private drawLabel(
    doc: jsPDF,
    addressLines: string[],
    x: number,
    y: number,
    format: LabelFormat,
    style: LabelStyle
  ): void {
    // Set font
    doc.setFontSize(style.fontSize);
    doc.setFont('helvetica', 'normal');
    
    // Draw border if enabled
    if (style.includeBorder) {
      doc.setLineWidth(style.borderWidth);
      doc.rect(x, y, format.labelWidth, format.labelHeight);
    }
    
    // Calculate line height in mm
    const lineHeight = style.fontSize * style.lineHeight * 0.352778; // Convert pt to mm
    let currentY = y + style.padding + lineHeight;
    
    // Write address lines
    addressLines.forEach((line, lineIndex) => {
      if (currentY + lineHeight <= y + format.labelHeight - style.padding) {
        let textX = x + style.padding;
        
        // Apply alignment
        if (style.alignment === 'center') {
          textX = x + format.labelWidth / 2;
          doc.text(line, textX, currentY, { align: 'center' });
        } else if (style.alignment === 'right') {
          textX = x + format.labelWidth - style.padding;
          doc.text(line, textX, currentY, { align: 'right' });
        } else {
          doc.text(line, textX, currentY);
        }
        
        currentY += lineHeight;
      }
    });
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Get available label formats
   */
  public getAvailableFormats(): LabelFormat[] {
    return STANDARD_LABEL_FORMATS;
  }

  /**
   * Get label format by ID
   */
  public getFormatById(id: string): LabelFormat | undefined {
    return STANDARD_LABEL_FORMATS.find(format => format.id === id);
  }

  /**
   * Get unique countries from member list
   */
  public getAvailableCountries(members: Member[]): string[] {
    const countries = new Set(members.map(m => m.land || 'Nederland'));
    return Array.from(countries).sort();
  }

  /**
   * Calculate estimated page count
   */
  public calculatePageCount(
    memberCount: number,
    format: LabelFormat,
    startPosition: number = 0
  ): number {
    const totalLabels = memberCount + startPosition;
    const labelsPerPage = format.columns * format.rows;
    return Math.ceil(totalLabels / labelsPerPage);
  }

  /**
   * Validate label generation options
   */
  public validateOptions(options: AddressLabelOptions): string[] {
    const errors: string[] = [];
    
    if (!options.format) {
      errors.push('Label format is required');
    }
    
    if (!options.style) {
      errors.push('Label style is required');
    }
    
    if (options.style && options.style.fontSize < 6) {
      errors.push('Font size must be at least 6pt');
    }
    
    if (options.style && options.style.fontSize > 20) {
      errors.push('Font size must be no more than 20pt');
    }
    
    if (options.startPosition < 0) {
      errors.push('Start position cannot be negative');
    }
    
    if (options.format && options.startPosition >= (options.format.columns * options.format.rows)) {
      errors.push('Start position exceeds labels per page');
    }
    
    return errors;
  }

  /**
   * Generate preview data for UI
   */
  public generatePreviewData(
    members: Member[],
    options: Partial<AddressLabelOptions>,
    maxLabels: number = 20
  ): Array<{ member: Member; addressLines: string[] }> {
    const processedMembers = this.processMembers(members, options);
    const includeCountry = options.includeCountry || false;
    
    return processedMembers
      .slice(0, maxLabels)
      .map(member => ({
        member,
        addressLines: this.formatAddress(member, includeCountry)
      }))
      .filter(item => item.addressLines.length > 0);
  }

  /**
   * Export address data to CSV format
   */
  public exportToCSV(members: Member[], options: Partial<AddressLabelOptions>): string {
    const processedMembers = this.processMembers(members, options);
    const includeCountry = options.includeCountry || false;
    
    const headers = ['Naam', 'Straat', 'Postcode', 'Woonplaats'];
    if (includeCountry) {
      headers.push('Land');
    }
    headers.push('Regio');
    
    const csvLines = [headers.join(',')];
    
    processedMembers.forEach(member => {
      const row = [
        this.escapeCsvValue(member.korte_naam || ''),
        this.escapeCsvValue(member.straat || ''),
        this.escapeCsvValue(member.postcode || ''),
        this.escapeCsvValue(member.woonplaats || '')
      ];
      
      if (includeCountry) {
        row.push(this.escapeCsvValue(member.land || 'Nederland'));
      }
      
      row.push(this.escapeCsvValue(member.regio || ''));
      
      csvLines.push(row.join(','));
    });
    
    return csvLines.join('\n');
  }

  /**
   * Escape CSV values
   */
  private escapeCsvValue(value: string): string {
    if (!value) return '';
    
    const stringValue = value.toString();
    
    // If the value contains comma, quote, or newline, wrap in quotes and escape internal quotes
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    
    return stringValue;
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const addressLabelService = AddressLabelService.getInstance();
export default AddressLabelService;