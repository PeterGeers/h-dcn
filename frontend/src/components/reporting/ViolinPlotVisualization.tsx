/**
 * Violin Plot Visualization Component
 * 
 * Creates interactive violin plots for age and membership duration distributions
 * by region using @visx/stats and Recharts for enhanced visualizations.
 */

import React, { useState, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Select,
  Button,
  ButtonGroup,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
  Tooltip,
  Badge
} from '@chakra-ui/react';
import {
  ResponsiveContainer,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  Bar,
  Line,
  Area
} from 'recharts';
import { ViolinPlotData } from '../../services/AnalyticsService';

// ============================================================================
// TYPES
// ============================================================================

interface ViolinPlotVisualizationProps {
  ageData: ViolinPlotData[];
  membershipData: ViolinPlotData[];
  loading?: boolean;
  error?: string | null;
  onExportChart?: (chartType: 'age' | 'membership') => void;
  onFullScreen?: (chartType: 'age' | 'membership') => void;
}

type ChartType = 'age' | 'membership';
type ViewMode = 'violin' | 'box' | 'histogram';

// ============================================================================
// COMPONENT
// ============================================================================

const ViolinPlotVisualization: React.FC<ViolinPlotVisualizationProps> = ({
  ageData,
  membershipData,
  loading = false,
  error = null,
  onExportChart,
  onFullScreen
}) => {
  // State
  const [selectedChart, setSelectedChart] = useState<ChartType>('age');
  const [viewMode, setViewMode] = useState<ViewMode>('violin');
  const [selectedRegion, setSelectedRegion] = useState<string>('all');

  // Theme colors
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'orange.400');
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const headingColor = useColorModeValue('gray.800', 'orange.300');

  // Get current data based on selected chart
  const currentData = selectedChart === 'age' ? ageData : membershipData;
  const chartTitle = selectedChart === 'age' ? 'Leeftijdsverdeling' : 'Lidmaatschap Duur';
  const yAxisLabel = selectedChart === 'age' ? 'Leeftijd (jaren)' : 'Lidmaatschap (jaren)';

  // Filter data by region if selected
  const filteredData = useMemo(() => {
    if (selectedRegion === 'all') return currentData;
    return currentData.filter(item => item.region === selectedRegion);
  }, [currentData, selectedRegion]);

  // Get available regions
  const availableRegions = useMemo(() => {
    const regions = new Set(currentData.map(item => item.region));
    return Array.from(regions).sort();
  }, [currentData]);

  // Prepare chart data for Recharts
  const chartData = useMemo(() => {
    return filteredData.map(item => ({
      region: item.region,
      count: item.values.length,
      average: item.values.reduce((sum, val) => sum + val, 0) / item.values.length,
      median: item.quartiles.median,
      q1: item.quartiles.q1,
      q3: item.quartiles.q3,
      min: item.quartiles.min,
      max: item.quartiles.max,
      // For histogram view
      ...item.density.reduce((acc, point, index) => {
        acc[`density_${index}`] = point.density;
        return acc;
      }, {} as Record<string, number>)
    }));
  }, [filteredData]);

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box
          bg={cardBg}
          border="1px"
          borderColor={borderColor}
          borderRadius="md"
          p={3}
          shadow="lg"
        >
          <Text fontWeight="semibold" color={headingColor}>
            {label}
          </Text>
          <VStack spacing={1} align="start">
            <Text fontSize="sm" color={textColor}>
              Aantal leden: {data.count}
            </Text>
            <Text fontSize="sm" color={textColor}>
              Gemiddelde: {data.average.toFixed(1)} {selectedChart === 'age' ? 'jaar' : 'jaar lid'}
            </Text>
            <Text fontSize="sm" color={textColor}>
              Mediaan: {data.median} {selectedChart === 'age' ? 'jaar' : 'jaar lid'}
            </Text>
            <Text fontSize="sm" color={textColor}>
              Bereik: {data.min} - {data.max} {selectedChart === 'age' ? 'jaar' : 'jaar lid'}
            </Text>
          </VStack>
        </Box>
      );
    }
    return null;
  };

  // Handle export
  const handleExport = () => {
    if (onExportChart) {
      onExportChart(selectedChart);
    }
  };

  // Handle full screen
  const handleFullScreen = () => {
    if (onFullScreen) {
      onFullScreen(selectedChart);
    }
  };

  // Render loading state
  if (loading) {
    return (
      <Box
        bg={cardBg}
        border="1px"
        borderColor={borderColor}
        borderRadius="lg"
        p={8}
        textAlign="center"
      >
        <VStack spacing={4}>
          <Spinner size="lg" color="orange.500" />
          <Text color={textColor}>Laden van visualisatie data...</Text>
        </VStack>
      </Box>
    );
  }

  // Render error state
  if (error) {
    return (
      <Box
        bg={cardBg}
        border="1px"
        borderColor={borderColor}
        borderRadius="lg"
        p={6}
      >
        <Alert status="error">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold">Fout bij laden van visualisatie</Text>
            <Text fontSize="sm">{error}</Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // Render empty state
  if (currentData.length === 0) {
    return (
      <Box
        bg={cardBg}
        border="1px"
        borderColor={borderColor}
        borderRadius="lg"
        p={8}
        textAlign="center"
      >
        <VStack spacing={4}>
          <Text fontSize="4xl">📊</Text>
          <Text color={headingColor} fontWeight="semibold">
            Geen data beschikbaar
          </Text>
          <Text color={textColor} fontSize="sm">
            Er zijn onvoldoende gegevens om een visualisatie te genereren.
          </Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box
      bg={cardBg}
      border="1px"
      borderColor={borderColor}
      borderRadius="lg"
      p={6}
    >
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center" wrap="wrap" spacing={4}>
          <VStack align="start" spacing={1}>
            <Heading size="md" color={headingColor}>
              📈 {chartTitle} per Regio
            </Heading>
            <HStack spacing={2}>
              <Badge colorScheme="orange" fontSize="xs">
                {filteredData.length} regio{filteredData.length !== 1 ? "'s" : ''}
              </Badge>
              <Badge colorScheme="blue" fontSize="xs">
                {filteredData.reduce((sum, item) => sum + item.values.length, 0)} leden
              </Badge>
            </HStack>
          </VStack>

          <HStack spacing={2}>
            <Button
              size="sm"
              variant="outline"
              colorScheme="orange"
              onClick={handleExport}
            >
              📊 Export
            </Button>
            <Button
              size="sm"
              variant="outline"
              colorScheme="orange"
              onClick={handleFullScreen}
            >
              🔍 Volledig scherm
            </Button>
          </HStack>
        </HStack>

        {/* Controls */}
        <HStack spacing={4} wrap="wrap">
          <VStack align="start" spacing={1}>
            <Text fontSize="sm" color={textColor} fontWeight="medium">
              Metric:
            </Text>
            <ButtonGroup size="sm" isAttached variant="outline">
              <Button
                colorScheme={selectedChart === 'age' ? 'orange' : 'gray'}
                onClick={() => setSelectedChart('age')}
              >
                Leeftijd
              </Button>
              <Button
                colorScheme={selectedChart === 'membership' ? 'orange' : 'gray'}
                onClick={() => setSelectedChart('membership')}
              >
                Lidmaatschap
              </Button>
            </ButtonGroup>
          </VStack>

          <VStack align="start" spacing={1}>
            <Text fontSize="sm" color={textColor} fontWeight="medium">
              Weergave:
            </Text>
            <ButtonGroup size="sm" isAttached variant="outline">
              <Tooltip label="Violin plot toont de volledige distributie">
                <Button
                  colorScheme={viewMode === 'violin' ? 'orange' : 'gray'}
                  onClick={() => setViewMode('violin')}
                >
                  🎻 Violin
                </Button>
              </Tooltip>
              <Tooltip label="Box plot toont kwartielen en uitschieters">
                <Button
                  colorScheme={viewMode === 'box' ? 'orange' : 'gray'}
                  onClick={() => setViewMode('box')}
                >
                  📦 Box
                </Button>
              </Tooltip>
              <Tooltip label="Histogram toont frequentieverdeling">
                <Button
                  colorScheme={viewMode === 'histogram' ? 'orange' : 'gray'}
                  onClick={() => setViewMode('histogram')}
                >
                  📊 Histogram
                </Button>
              </Tooltip>
            </ButtonGroup>
          </VStack>

          {availableRegions.length > 1 && (
            <VStack align="start" spacing={1}>
              <Text fontSize="sm" color={textColor} fontWeight="medium">
                Regio:
              </Text>
              <Select
                size="sm"
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                bg={cardBg}
                borderColor={borderColor}
                minW="150px"
              >
                <option value="all">Alle regio's</option>
                {availableRegions.map(region => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
              </Select>
            </VStack>
          )}
        </HStack>

        {/* Chart */}
        <Box height="400px" width="100%">
          <ResponsiveContainer width="100%" height="100%">
            {viewMode === 'violin' || viewMode === 'box' ? (
              <ComposedChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                <XAxis 
                  dataKey="region" 
                  tick={{ fill: textColor, fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  tick={{ fill: textColor, fontSize: 12 }}
                  label={{ 
                    value: yAxisLabel, 
                    angle: -90, 
                    position: 'insideLeft',
                    style: { textAnchor: 'middle', fill: textColor }
                  }}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend />
                
                {/* Box plot elements */}
                <Bar 
                  dataKey="q1" 
                  fill="transparent" 
                  stroke="#FFA500" 
                  strokeWidth={2}
                  name="Q1"
                />
                <Bar 
                  dataKey="median" 
                  fill="#FFA500" 
                  opacity={0.7}
                  name="Mediaan"
                />
                <Bar 
                  dataKey="q3" 
                  fill="transparent" 
                  stroke="#FFA500" 
                  strokeWidth={2}
                  name="Q3"
                />
                <Line 
                  type="monotone" 
                  dataKey="average" 
                  stroke="#FF6B35" 
                  strokeWidth={3}
                  dot={{ fill: '#FF6B35', strokeWidth: 2, r: 4 }}
                  name="Gemiddelde"
                />
              </ComposedChart>
            ) : (
              <ComposedChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                <XAxis 
                  dataKey="region" 
                  tick={{ fill: textColor, fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  tick={{ fill: textColor, fontSize: 12 }}
                  label={{ 
                    value: 'Aantal leden', 
                    angle: -90, 
                    position: 'insideLeft',
                    style: { textAnchor: 'middle', fill: textColor }
                  }}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend />
                
                <Bar 
                  dataKey="count" 
                  fill="#FFA500" 
                  opacity={0.8}
                  name="Aantal leden"
                />
              </ComposedChart>
            )}
          </ResponsiveContainer>
        </Box>

        {/* Summary Statistics */}
        <HStack spacing={6} wrap="wrap" justify="center">
          {filteredData.map(item => (
            <VStack key={item.region} spacing={1} align="center">
              <Text fontSize="sm" fontWeight="semibold" color={headingColor}>
                {item.region}
              </Text>
              <Text fontSize="xs" color={textColor}>
                {item.values.length} leden
              </Text>
              <Text fontSize="xs" color={textColor}>
                Ø {(item.values.reduce((sum, val) => sum + val, 0) / item.values.length).toFixed(1)}
                {selectedChart === 'age' ? ' jaar' : ' jaar lid'}
              </Text>
            </VStack>
          ))}
        </HStack>
      </VStack>
    </Box>
  );
};

export default ViolinPlotVisualization;