/**
 * React Hook for Member Export Functionality
 * 
 * This hook provides a React-friendly interface to the MemberExportService,
 * managing loading states, error handling, and export operations.
 * 
 * Features:
 * - Export members using predefined views
 * - Generate export previews
 * - Handle loading states and errors
 * - Permission checking for export operations
 * - Progress tracking for large exports
 */

import { useState, useCallback, useMemo } from 'react';
import { 
  memberExportService, 
  ExportFormat, 
  ExportOptions, 
  ExportResult, 
  ExportPreview,
  ExportViewConfig,
  EXPORT_VIEWS
} from '../services/MemberExportService';
import { Member } from '../types/index';
import { useAuth } from '../hooks/useAuth';

// ============================================================================
// HOOK TYPES
// ============================================================================

export interface ExportState {
  isExporting: boolean;
  isGeneratingPreview: boolean;
  error: string | null;
  lastExportResult: ExportResult | null;
  progress: number; // 0-100
}

export interface ExportHookReturn {
  // State
  exportState: ExportState;
  
  // Available views for current user
  availableViews: ExportViewConfig[];
  
  // Export operations
  exportView: (viewName: string, members: Member[], options?: Partial<ExportOptions>) => Promise<ExportResult>;
  exportTableContext: (contextName: string, members: Member[], options?: Partial<ExportOptions>) => Promise<ExportResult>;
  exportCustomColumns: (
    members: Member[], 
    columns: Array<{ key: string; label: string; getValue: (member: Member) => string }>,
    options?: Partial<ExportOptions>
  ) => Promise<ExportResult>;
  
  // Preview operations
  generatePreview: (viewName: string, members: Member[], sampleSize?: number) => Promise<ExportPreview>;
  
  // Permission checking
  canExportView: (viewName: string) => boolean;
  
  // Utility functions
  clearError: () => void;
  resetState: () => void;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export const useMemberExport = (): ExportHookReturn => {
  const { user } = useAuth();
  
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  const [exportState, setExportState] = useState<ExportState>({
    isExporting: false,
    isGeneratingPreview: false,
    error: null,
    lastExportResult: null,
    progress: 0
  });

  // ============================================================================
  // USER PERMISSIONS
  // ============================================================================
  
  const userRoles = useMemo(() => {
    return user?.groups || [];
  }, [user]);

  const availableViews = useMemo(() => {
    return memberExportService.getAvailableViews(userRoles);
  }, [userRoles]);

  // ============================================================================
  // ERROR HANDLING
  // ============================================================================
  
  const setError = useCallback((error: string) => {
    setExportState(prev => ({
      ...prev,
      error,
      isExporting: false,
      isGeneratingPreview: false
    }));
  }, []);

  const clearError = useCallback(() => {
    setExportState(prev => ({
      ...prev,
      error: null
    }));
  }, []);

  const resetState = useCallback(() => {
    setExportState({
      isExporting: false,
      isGeneratingPreview: false,
      error: null,
      lastExportResult: null,
      progress: 0
    });
  }, []);

  // ============================================================================
  // EXPORT OPERATIONS
  // ============================================================================
  
  /**
   * Export members using a predefined export view
   */
  const exportView = useCallback(async (
    viewName: string,
    members: Member[],
    options: Partial<ExportOptions> = {}
  ): Promise<ExportResult> => {
    try {
      // Check permissions
      if (!memberExportService.canExportView(viewName, userRoles)) {
        const error = `You don't have permission to export '${viewName}'`;
        setError(error);
        return { success: false, error };
      }

      // Validate inputs
      if (!members || members.length === 0) {
        const error = 'No members provided for export';
        setError(error);
        return { success: false, error };
      }

      // Set loading state
      setExportState(prev => ({
        ...prev,
        isExporting: true,
        error: null,
        progress: 0
      }));

      // Simulate progress for user feedback
      const progressInterval = setInterval(() => {
        setExportState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90)
        }));
      }, 100);

      try {
        // Perform export
        const result = await memberExportService.exportView(viewName, members, options);

        // Clear progress interval
        clearInterval(progressInterval);

        // Update state with result
        setExportState(prev => ({
          ...prev,
          isExporting: false,
          lastExportResult: result,
          progress: 100,
          error: result.success ? null : result.error || 'Export failed'
        }));

        return result;
      } catch (error) {
        clearInterval(progressInterval);
        throw error;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Export failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [userRoles, setError]);

  /**
   * Export members using a table context configuration
   */
  const exportTableContext = useCallback(async (
    contextName: string,
    members: Member[],
    options: Partial<ExportOptions> = {}
  ): Promise<ExportResult> => {
    try {
      // Validate inputs
      if (!members || members.length === 0) {
        const error = 'No members provided for export';
        setError(error);
        return { success: false, error };
      }

      // Set loading state
      setExportState(prev => ({
        ...prev,
        isExporting: true,
        error: null,
        progress: 0
      }));

      // Simulate progress
      const progressInterval = setInterval(() => {
        setExportState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90)
        }));
      }, 100);

      try {
        // Perform export
        const result = await memberExportService.exportTableContext(contextName, members, options);

        // Clear progress interval
        clearInterval(progressInterval);

        // Update state with result
        setExportState(prev => ({
          ...prev,
          isExporting: false,
          lastExportResult: result,
          progress: 100,
          error: result.success ? null : result.error || 'Export failed'
        }));

        return result;
      } catch (error) {
        clearInterval(progressInterval);
        throw error;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Export failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [setError]);

  /**
   * Export members using custom column definitions
   */
  const exportCustomColumns = useCallback(async (
    members: Member[],
    columns: Array<{ key: string; label: string; getValue: (member: Member) => string }>,
    options: Partial<ExportOptions> = {}
  ): Promise<ExportResult> => {
    try {
      // Validate inputs
      if (!members || members.length === 0) {
        const error = 'No members provided for export';
        setError(error);
        return { success: false, error };
      }

      if (!columns || columns.length === 0) {
        const error = 'No columns defined for export';
        setError(error);
        return { success: false, error };
      }

      // Set loading state
      setExportState(prev => ({
        ...prev,
        isExporting: true,
        error: null,
        progress: 0
      }));

      // Simulate progress
      const progressInterval = setInterval(() => {
        setExportState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90)
        }));
      }, 100);

      try {
        // Perform export
        const result = await memberExportService.exportCustomColumns(members, columns, options);

        // Clear progress interval
        clearInterval(progressInterval);

        // Update state with result
        setExportState(prev => ({
          ...prev,
          isExporting: false,
          lastExportResult: result,
          progress: 100,
          error: result.success ? null : result.error || 'Export failed'
        }));

        return result;
      } catch (error) {
        clearInterval(progressInterval);
        throw error;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Export failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [setError]);

  // ============================================================================
  // PREVIEW OPERATIONS
  // ============================================================================
  
  /**
   * Generate a preview of the export without creating the file
   */
  const generatePreview = useCallback(async (
    viewName: string,
    members: Member[],
    sampleSize: number = 5
  ): Promise<ExportPreview> => {
    try {
      // Check if view exists
      if (!EXPORT_VIEWS[viewName]) {
        const error = `Export view '${viewName}' not found`;
        setError(error);
        return {
          headers: [],
          sampleRows: [],
          totalRecords: 0,
          estimatedFileSize: '0 B'
        };
      }

      // Validate inputs
      if (!members || members.length === 0) {
        return {
          headers: [],
          sampleRows: [],
          totalRecords: 0,
          estimatedFileSize: '0 B'
        };
      }

      // Set loading state
      setExportState(prev => ({
        ...prev,
        isGeneratingPreview: true,
        error: null
      }));

      // Generate preview
      const preview = memberExportService.generatePreview(viewName, members, sampleSize);

      // Update state
      setExportState(prev => ({
        ...prev,
        isGeneratingPreview: false
      }));

      return preview;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Preview generation failed';
      setError(errorMessage);
      return {
        headers: [],
        sampleRows: [],
        totalRecords: 0,
        estimatedFileSize: '0 B'
      };
    }
  }, [setError]);

  // ============================================================================
  // PERMISSION CHECKING
  // ============================================================================
  
  /**
   * Check if user can export a specific view
   */
  const canExportView = useCallback((viewName: string): boolean => {
    return memberExportService.canExportView(viewName, userRoles);
  }, [userRoles]);

  // ============================================================================
  // RETURN HOOK INTERFACE
  // ============================================================================
  
  return {
    // State
    exportState,
    
    // Available views for current user
    availableViews,
    
    // Export operations
    exportView,
    exportTableContext,
    exportCustomColumns,
    
    // Preview operations
    generatePreview,
    
    // Permission checking
    canExportView,
    
    // Utility functions
    clearError,
    resetState
  };
};

export default useMemberExport;