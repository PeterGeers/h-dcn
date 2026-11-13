import React from 'react';
import { Button } from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';

interface CSVExportButtonProps {
  data: any[];
  filename: string;
  columns?: string[];
  disabled?: boolean;
  title?: string;
  /** Append the current date (YYYY-MM-DD) to the filename. Defaults to true. */
  includeDate?: boolean;
  /** Button label. Defaults to "Export CSV". */
  label?: string;
}

function CSVExportButton({
  data,
  filename,
  columns,
  disabled = false,
  title,
  includeDate = true,
  label = 'Export CSV',
}: CSVExportButtonProps) {
  const exportToCSV = () => {
    if (!data || data.length === 0) return;

    const headers = columns || Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row => 
        headers.map(header => {
          const value = row[header] || '';
          return `"${String(value).replace(/"/g, '""')}"`;
        }).join(',')
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    const downloadName = includeDate
      ? `${filename}_${new Date().toISOString().split('T')[0]}.csv`
      : `${filename}.csv`;
    link.setAttribute('download', downloadName);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Button
      leftIcon={<DownloadIcon />}
      colorScheme="green"
      variant="outline"
      onClick={exportToCSV}
      size="sm"
      isDisabled={disabled}
      title={title}
    >
      {label}
    </Button>
  );
}

export default CSVExportButton;