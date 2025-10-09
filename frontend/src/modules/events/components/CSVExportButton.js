import React from 'react';
import { Button } from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';

function CSVExportButton({ data, filename, columns }) {
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
    link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
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
    >
      Export CSV
    </Button>
  );
}

export default CSVExportButton;