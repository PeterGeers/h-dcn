/**
 * Address Label Generator Component for H-DCN Reporting
 * 
 * This component provides address label generation functionality with multiple
 * layout options for printing on standard label sheets. Supports various
 * label formats commonly used for mailings and distribution.
 */

import React, { useState, useRef } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Select,
  FormControl,
  FormLabel,
  Checkbox,
  Alert,
  AlertIcon,
  useToast,
  Grid,
  GridItem,
  Divider,
  Badge,
  Spinner
} from '@chakra-ui/react';
import { DownloadIcon, ViewIcon, EditIcon } from '@chakra-ui/icons';
import { Member } from '../../types/index';
import { memberExportService } from '../../services/MemberExportService';
import { 
  addressLabelService, 
  STANDARD_LABEL_FORMATS, 
  DEFAULT_LABEL_STYLE,
  LabelFormat,
  LabelStyle,
  AddressLabelOptions 
} from '../../services/AddressLabelService';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

// Import types from service
export type { LabelFormat, LabelStyle, AddressLabelOptions } from '../../services/AddressLabelService';

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface AddressLabelGeneratorProps {
  members: Member[];
  viewName?: string;
  onClose?: () => void;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AddressLabelGenerator: React.FC<AddressLabelGeneratorProps> = ({
  members,
  viewName = 'addressStickersRegional',
  onClose
}) => {
  const [selectedFormat, setSelectedFormat] = useState<LabelFormat>(STANDARD_LABEL_FORMATS[0]);
  const [labelStyle, setLabelStyle] = useState<LabelStyle>(DEFAULT_LABEL_STYLE);
  const [includeCountry, setIncludeCountry] = useState(false);
  const [countryFilter, setCountryFilter] = useState('all');
  const [sortBy, setSortBy] = useState<'name' | 'postcode' | 'region'>('name');
  const [startPosition, setStartPosition] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  
  const previewRef = useRef<HTMLDivElement>(null);
  const toast = useToast();

  // Filter and sort members using service
  const processedMembers = React.useMemo(() => {
    return addressLabelService.processMembers(members, {
      countryFilter,
      sortBy,
      includeCountry
    });
  }, [members, countryFilter, sortBy, includeCountry]);

  // Get unique countries for filter using service
  const availableCountries = React.useMemo(() => {
    return addressLabelService.getAvailableCountries(members);
  }, [members]);

  // Format address for label using service
  const formatAddress = (member: Member): string[] => {
    return addressLabelService.formatAddress(member, includeCountry);
  };

  // Generate PDF labels using service
  const generatePDF = async () => {
    setIsGenerating(true);
    
    try {
      const options: AddressLabelOptions = {
        format: selectedFormat,
        style: labelStyle,
        includeCountry,
        countryFilter,
        sortBy,
        startPosition
      };

      const result = await addressLabelService.generateLabelsPDF(members, options);
      
      if (result.success) {
        toast({
          title: '✅ Labels gegenereerd!',
          description: `${result.labelCount} adreslabels opgeslagen als ${result.filename}`,
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
      } else {
        throw new Error(result.error || 'Unknown error occurred');
      }
      
    } catch (error) {
      console.error('Error generating labels:', error);
      toast({
        title: '❌ Fout bij genereren',
        description: `Kon labels niet genereren: ${error instanceof Error ? error.message : 'Onbekende fout'}`,
        status: 'error',
        duration: 8000,
        isClosable: true,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  // Export to other formats
  const exportToFormat = async (format: 'csv' | 'xlsx') => {
    try {
      const exportData = processedMembers.map(member => ({
        'Naam': member.korte_naam || '',
        'Straat': member.straat || '',
        'Postcode': member.postcode || '',
        'Woonplaats': member.woonplaats || '',
        'Land': member.land || 'Nederland',
        'Regio': member.regio || ''
      }));

      const result = await memberExportService.exportCustomColumns(
        processedMembers,
        [
          { key: 'korte_naam', label: 'Naam', getValue: (m) => m.korte_naam || '' },
          { key: 'straat', label: 'Straat', getValue: (m) => m.straat || '' },
          { key: 'postcode', label: 'Postcode', getValue: (m) => m.postcode || '' },
          { key: 'woonplaats', label: 'Woonplaats', getValue: (m) => m.woonplaats || '' },
          { key: 'land', label: 'Land', getValue: (m) => m.land || 'Nederland' },
          { key: 'regio', label: 'Regio', getValue: (m) => m.regio || '' }
        ],
        {
          format,
          filename: `hdcn-address-labels-${new Date().toISOString().split('T')[0]}.${format}`
        }
      );

      if (result.success) {
        toast({
          title: '✅ Export voltooid!',
          description: `${processedMembers.length} adressen geëxporteerd naar ${format.toUpperCase()}`,
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error(`Error exporting to ${format}:`, error);
      toast({
        title: '❌ Export mislukt',
        description: `Kon niet exporteren naar ${format.toUpperCase()}`,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  // Toggle preview mode
  const togglePreview = () => {
    setPreviewMode(!previewMode);
  };

  // Print preview
  const printPreview = () => {
    if (previewRef.current) {
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(`
          <html>
            <head>
              <title>Address Labels Preview</title>
              <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                .label-sheet { width: 210mm; margin: 0 auto; }
                .label { 
                  display: inline-block; 
                  width: ${selectedFormat.labelWidth}mm; 
                  height: ${selectedFormat.labelHeight}mm; 
                  border: 1px solid #ccc; 
                  padding: ${labelStyle.padding}mm; 
                  margin: ${selectedFormat.gapVertical/2}mm ${selectedFormat.gapHorizontal/2}mm;
                  font-size: ${labelStyle.fontSize}pt;
                  line-height: ${labelStyle.lineHeight};
                  text-align: ${labelStyle.alignment};
                  vertical-align: top;
                  box-sizing: border-box;
                  overflow: hidden;
                }
                @media print {
                  body { margin: 0; padding: 0; }
                  .label { border: ${labelStyle.includeBorder ? '1px solid #000' : 'none'}; }
                }
              </style>
            </head>
            <body>
              ${previewRef.current.innerHTML}
            </body>
          </html>
        `);
        printWindow.document.close();
        printWindow.print();
      }
    }
  };

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading color="orange.500" size="lg">
              🏷️ Adreslabels Generator
            </Heading>
            <Text color="gray.300" fontSize="sm">
              Genereer adreslabels voor mailings en distributie
            </Text>
          </VStack>
          {onClose && (
            <Button variant="ghost" onClick={onClose}>
              Sluiten
            </Button>
          )}
        </HStack>

        {/* Configuration */}
        <Box bg="gray.800" borderRadius="lg" p={6}>
          <VStack spacing={4} align="stretch">
            <Heading size="md" color="orange.300">
              Configuratie
            </Heading>
            
            <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={4}>
              {/* Label Format */}
              <GridItem>
                <FormControl>
                  <FormLabel color="gray.300">Label Formaat</FormLabel>
                  <Select
                    value={selectedFormat.id}
                    onChange={(e) => {
                      const format = STANDARD_LABEL_FORMATS.find(f => f.id === e.target.value);
                      if (format) setSelectedFormat(format);
                    }}
                    bg="gray.700"
                    borderColor="gray.600"
                  >
                    {STANDARD_LABEL_FORMATS.map(format => (
                      <option key={format.id} value={format.id}>
                        {format.name}
                      </option>
                    ))}
                  </Select>
                  <Text fontSize="xs" color="gray.400" mt={1}>
                    {selectedFormat.description}
                  </Text>
                </FormControl>
              </GridItem>

              {/* Sort Order */}
              <GridItem>
                <FormControl>
                  <FormLabel color="gray.300">Sortering</FormLabel>
                  <Select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as 'name' | 'postcode' | 'region')}
                    bg="gray.700"
                    borderColor="gray.600"
                  >
                    <option value="name">Op naam</option>
                    <option value="postcode">Op postcode</option>
                    <option value="region">Op regio</option>
                  </Select>
                </FormControl>
              </GridItem>

              {/* Country Filter */}
              <GridItem>
                <FormControl>
                  <FormLabel color="gray.300">Land Filter</FormLabel>
                  <Select
                    value={countryFilter}
                    onChange={(e) => setCountryFilter(e.target.value)}
                    bg="gray.700"
                    borderColor="gray.600"
                  >
                    <option value="all">Alle landen</option>
                    {availableCountries.map(country => (
                      <option key={country} value={country}>
                        {country}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              </GridItem>

              {/* Start Position */}
              <GridItem>
                <FormControl>
                  <FormLabel color="gray.300">Start Positie</FormLabel>
                  <Select
                    value={startPosition}
                    onChange={(e) => setStartPosition(parseInt(e.target.value))}
                    bg="gray.700"
                    borderColor="gray.600"
                  >
                    <option value={0}>Begin van vel</option>
                    {Array.from({ length: selectedFormat.columns * selectedFormat.rows - 1 }, (_, i) => (
                      <option key={i + 1} value={i + 1}>
                        Overslaan eerste {i + 1} label{i > 0 ? 's' : ''}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              </GridItem>
            </Grid>

            {/* Style Options */}
            <Divider borderColor="gray.600" />
            
            <Grid templateColumns="repeat(auto-fit, minmax(200px, 1fr))" gap={4}>
              <GridItem>
                <FormControl>
                  <FormLabel color="gray.300">Lettergrootte</FormLabel>
                  <Select
                    value={labelStyle.fontSize}
                    onChange={(e) => setLabelStyle({
                      ...labelStyle,
                      fontSize: parseInt(e.target.value)
                    })}
                    bg="gray.700"
                    borderColor="gray.600"
                  >
                    <option value={8}>8pt (Klein)</option>
                    <option value={9}>9pt</option>
                    <option value={10}>10pt (Standaard)</option>
                    <option value={11}>11pt</option>
                    <option value={12}>12pt (Groot)</option>
                  </Select>
                </FormControl>
              </GridItem>

              <GridItem>
                <FormControl>
                  <FormLabel color="gray.300">Uitlijning</FormLabel>
                  <Select
                    value={labelStyle.alignment}
                    onChange={(e) => setLabelStyle({
                      ...labelStyle,
                      alignment: e.target.value as 'left' | 'center' | 'right'
                    })}
                    bg="gray.700"
                    borderColor="gray.600"
                  >
                    <option value="left">Links</option>
                    <option value="center">Midden</option>
                    <option value="right">Rechts</option>
                  </Select>
                </FormControl>
              </GridItem>

              <GridItem>
                <VStack align="start" spacing={2}>
                  <Checkbox
                    isChecked={includeCountry}
                    onChange={(e) => setIncludeCountry(e.target.checked)}
                    colorScheme="orange"
                  >
                    <Text color="gray.300">Land vermelden</Text>
                  </Checkbox>
                  <Checkbox
                    isChecked={labelStyle.includeBorder}
                    onChange={(e) => setLabelStyle({
                      ...labelStyle,
                      includeBorder: e.target.checked
                    })}
                    colorScheme="orange"
                  >
                    <Text color="gray.300">Rand tonen</Text>
                  </Checkbox>
                </VStack>
              </GridItem>
            </Grid>
          </VStack>
        </Box>

        {/* Statistics */}
        <Box bg="gray.800" borderRadius="lg" p={4}>
          <HStack justify="space-between" wrap="wrap" spacing={4}>
            <HStack spacing={4}>
              <Badge colorScheme="blue" fontSize="sm" p={2}>
                {processedMembers.length} labels
              </Badge>
              <Badge colorScheme="green" fontSize="sm" p={2}>
                {Math.ceil(processedMembers.length / (selectedFormat.columns * selectedFormat.rows))} pagina's
              </Badge>
              <Badge colorScheme="purple" fontSize="sm" p={2}>
                {selectedFormat.name}
              </Badge>
            </HStack>
          </HStack>
        </Box>

        {/* Actions */}
        <HStack spacing={4} wrap="wrap">
          <Button
            leftIcon={<DownloadIcon />}
            colorScheme="orange"
            onClick={generatePDF}
            isLoading={isGenerating}
            loadingText="Genereren..."
          >
            PDF Genereren
          </Button>
          
          <Button
            leftIcon={<ViewIcon />}
            variant="outline"
            colorScheme="blue"
            onClick={togglePreview}
          >
            {previewMode ? 'Verberg Preview' : 'Toon Preview'}
          </Button>
          
          <Button
            leftIcon={<EditIcon />}
            variant="outline"
            colorScheme="green"
            onClick={printPreview}
            isDisabled={!previewMode}
          >
            Print Preview
          </Button>
          
          <Button
            variant="outline"
            onClick={() => exportToFormat('xlsx')}
          >
            Export Excel
          </Button>
          
          <Button
            variant="outline"
            onClick={() => exportToFormat('csv')}
          >
            Export CSV
          </Button>
        </HStack>

        {/* Preview */}
        {previewMode && (
          <Box bg="white" color="black" p={4} borderRadius="lg" ref={previewRef}>
            <VStack spacing={4} align="stretch">
              <Text fontWeight="bold" textAlign="center" mb={4}>
                Preview: {selectedFormat.name} ({processedMembers.length} labels)
              </Text>
              
              <Box className="label-sheet">
                {processedMembers.map((member, index) => {
                  const addressLines = formatAddress(member);
                  if (addressLines.length === 0) return null;
                  
                  return (
                    <Box
                      key={`${member.member_id || index}`}
                      className="label"
                      display="inline-block"
                      width={`${selectedFormat.labelWidth}mm`}
                      height={`${selectedFormat.labelHeight}mm`}
                      border={labelStyle.includeBorder ? "1px solid #ccc" : "1px dashed #eee"}
                      p={`${labelStyle.padding}mm`}
                      m={`${selectedFormat.gapVertical/2}mm ${selectedFormat.gapHorizontal/2}mm`}
                      fontSize={`${labelStyle.fontSize}pt`}
                      lineHeight={labelStyle.lineHeight}
                      textAlign={labelStyle.alignment}
                      verticalAlign="top"
                      boxSizing="border-box"
                      overflow="hidden"
                    >
                      {addressLines.map((line, lineIndex) => (
                        <Text key={lineIndex} fontSize="inherit" lineHeight="inherit">
                          {line}
                        </Text>
                      ))}
                    </Box>
                  );
                })}
              </Box>
            </VStack>
          </Box>
        )}

        {/* Validation Warnings */}
        {processedMembers.length === 0 && (
          <Alert status="warning">
            <AlertIcon />
            <VStack align="start" spacing={1}>
              <Text fontWeight="semibold">Geen geldige adressen gevonden</Text>
              <Text fontSize="sm">
                Controleer of de geselecteerde leden complete adresgegevens hebben (naam, straat, postcode, woonplaats).
              </Text>
            </VStack>
          </Alert>
        )}

        {members.length > processedMembers.length && (
          <Alert status="info">
            <AlertIcon />
            <Text fontSize="sm">
              {members.length - processedMembers.length} leden uitgefilterd vanwege incomplete adresgegevens of landfilter.
            </Text>
          </Alert>
        )}
      </VStack>
    </Box>
  );
};

export default AddressLabelGenerator;