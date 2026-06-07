/**
 * Member Export Service
 * 
 * Service for exporting member data in various formats (CSV, XLSX, PDF, TXT).
 * Supports predefined export views, table context exports, custom columns,
 * and Google Contacts integration via GoogleMailService.
 */

import { ApiService } from './apiService';
import { Member } from '../types/index';

export interface MemberExportResponse {
  success: boolean;
  data: Member[];
  metadata: {
    total_count: number;
    export_date: string;
    user_email: string;
    applied_filters: {
      regional: boolean;
    };
  };
}

export interface MemberExportError {
  success: false;
  error: string;
}

// Export view configuration
export interface ExportViewConfig {
  name: string;
  description: string;
  defaultFormat: string;
  filter?: (member: Member) => boolean;
  columns?: Array<{ key: string; label: string; getValue?: (member: Member) => string }>;
  permissions: {
    view: string[];
    export: string[];
  };
  regionalRestricted?: boolean;
}

// Export format types
export type ExportFormat = 'csv' | 'xlsx' | 'pdf' | 'txt' | 'excel' | 'json' | 'google-contacts';

// Export options
export interface ExportOptions {
  format?: string;
  filename?: string;
  includeHeaders?: boolean;
  delimiter?: string;
}

// Export result
export interface ExportResult {
  success: boolean;
  error?: string;
  filename?: string;
  recordCount?: number;
  googleResult?: {
    groupName?: string;
    memberCount?: number;
  };
}

// Export preview
export interface ExportPreview {
  headers: string[];
  sampleRows: string[][];
  totalRecords: number;
  estimatedFileSize: string;
}

// Custom column definition
export interface CustomColumn {
  key: string;
  label: string;
  getValue: (member: Member) => string;
}

// Predefined export views
export const EXPORT_VIEWS: Record<string, ExportViewConfig> = {
  emailGroupsDigital: {
    name: 'Email Groups (Digital)',
    description: 'Members who prefer digital communication',
    defaultFormat: 'csv',
    filter: (member: Member) => (member.status === 'Actief' || member.status === 'Active') && member.clubblad === 'Digitaal' && !!member.email,
    columns: [
      { key: 'korte_naam', label: 'Name' },
      { key: 'email', label: 'Email' }
    ],
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'Communication_Read'],
      export: ['Members_CRUD', 'Communication_CRUD']
    },
    regionalRestricted: true
  },
  emailGroupsRegional: {
    name: 'Regional Email Groups',
    description: 'Members in specific regions for email communication',
    defaultFormat: 'csv',
    filter: (member: Member) => (member.status === 'Actief' || member.status === 'Active') && !!member.email,
    columns: [
      { key: 'korte_naam', label: 'Name' },
      { key: 'email', label: 'Email' },
      { key: 'regio', label: 'Region' }
    ],
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'Communication_Read'],
      export: ['Members_CRUD', 'Communication_CRUD']
    },
    regionalRestricted: true
  },
  addressStickersPaper: {
    name: 'Paper Address Labels',
    description: 'Members who receive paper communications',
    defaultFormat: 'pdf',
    filter: (member: Member) => (member.status === 'Actief' || member.status === 'Active') && member.clubblad === 'Papier',
    columns: [
      { key: 'korte_naam', label: 'Name' },
      { key: 'straat', label: 'Street' },
      { key: 'postcode', label: 'Postcode' },
      { key: 'woonplaats', label: 'City' }
    ],
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_CRUD']
    },
    regionalRestricted: true
  },
  addressStickersRegional: {
    name: 'Regional Address Labels',
    description: 'Regional member communications',
    defaultFormat: 'pdf',
    filter: (member: Member) => (member.status === 'Actief' || member.status === 'Active'),
    columns: [
      { key: 'korte_naam', label: 'Name' },
      { key: 'straat', label: 'Street' },
      { key: 'postcode', label: 'Postcode' },
      { key: 'woonplaats', label: 'City' },
      { key: 'regio', label: 'Region' }
    ],
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_CRUD']
    },
    regionalRestricted: true
  },
  birthdayList: {
    name: 'Birthday List',
    description: 'Active members for birthday communications',
    defaultFormat: 'csv',
    filter: (member: Member) => (member.status === 'Actief' || member.status === 'Active'),
    columns: [
      { key: 'korte_naam', label: 'Name' },
      { key: 'email', label: 'Email' },
      { key: 'telefoon', label: 'Phone' },
      { key: 'verjaardag', label: 'Birthday' }
    ],
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_CRUD']
    },
    regionalRestricted: false
  }
};

export class MemberExportService {
  private static instance: MemberExportService;

  private constructor() {}

  /**
   * Get singleton instance
   */
  static getInstance(): MemberExportService {
    if (!MemberExportService.instance) {
      MemberExportService.instance = new MemberExportService();
    }
    return MemberExportService.instance;
  }

  /**
   * Export all members that the current user has access to via API
   */
  static async exportMembers(): Promise<MemberExportResponse | MemberExportError> {
    try {
      console.log('[MemberExportService] Exporting member data');
      
      const response = await ApiService.get<MemberExportResponse>('/members/export');
      
      if (!response.success) {
        return {
          success: false,
          error: response.error || 'Export failed'
        };
      }

      const exportData = response.data;
      if (!exportData || !exportData.data) {
        return {
          success: false,
          error: 'No export data received'
        };
      }

      console.log(`[MemberExportService] Successfully exported ${exportData.data.length} members`);
      return exportData;
    } catch (error) {
      console.error('[MemberExportService] Export error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  /**
   * Check if the current user has permission to export members
   */
  static async checkExportPermission(): Promise<{ hasPermission: boolean; error?: string }> {
    try {
      const response = await ApiService.get('/members/export');
      return { hasPermission: response.success };
    } catch (error) {
      return {
        hasPermission: false,
        error: error instanceof Error ? error.message : 'Permission check failed'
      };
    }
  }

  /**
   * Simple CSV export — static convenience method for components
   */
  static async exportCustomColumns(
    members: any[],
    columns: Array<{ key: string; label: string; getValue: (member: any) => string }>,
    options?: { format?: string; filename?: string }
  ): Promise<{ success: boolean; error?: string }> {
    const instance = MemberExportService.getInstance();
    return instance.exportCustomColumns(
      members,
      columns.map(col => ({ key: col.key, label: col.label, getValue: col.getValue })),
      options
    );
  }

  /**
   * Export a predefined view to a file
   */
  async exportView(viewName: string, members: Member[] | null, options?: ExportOptions): Promise<ExportResult> {
    try {
      if (!members) {
        return { success: false, error: 'No members data provided' };
      }

      const view = EXPORT_VIEWS[viewName];
      if (!view) {
        return { success: false, error: `Export view '${viewName}' not found` };
      }

      // Handle google-contacts format
      if (options?.format === 'google-contacts') {
        return this.exportViewToGoogleContacts(viewName, members);
      }

      const filteredMembers = view.filter ? members.filter(view.filter) : members;
      const format = options?.format || view.defaultFormat;
      const filename = options?.filename || this.generateFilename(view.name, format);
      const columns = view.columns || [];

      // Generate export data
      const headers = columns.map(col => col.label);
      const rows = filteredMembers.map(member =>
        columns.map(col => col.getValue ? col.getValue(member) : String((member as any)[col.key] || ''))
      );

      this.downloadFile(headers, rows, format, filename);

      return {
        success: true,
        filename,
        recordCount: filteredMembers.length
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  /**
   * Export using a table context configuration
   */
  async exportTableContext(contextName: string, members: Member[], options?: ExportOptions): Promise<ExportResult> {
    try {
      // Dynamic import of memberFields config
      const { MEMBER_TABLE_CONTEXTS, MEMBER_FIELDS } = await import('../config/memberFields');
      
      const context = (MEMBER_TABLE_CONTEXTS as any)?.[contextName];
      if (!context) {
        return { success: false, error: `Table context '${contextName}' not found` };
      }

      const columns = context.columns
        .filter((col: any) => col.visible)
        .sort((a: any, b: any) => a.order - b.order);

      const headers = columns.map((col: any) => {
        const field = (MEMBER_FIELDS as any)?.[col.fieldKey];
        return field?.label || col.fieldKey;
      });

      const rows = members.map((member: Member) =>
        columns.map((col: any) => String((member as any)[col.fieldKey] || ''))
      );

      const format = options?.format || 'csv';
      const filename = options?.filename || this.generateFilename(context.name || contextName, format);

      this.downloadFile(headers, rows, format, filename);

      return {
        success: true,
        filename,
        recordCount: members.length
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  /**
   * Export using custom column definitions
   */
  async exportCustomColumns(members: Member[], columns: CustomColumn[], options?: ExportOptions): Promise<ExportResult> {
    try {
      if (!columns || columns.length === 0) {
        return { success: false, error: 'No columns specified' };
      }

      const headers = columns.map(col => col.label);
      const rows = members.map(member =>
        columns.map(col => col.getValue(member))
      );

      const format = options?.format || 'csv';
      const filename = options?.filename || this.generateFilename('custom-export', format);

      this.downloadFile(headers, rows, format, filename);

      return {
        success: true,
        filename,
        recordCount: members.length
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }

  /**
   * Export view to Google Contacts via GoogleMailService
   */
  async exportViewToGoogleContacts(
    viewName: string,
    members: Member[],
    customName?: string
  ): Promise<ExportResult> {
    try {
      // Lazy import to avoid circular dependency
      const { GoogleMailService } = await import('./GoogleMailService');
      const googleService = GoogleMailService.getInstance();

      if (!googleService.isAuthenticated()) {
        return { success: false, error: 'Not authenticated with Google' };
      }

      const result = await googleService.createDistributionListFromView(
        viewName,
        members,
        customName
      );

      return {
        success: result.success,
        error: result.error,
        googleResult: result.success ? {
          groupName: customName || result.groupName,
          memberCount: result.memberCount
        } : undefined
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Google Contacts export failed'
      };
    }
  }

  /**
   * Get supported export formats for a view
   */
  getSupportedFormats(viewName: string): string[] {
    const baseFormats = ['csv', 'xlsx', 'pdf', 'txt'];
    
    // Only email views support google-contacts, and only when authenticated
    const emailViews = ['emailGroupsDigital', 'emailGroupsRegional'];
    if (emailViews.includes(viewName) && this.isGoogleContactsAvailable()) {
      return [...baseFormats, 'google-contacts'];
    }

    return baseFormats;
  }

  /**
   * Check if Google Contacts export is available
   */
  isGoogleContactsAvailable(): boolean {
    try {
      // Check if google token exists in localStorage
      const token = localStorage.getItem('google_access_token');
      const expiresAt = localStorage.getItem('google_expires_at');
      
      if (!token || !expiresAt) return false;
      return Date.now() < parseInt(expiresAt, 10);
    } catch {
      return false;
    }
  }

  /**
   * Check if a user can export a given view
   */
  canExportView(viewName: string, userRoles: string[]): boolean {
    const view = EXPORT_VIEWS[viewName];
    if (!view) return false;
    return view.permissions.export.some(role => userRoles.includes(role));
  }

  /**
   * Get available views for a user's roles
   */
  getAvailableViews(userRoles: string[]): ExportViewConfig[] {
    return Object.values(EXPORT_VIEWS).filter(view =>
      view.permissions.view.some(role => userRoles.includes(role))
    );
  }

  /**
   * Generate a preview of the export data
   */
  generatePreview(viewName: string, members: Member[], limit: number = 5): ExportPreview {
    const view = EXPORT_VIEWS[viewName];
    if (!view) {
      return { headers: [], sampleRows: [], totalRecords: 0, estimatedFileSize: '0 B' };
    }

    const filteredMembers = view.filter ? members.filter(view.filter) : members;
    const columns = view.columns || [];
    const headers = columns.map(col => col.label);

    const sampleRows = filteredMembers.slice(0, limit).map(member =>
      columns.map(col => col.getValue ? col.getValue(member) : String((member as any)[col.key] || ''))
    );

    // Estimate file size based on row count and average row length
    const avgRowLength = headers.join(',').length + 20; // rough estimate
    const estimatedBytes = (filteredMembers.length + 1) * avgRowLength;

    return {
      headers,
      sampleRows,
      totalRecords: filteredMembers.length,
      estimatedFileSize: this.formatFileSize(estimatedBytes)
    };
  }

  /**
   * Generate a filename for export
   */
  private generateFilename(viewName: string, format: string): string {
    const sanitized = viewName.toLowerCase().replace(/[^a-z0-9\s-]/g, '-').replace(/\s+/g, '-');
    const date = new Date().toISOString().split('T')[0];
    return `hdcn-${sanitized}-${date}.${format}`;
  }

  /**
   * Escape a CSV value
   */
  private escapeCsvValue(value: string): string {
    if (!value) return '';
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  }

  /**
   * Format file size in human-readable form
   */
  private formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const value = bytes / Math.pow(k, i);
    return `${Number.isInteger(value) ? value : value.toFixed(1)} ${units[i]}`;
  }

  /**
   * Download file to user's system
   */
  private downloadFile(headers: string[], rows: string[][], format: string, filename: string): void {
    let content: string;
    let mimeType: string;

    switch (format) {
      case 'csv':
        content = [
          headers.map(h => this.escapeCsvValue(h)).join(','),
          ...rows.map(row => row.map(cell => this.escapeCsvValue(cell)).join(','))
        ].join('\n');
        mimeType = 'text/csv;charset=utf-8;';
        break;
      case 'txt':
        content = [
          headers.join('\t'),
          ...rows.map(row => row.join('\t'))
        ].join('\n');
        mimeType = 'text/plain;charset=utf-8;';
        break;
      case 'xlsx':
        // For xlsx, we rely on the xlsx library if available
        try {
          const XLSX = require('xlsx');
          const wb = XLSX.utils.book_new();
          const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
          XLSX.utils.book_append_sheet(wb, ws, 'Export');
          const buffer = XLSX.write(wb, { type: 'array', bookType: 'xlsx' });
          const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
          this.triggerDownload(blob, filename);
          return;
        } catch {
          // Fallback to CSV if xlsx not available
          content = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
          mimeType = 'text/csv;charset=utf-8;';
        }
        break;
      case 'pdf':
        // For PDF, we rely on jspdf library if available
        try {
          const jsPDF = require('jspdf');
          require('jspdf-autotable');
          const doc = new jsPDF();
          doc.autoTable({ head: [headers], body: rows });
          doc.save(filename);
          return;
        } catch {
          // Fallback to CSV if jspdf not available
          content = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
          mimeType = 'text/csv;charset=utf-8;';
        }
        break;
      default:
        content = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
        mimeType = 'text/csv;charset=utf-8;';
    }

    const blob = new Blob([content], { type: mimeType });
    this.triggerDownload(blob, filename);
  }

  /**
   * Trigger browser file download
   */
  private triggerDownload(blob: Blob, filename: string): void {
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

export default MemberExportService;
