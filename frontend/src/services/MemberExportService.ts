/**
 * Member Export Service for H-DCN Reporting
 * 
 * This service handles exporting processed member data to various formats:
 * - CSV: Comma-separated values for spreadsheet applications
 * - XLSX: Excel format with formatting and multiple sheets
 * - PDF: Formatted documents for printing and sharing
 * 
 * Key Features:
 * - Uses processed parquet data with calculated fields
 * - Supports predefined export views from memberFields.ts
 * - Regional filtering and permission-based access
 * - Professional formatting and H-DCN branding
 * - Multiple export formats with consistent data
 */

import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import { Member } from '../types/index';
import { getMemberFullName } from '../utils/calculatedFields';
import { MEMBER_TABLE_CONTEXTS, MEMBER_FIELDS } from '../config/memberFields';
import { renderFieldValue } from '../utils/fieldRenderers';
import { googleMailService, DistributionListResult } from './GoogleMailService';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export type ExportFormat = 'csv' | 'xlsx' | 'pdf' | 'txt' | 'google-contacts';

export interface ExportOptions {
  format: ExportFormat;
  filename?: string;
  includeHeaders?: boolean;
  dateFormat?: string;
  delimiter?: string; // For CSV exports
  sheetName?: string; // For XLSX exports
  orientation?: 'portrait' | 'landscape'; // For PDF exports
  includeTimestamp?: boolean;
}

export interface ExportResult {
  success: boolean;
  filename?: string;
  error?: string;
  recordCount?: number;
  fileSize?: number;
  googleResult?: DistributionListResult; // For Google Contacts exports
}

export interface ExportPreview {
  headers: string[];
  sampleRows: string[][];
  totalRecords: number;
  estimatedFileSize: string;
}

// Predefined export views for common use cases
export interface ExportViewConfig {
  name: string;
  description: string;
  contextName: string;
  filter?: (member: Member) => boolean;
  customColumns?: Array<{
    key: string;
    label: string;
    getValue: (member: Member) => string;
  }>;
  defaultFormat: ExportFormat;
  permissions: {
    view: string[];
    export: string[];
  };
  regionalRestricted?: boolean;
}

// ============================================================================
// PREDEFINED EXPORT VIEWS
// ============================================================================

export const EXPORT_VIEWS: Record<string, ExportViewConfig> = {
  // Address labels for paper clubblad distribution
  addressStickersPaper: {
    name: 'Address Stickers (Paper)',
    description: 'Address labels for paper clubblad distribution',
    contextName: 'communicationView',
    filter: (member: Member) => 
      member.status === 'Actief' && member.clubblad === 'Papier',
    customColumns: [
      { key: 'korte_naam', label: 'Naam', getValue: (m) => m.korte_naam || '' },
      { key: 'straat', label: 'Straat', getValue: (m) => m.straat || '' },
      { key: 'postcode', label: 'Postcode', getValue: (m) => m.postcode || '' },
      { key: 'woonplaats', label: 'Woonplaats', getValue: (m) => m.woonplaats || '' },
      { key: 'land', label: 'Land', getValue: (m) => m.land || 'Nederland' }
    ],
    defaultFormat: 'xlsx',
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'Communication_Read'],
      export: ['Members_CRUD', 'Communication_CRUD']
    },
    regionalRestricted: false
  },

  // Address labels for regional mailings
  addressStickersRegional: {
    name: 'Address Stickers (Regional)',
    description: 'Address labels for regional mailings',
    contextName: 'communicationView',
    filter: (member: Member) => member.status === 'Actief',
    customColumns: [
      { key: 'korte_naam', label: 'Naam', getValue: (m) => m.korte_naam || '' },
      { key: 'straat', label: 'Straat', getValue: (m) => m.straat || '' },
      { key: 'postcode', label: 'Postcode', getValue: (m) => m.postcode || '' },
      { key: 'woonplaats', label: 'Woonplaats', getValue: (m) => m.woonplaats || '' },
      { key: 'land', label: 'Land', getValue: (m) => m.land || 'Nederland' }
    ],
    defaultFormat: 'xlsx',
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_CRUD']
    },
    regionalRestricted: true
  },

  // Email groups for digital clubblad
  emailGroupsDigital: {
    name: 'Email Groups (Digital)',
    description: 'Email addresses for digital clubblad distribution',
    contextName: 'communicationView',
    filter: (member: Member) => 
      member.status === 'Actief' && 
      member.clubblad === 'Digitaal' && 
      member.email && member.email.trim() !== '',
    customColumns: [
      { key: 'korte_naam', label: 'Naam', getValue: (m) => m.korte_naam || '' },
      { key: 'email', label: 'Email', getValue: (m) => m.email || '' }
    ],
    defaultFormat: 'csv',
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'Communication_Read'],
      export: ['Members_CRUD', 'Communication_CRUD']
    },
    regionalRestricted: false
  },

  // Email groups for regional communication
  emailGroupsRegional: {
    name: 'Email Groups (Regional)',
    description: 'Email addresses for regional communication',
    contextName: 'communicationView',
    filter: (member: Member) => 
      member.status === 'Actief' && 
      member.email && member.email.trim() !== '',
    customColumns: [
      { key: 'korte_naam', label: 'Naam', getValue: (m) => m.korte_naam || '' },
      { key: 'email', label: 'Email', getValue: (m) => m.email || '' },
      { key: 'regio', label: 'Regio', getValue: (m) => m.regio || '' }
    ],
    defaultFormat: 'csv',
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_CRUD']
    },
    regionalRestricted: true
  },

  // Birthday list with addresses
  birthdayList: {
    name: 'Birthday List with Addresses',
    description: 'Member birthdays with full addresses for cards/gifts',
    contextName: 'memberOverview',
    filter: (member: Member) => member.status === 'Actief',
    customColumns: [
      { key: 'korte_naam', label: 'Naam', getValue: (m) => m.korte_naam || '' },
      { key: 'verjaardag', label: 'Verjaardag', getValue: (m) => m.verjaardag || '' },
      { key: 'straat', label: 'Straat', getValue: (m) => m.straat || '' },
      { key: 'postcode', label: 'Postcode', getValue: (m) => m.postcode || '' },
      { key: 'woonplaats', label: 'Woonplaats', getValue: (m) => m.woonplaats || '' },
      { key: 'land', label: 'Land', getValue: (m) => m.land || 'Nederland' },
      { key: 'email', label: 'Email', getValue: (m) => m.email || '' },
      { key: 'telefoon', label: 'Telefoon', getValue: (m) => m.telefoon || '' }
    ],
    defaultFormat: 'xlsx',
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_CRUD']
    },
    regionalRestricted: true
  }
};

// ============================================================================
// MEMBER EXPORT SERVICE CLASS
// ============================================================================

export class MemberExportService {
  private static instance: MemberExportService;

  private constructor() {}

  public static getInstance(): MemberExportService {
    if (!MemberExportService.instance) {
      MemberExportService.instance = new MemberExportService();
    }
    return MemberExportService.instance;
  }

  // ============================================================================
  // MAIN EXPORT METHODS
  // ============================================================================

  /**
   * Export members using a predefined export view
   */
  public async exportView(
    viewName: string,
    members: Member[],
    options: Partial<ExportOptions> = {}
  ): Promise<ExportResult> {
    try {
      const view = EXPORT_VIEWS[viewName];
      if (!view) {
        throw new Error(`Export view '${viewName}' not found`);
      }

      // Apply view filter
      const filteredMembers = view.filter ? members.filter(view.filter) : members;

      // For Google Contacts export, pass additional data
      if (options.format === 'google-contacts') {
        const exportOptions = {
          format: 'google-contacts' as ExportFormat,
          filename: this.generateFilename(view.name, 'google-contacts'),
          viewName,
          members: filteredMembers,
          ...options
        };
        
        // Use custom columns if defined, otherwise use table context
        if (view.customColumns) {
          return this.exportCustomColumns(
            filteredMembers,
            view.customColumns,
            exportOptions
          );
        } else {
          return this.exportTableContext(
            view.contextName,
            filteredMembers,
            exportOptions
          );
        }
      }

      // Use custom columns if defined, otherwise use table context
      if (view.customColumns) {
        return this.exportCustomColumns(
          filteredMembers,
          view.customColumns,
          {
            format: view.defaultFormat,
            filename: this.generateFilename(view.name, view.defaultFormat),
            ...options
          }
        );
      } else {
        return this.exportTableContext(
          view.contextName,
          filteredMembers,
          {
            format: view.defaultFormat,
            filename: this.generateFilename(view.name, view.defaultFormat),
            ...options
          }
        );
      }
    } catch (error) {
      console.error('Export view error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  /**
   * Export members using a table context configuration
   */
  public async exportTableContext(
    contextName: string,
    members: Member[],
    options: Partial<ExportOptions> = {}
  ): Promise<ExportResult> {
    try {
      const context = MEMBER_TABLE_CONTEXTS[contextName];
      if (!context) {
        throw new Error(`Table context '${contextName}' not found`);
      }

      // Get visible columns in order
      const visibleColumns = context.columns
        .filter(col => col.visible)
        .sort((a, b) => a.order - b.order);

      // Prepare data
      const headers = visibleColumns.map(col => {
        const field = MEMBER_FIELDS[col.fieldKey];
        return field?.label || col.fieldKey;
      });

      const rows = members.map(member => 
        visibleColumns.map(col => {
          const field = MEMBER_FIELDS[col.fieldKey];
          const value = member[col.fieldKey as keyof Member];
          return field ? renderFieldValue(field, value) || '' : String(value || '');
        })
      );

      const exportOptions: ExportOptions = {
        format: 'csv',
        filename: this.generateFilename(context.name, 'csv'),
        includeHeaders: true,
        includeTimestamp: true,
        ...options
      };

      return this.performExport(headers, rows, exportOptions);
    } catch (error) {
      console.error('Export table context error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  /**
   * Export members using custom column definitions
   */
  public async exportCustomColumns(
    members: Member[],
    columns: Array<{ key: string; label: string; getValue: (member: Member) => string }>,
    options: Partial<ExportOptions> = {}
  ): Promise<ExportResult> {
    try {
      const headers = columns.map(col => col.label);
      const rows = members.map(member => 
        columns.map(col => col.getValue(member) || '')
      );

      const exportOptions: ExportOptions = {
        format: 'csv',
        includeHeaders: true,
        includeTimestamp: true,
        ...options
      };

      return this.performExport(headers, rows, exportOptions);
    } catch (error) {
      console.error('Export custom columns error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  // ============================================================================
  // FORMAT-SPECIFIC EXPORT METHODS
  // ============================================================================

  /**
   * Perform the actual export based on format
   */
  private async performExport(
    headers: string[],
    rows: string[][],
    options: ExportOptions
  ): Promise<ExportResult> {
    try {
      switch (options.format) {
        case 'csv':
          return this.exportToCSV(headers, rows, options);
        case 'xlsx':
          return this.exportToXLSX(headers, rows, options);
        case 'pdf':
          return this.exportToPDF(headers, rows, options);
        case 'txt':
          return this.exportToTXT(headers, rows, options);
        case 'google-contacts':
          return this.exportToGoogleContacts(headers, rows, options);
        default:
          throw new Error(`Unsupported export format: ${options.format}`);
      }
    } catch (error) {
      console.error('Perform export error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  /**
   * Export to CSV format
   */
  private exportToCSV(
    headers: string[],
    rows: string[][],
    options: ExportOptions
  ): ExportResult {
    try {
      const delimiter = options.delimiter || ',';
      const lines: string[] = [];

      // Add headers if requested
      if (options.includeHeaders) {
        lines.push(headers.map(h => this.escapeCsvValue(h)).join(delimiter));
      }

      // Add data rows
      rows.forEach(row => {
        lines.push(row.map(cell => this.escapeCsvValue(cell)).join(delimiter));
      });

      // Add timestamp if requested
      if (options.includeTimestamp) {
        lines.push('');
        lines.push(`# Exported on ${new Date().toLocaleString('nl-NL')}`);
      }

      const csvContent = lines.join('\n');
      const filename = options.filename || this.generateFilename('export', 'csv');

      // Create and download file
      this.downloadFile(csvContent, filename, 'text/csv;charset=utf-8;');

      return {
        success: true,
        filename,
        recordCount: rows.length,
        fileSize: new Blob([csvContent]).size
      };
    } catch (error) {
      console.error('CSV export error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'CSV export failed'
      };
    }
  }

  /**
   * Export to Excel (XLSX) format
   */
  private exportToXLSX(
    headers: string[],
    rows: string[][],
    options: ExportOptions
  ): ExportResult {
    try {
      // Create workbook and worksheet
      const workbook = XLSX.utils.book_new();
      const sheetName = options.sheetName || 'Members';

      // Prepare data for worksheet
      const worksheetData: string[][] = [];
      
      if (options.includeHeaders) {
        worksheetData.push(headers);
      }
      
      worksheetData.push(...rows);

      // Add timestamp if requested
      if (options.includeTimestamp) {
        worksheetData.push([]);
        worksheetData.push([`Exported on ${new Date().toLocaleString('nl-NL')}`]);
      }

      // Create worksheet
      const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);

      // Apply basic formatting
      const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1');
      
      // Set column widths
      const columnWidths = headers.map((header, index) => {
        const maxLength = Math.max(
          header.length,
          ...rows.map(row => (row[index] || '').toString().length)
        );
        return { wch: Math.min(Math.max(maxLength + 2, 10), 50) };
      });
      worksheet['!cols'] = columnWidths;

      // Style header row if present
      if (options.includeHeaders) {
        for (let col = 0; col < headers.length; col++) {
          const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col });
          if (worksheet[cellAddress]) {
            worksheet[cellAddress].s = {
              font: { bold: true },
              fill: { fgColor: { rgb: 'E6E6E6' } }
            };
          }
        }
      }

      // Add worksheet to workbook
      XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);

      // Generate file
      const filename = options.filename || this.generateFilename('export', 'xlsx');
      const buffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
      const blob = new Blob([buffer], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });

      // Download file
      this.downloadBlob(blob, filename);

      return {
        success: true,
        filename,
        recordCount: rows.length,
        fileSize: blob.size
      };
    } catch (error) {
      console.error('XLSX export error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Excel export failed'
      };
    }
  }

  /**
   * Export to PDF format
   */
  private exportToPDF(
    headers: string[],
    rows: string[][],
    options: ExportOptions
  ): ExportResult {
    try {
      const orientation = options.orientation || 'landscape';
      const doc = new jsPDF(orientation);

      // Add H-DCN header
      doc.setFontSize(16);
      doc.text('H-DCN Ledenexport', 20, 20);
      
      if (options.includeTimestamp) {
        doc.setFontSize(10);
        doc.text(`Gegenereerd op: ${new Date().toLocaleString('nl-NL')}`, 20, 30);
      }

      // Prepare table data
      const tableData = options.includeHeaders ? [headers, ...rows] : rows;

      // Add table using autoTable plugin
      (doc as any).autoTable({
        head: options.includeHeaders ? [headers] : undefined,
        body: options.includeHeaders ? rows : tableData,
        startY: 40,
        styles: {
          fontSize: 8,
          cellPadding: 2
        },
        headStyles: {
          fillColor: [230, 230, 230],
          textColor: [0, 0, 0],
          fontStyle: 'bold'
        },
        columnStyles: {
          // Auto-adjust column widths based on content
        },
        margin: { top: 40, right: 20, bottom: 20, left: 20 },
        tableWidth: 'auto',
        theme: 'grid'
      });

      // Generate and download PDF
      const filename = options.filename || this.generateFilename('export', 'pdf');
      doc.save(filename);

      return {
        success: true,
        filename,
        recordCount: rows.length
      };
    } catch (error) {
      console.error('PDF export error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'PDF export failed'
      };
    }
  }

  /**
   * Export to plain text format (for email lists)
   */
  private exportToTXT(
    headers: string[],
    rows: string[][],
    options: ExportOptions
  ): ExportResult {
    try {
      const lines: string[] = [];

      // Add headers if requested
      if (options.includeHeaders) {
        lines.push(headers.join('\t'));
        lines.push(''); // Empty line after headers
      }

      // Add data rows
      rows.forEach(row => {
        lines.push(row.join('\t'));
      });

      // Add timestamp if requested
      if (options.includeTimestamp) {
        lines.push('');
        lines.push(`# Exported on ${new Date().toLocaleString('nl-NL')}`);
      }

      const txtContent = lines.join('\n');
      const filename = options.filename || this.generateFilename('export', 'txt');

      // Create and download file
      this.downloadFile(txtContent, filename, 'text/plain;charset=utf-8;');

      return {
        success: true,
        filename,
        recordCount: rows.length,
        fileSize: new Blob([txtContent]).size
      };
    } catch (error) {
      console.error('TXT export error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Text export failed'
      };
    }
  }

  /**
   * Export to Google Contacts as distribution list
   */
  private async exportToGoogleContacts(
    headers: string[],
    rows: string[][],
    options: ExportOptions & { viewName?: string; members?: Member[] }
  ): Promise<ExportResult> {
    try {
      if (!options.viewName || !options.members) {
        throw new Error('Google Contacts export requires viewName and members data');
      }

      // Check if user is authenticated with Google
      if (!googleMailService.isAuthenticated()) {
        throw new Error('Not authenticated with Google. Please connect your Google account first.');
      }

      // Create distribution list using the Google Mail service
      const result = await googleMailService.createDistributionListFromView(
        options.viewName,
        options.members,
        options.filename?.replace(/\.[^/.]+$/, '') // Remove file extension for group name
      );

      return {
        success: result.success,
        error: result.error,
        recordCount: result.memberCount || 0,
        googleResult: result
      };
    } catch (error) {
      console.error('Google Contacts export error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Google Contacts export failed'
      };
    }
  }

  // ============================================================================
  // PREVIEW FUNCTIONALITY
  // ============================================================================

  /**
   * Generate a preview of the export without creating the file
   */
  public generatePreview(
    viewName: string,
    members: Member[],
    sampleSize: number = 5
  ): ExportPreview {
    try {
      const view = EXPORT_VIEWS[viewName];
      if (!view) {
        throw new Error(`Export view '${viewName}' not found`);
      }

      // Apply view filter
      const filteredMembers = view.filter ? members.filter(view.filter) : members;

      let headers: string[];
      let sampleRows: string[][];

      if (view.customColumns) {
        headers = view.customColumns.map(col => col.label);
        sampleRows = filteredMembers
          .slice(0, sampleSize)
          .map(member => view.customColumns!.map(col => col.getValue(member) || ''));
      } else {
        const context = MEMBER_TABLE_CONTEXTS[view.contextName];
        if (!context) {
          throw new Error(`Table context '${view.contextName}' not found`);
        }

        const visibleColumns = context.columns
          .filter(col => col.visible)
          .sort((a, b) => a.order - b.order);

        headers = visibleColumns.map(col => {
          const field = MEMBER_FIELDS[col.fieldKey];
          return field?.label || col.fieldKey;
        });

        sampleRows = filteredMembers
          .slice(0, sampleSize)
          .map(member => 
            visibleColumns.map(col => {
              const field = MEMBER_FIELDS[col.fieldKey];
              const value = member[col.fieldKey as keyof Member];
              return field ? renderFieldValue(field, value) || '' : String(value || '');
            })
          );
      }

      // Estimate file size (rough calculation)
      const avgRowSize = sampleRows.length > 0 
        ? sampleRows.reduce((sum, row) => sum + row.join(',').length, 0) / sampleRows.length
        : 50;
      const estimatedSize = (headers.join(',').length + avgRowSize * filteredMembers.length) * 1.2; // 20% overhead
      
      return {
        headers,
        sampleRows,
        totalRecords: filteredMembers.length,
        estimatedFileSize: this.formatFileSize(estimatedSize)
      };
    } catch (error) {
      console.error('Preview generation error:', error);
      return {
        headers: [],
        sampleRows: [],
        totalRecords: 0,
        estimatedFileSize: '0 B'
      };
    }
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Generate a filename with timestamp
   */
  private generateFilename(baseName: string, format: ExportFormat): string {
    const timestamp = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    const sanitizedName = baseName.toLowerCase().replace(/[^a-z0-9]/g, '-');
    return `hdcn-${sanitizedName}-${timestamp}.${format}`;
  }

  /**
   * Escape CSV values to handle commas, quotes, and newlines
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

  /**
   * Download a text file
   */
  private downloadFile(content: string, filename: string, mimeType: string): void {
    const blob = new Blob([content], { type: mimeType });
    this.downloadBlob(blob, filename);
  }

  /**
   * Download a blob as a file
   */
  private downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Format file size in human-readable format
   */
  private formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }

  /**
   * Get available export views for a user role
   */
  public getAvailableViews(userRoles: string[]): ExportViewConfig[] {
    return Object.values(EXPORT_VIEWS).filter(view => 
      view.permissions.view.some(role => userRoles.includes(role))
    );
  }

  /**
   * Check if user can export a specific view
   */
  public canExportView(viewName: string, userRoles: string[]): boolean {
    const view = EXPORT_VIEWS[viewName];
    if (!view) return false;
    
    return view.permissions.export.some(role => userRoles.includes(role));
  }

  /**
   * Export view directly to Google Contacts
   */
  public async exportViewToGoogleContacts(
    viewName: string,
    members: Member[],
    customName?: string
  ): Promise<ExportResult> {
    return this.exportView(viewName, members, {
      format: 'google-contacts',
      filename: customName
    });
  }

  /**
   * Check if Google Contacts export is available
   */
  public isGoogleContactsAvailable(): boolean {
    return googleMailService.isAuthenticated();
  }

  /**
   * Get supported export formats for a view
   */
  public getSupportedFormats(viewName: string): ExportFormat[] {
    const view = EXPORT_VIEWS[viewName];
    if (!view) return [];

    const baseFormats: ExportFormat[] = ['csv', 'xlsx', 'pdf'];
    
    // Add TXT for email-based views
    if (viewName.includes('email') || viewName.includes('Email')) {
      baseFormats.push('txt');
    }

    // Add Google Contacts for email-based views if authenticated
    if ((viewName.includes('email') || viewName.includes('Email')) && this.isGoogleContactsAvailable()) {
      baseFormats.push('google-contacts');
    }

    return baseFormats;
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const memberExportService = MemberExportService.getInstance();
export default MemberExportService;