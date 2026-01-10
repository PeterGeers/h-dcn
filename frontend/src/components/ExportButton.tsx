/**
 * Export Button Component
 * 
 * A reusable button component for exporting member data in various formats.
 * Integrates with the MemberExportService and provides a clean UI for exports.
 * 
 * Features:
 * - Multiple export formats (CSV, XLSX, PDF, TXT)
 * - Loading states and progress indication
 * - Error handling and user feedback
 * - Permission-based visibility
 * - Customizable appearance and behavior
 */

import React, { useState } from 'react';
import {
  Button,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  Icon,
  HStack,
  Text,
  Progress,
  Alert,
  AlertIcon,
  AlertDescription,
  Box,
  Tooltip,
  useToast
} from '@chakra-ui/react';
import { 
  DownloadIcon, 
  ChevronDownIcon,
  CheckIcon,
  WarningIcon
} from '@chakra-ui/icons';
import { Member } from '../types/index';
import { useMemberExport } from '../hooks/useMemberExport';
import { ExportFormat, ExportOptions } from '../services/MemberExportService';

// ============================================================================
// COMPONENT TYPES
// ============================================================================

export interface ExportButtonProps {
  // Data to export
  members: Member[];
  
  // Export configuration
  viewName?: string; // Predefined export view
  contextName?: string; // Table context to use
  customColumns?: Array<{
    key: string;
    label: string;
    getValue: (member: Member) => string;
  }>;
  
  // UI customization
  variant?: 'solid' | 'outline' | 'ghost';
  colorScheme?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  isDisabled?: boolean;
  
  // Export options
  defaultFormat?: ExportFormat;
  availableFormats?: ExportFormat[];
  filename?: string;
  
  // Behavior
  showProgress?: boolean;
  showFormatMenu?: boolean;
  autoDownload?: boolean;
  
  // Callbacks
  onExportStart?: () => void;
  onExportComplete?: (result: any) => void;
  onExportError?: (error: string) => void;
  
  // Labels
  buttonText?: string;
  tooltipText?: string;
}

// ============================================================================
// FORMAT CONFIGURATION
// ============================================================================

const FORMAT_CONFIG = {
  csv: {
    label: 'CSV',
    description: 'Comma-separated values',
    icon: '📄',
    mimeType: 'text/csv'
  },
  xlsx: {
    label: 'Excel',
    description: 'Microsoft Excel format',
    icon: '📊',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  },
  pdf: {
    label: 'PDF',
    description: 'Portable Document Format',
    icon: '📋',
    mimeType: 'application/pdf'
  },
  txt: {
    label: 'Text',
    description: 'Plain text format',
    icon: '📝',
    mimeType: 'text/plain'
  }
};

// ============================================================================
// EXPORT BUTTON COMPONENT
// ============================================================================

export const ExportButton: React.FC<ExportButtonProps> = ({
  members,
  viewName,
  contextName,
  customColumns,
  variant = 'outline',
  colorScheme = 'green',
  size = 'sm',
  isDisabled = false,
  defaultFormat = 'csv',
  availableFormats = ['csv', 'xlsx', 'pdf'],
  filename,
  showProgress = true,
  showFormatMenu = true,
  autoDownload = true,
  onExportStart,
  onExportComplete,
  onExportError,
  buttonText = 'Export',
  tooltipText = 'Export member data'
}) => {
  const toast = useToast();
  const {
    exportState,
    exportView,
    exportTableContext,
    exportCustomColumns,
    canExportView
  } = useMemberExport();

  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>(defaultFormat);

  // ============================================================================
  // PERMISSION CHECKING
  // ============================================================================

  const hasExportPermission = React.useMemo(() => {
    if (viewName) {
      return canExportView(viewName);
    }
    // For table context or custom columns, assume permission if user can see the component
    return true;
  }, [viewName, canExportView]);

  // ============================================================================
  // EXPORT HANDLERS
  // ============================================================================

  const handleExport = async (format: ExportFormat) => {
    try {
      // Validate data
      if (!members || members.length === 0) {
        toast({
          title: 'No Data',
          description: 'No members available to export',
          status: 'warning',
          duration: 3000,
          isClosable: true
        });
        return;
      }

      // Call onExportStart callback
      onExportStart?.();

      // Prepare export options
      const exportOptions: Partial<ExportOptions> = {
        format,
        filename,
        includeHeaders: true,
        includeTimestamp: true
      };

      let result;

      // Perform export based on configuration
      if (viewName) {
        result = await exportView(viewName, members, exportOptions);
      } else if (contextName) {
        result = await exportTableContext(contextName, members, exportOptions);
      } else if (customColumns) {
        result = await exportCustomColumns(members, customColumns, exportOptions);
      } else {
        throw new Error('No export configuration provided');
      }

      // Handle result
      if (result.success) {
        toast({
          title: 'Export Successful',
          description: `Exported ${result.recordCount} members to ${result.filename}`,
          status: 'success',
          duration: 5000,
          isClosable: true
        });
        onExportComplete?.(result);
      } else {
        throw new Error(result.error || 'Export failed');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Export failed';
      
      toast({
        title: 'Export Failed',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true
      });
      
      onExportError?.(errorMessage);
    }
  };

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  const renderSingleFormatButton = () => (
    <Tooltip label={tooltipText} hasArrow>
      <Button
        leftIcon={<DownloadIcon />}
        variant={variant}
        colorScheme={colorScheme}
        size={size}
        isDisabled={isDisabled || !hasExportPermission || exportState.isExporting}
        isLoading={exportState.isExporting}
        loadingText="Exporting..."
        onClick={() => handleExport(selectedFormat)}
      >
        {buttonText} {FORMAT_CONFIG[selectedFormat].label}
      </Button>
    </Tooltip>
  );

  const renderFormatMenu = () => (
    <Menu>
      <Tooltip label={tooltipText} hasArrow>
        <MenuButton
          as={Button}
          leftIcon={<DownloadIcon />}
          rightIcon={<ChevronDownIcon />}
          variant={variant}
          colorScheme={colorScheme}
          size={size}
          isDisabled={isDisabled || !hasExportPermission || exportState.isExporting}
          isLoading={exportState.isExporting}
          loadingText="Exporting..."
        >
          {buttonText}
        </MenuButton>
      </Tooltip>
      
      <MenuList>
        {availableFormats.map((format) => (
          <MenuItem
            key={format}
            icon={<Text fontSize="sm">{FORMAT_CONFIG[format].icon}</Text>}
            onClick={() => handleExport(format)}
          >
            <Box>
              <Text fontWeight="medium">{FORMAT_CONFIG[format].label}</Text>
              <Text fontSize="xs" color="gray.500">
                {FORMAT_CONFIG[format].description}
              </Text>
            </Box>
          </MenuItem>
        ))}
        
        {members && members.length > 0 && (
          <>
            <MenuDivider />
            <MenuItem isDisabled>
              <Text fontSize="xs" color="gray.500">
                {members.length} members available
              </Text>
            </MenuItem>
          </>
        )}
      </MenuList>
    </Menu>
  );

  // ============================================================================
  // MAIN RENDER
  // ============================================================================

  // Don't render if user doesn't have permission
  if (!hasExportPermission) {
    return null;
  }

  return (
    <Box>
      {/* Export Button */}
      {showFormatMenu && availableFormats.length > 1 
        ? renderFormatMenu() 
        : renderSingleFormatButton()
      }
      
      {/* Progress Indicator */}
      {showProgress && exportState.isExporting && (
        <Box mt={2} width="200px">
          <Progress
            value={exportState.progress}
            size="sm"
            colorScheme={colorScheme}
            hasStripe
            isAnimated
          />
          <Text fontSize="xs" color="gray.500" mt={1}>
            Exporting... {exportState.progress}%
          </Text>
        </Box>
      )}
      
      {/* Error Display */}
      {exportState.error && (
        <Alert status="error" size="sm" mt={2} borderRadius="md">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            {exportState.error}
          </AlertDescription>
        </Alert>
      )}
      
      {/* Success Indicator */}
      {exportState.lastExportResult?.success && !exportState.isExporting && (
        <HStack mt={2} spacing={2}>
          <Icon as={CheckIcon} color="green.500" />
          <Text fontSize="sm" color="green.600">
            Export completed successfully
          </Text>
        </HStack>
      )}
    </Box>
  );
};

export default ExportButton;