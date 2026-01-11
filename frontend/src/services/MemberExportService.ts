/**
 * Member Export Service
 * 
 * Simple service to export member data as JSON.
 * Much simpler than parquet files - just standard API calls!
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

// Simple export view configuration for compatibility with GoogleMailService
export interface ExportViewConfig {
  name: string;
  description: string;
  filter?: (member: Member) => boolean;
  permissions?: {
    view: string[];
    export: string[];
  };
  regionalRestricted?: boolean;
}

// Export format types for compatibility
export type ExportFormat = 'csv' | 'excel' | 'json' | 'pdf';

// Export options for compatibility
export interface ExportOptions {
  format: ExportFormat;
  filename?: string;
  includeHeaders?: boolean;
  delimiter?: string;
}

// Basic export views for compatibility
export const EXPORT_VIEWS: Record<string, ExportViewConfig> = {
  emailGroupsDigital: {
    name: 'Digital Email Groups',
    description: 'Members who prefer digital communication',
    filter: (member: Member) => member.status === 'active' && !!member.email,
    permissions: {
      view: ['Members_Read', 'Members_CRUD', 'Communication_Read'],
      export: ['Members_Read', 'Members_CRUD', 'Communication_CRUD']
    },
    regionalRestricted: true
  },
  addressStickersPaper: {
    name: 'Paper Address Labels',
    description: 'Members who receive paper communications',
    filter: (member: Member) => member.status === 'active',
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_Read', 'Members_CRUD']
    },
    regionalRestricted: true
  },
  addressStickersRegional: {
    name: 'Regional Address Labels',
    description: 'Regional member communications',
    filter: (member: Member) => member.status === 'active',
    permissions: {
      view: ['Members_Read', 'Members_CRUD'],
      export: ['Members_Read', 'Members_CRUD']
    },
    regionalRestricted: true
  }
};

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

export class MemberExportService {
  /**
   * Export all members that the current user has access to
   * 
   * This is much simpler than parquet files:
   * - Standard JSON API response
   * - No binary data handling
   * - No CORS issues
   * - No web workers needed
   * - Regional filtering handled by backend
   * - Calculated fields included
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
      // Try to make a request to see if we have permission
      // The backend will return 403 if no permission
      const response = await ApiService.get('/members/export');
      
      return {
        hasPermission: response.success
      };
    } catch (error) {
      return {
        hasPermission: false,
        error: error instanceof Error ? error.message : 'Permission check failed'
      };
    }
  }

  /**
   * Simple CSV export for compatibility with old address label system
   */
  static async exportCustomColumns(
    members: any[],
    columns: Array<{ key: string; label: string; getValue: (member: any) => string }>,
    options?: { format?: string; filename?: string }
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const format = options?.format || 'csv';
      const filename = options?.filename || `export_${new Date().toISOString().split('T')[0]}.${format}`;
      
      // Create CSV content
      const headers = columns.map(col => col.label).join(',');
      const rows = members.map(member => 
        columns.map(col => `"${col.getValue(member).replace(/"/g, '""')}"`).join(',')
      );
      const csvContent = [headers, ...rows].join('\n');

      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }
}

export default MemberExportService;