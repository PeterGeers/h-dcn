/**
 * Analytics Section Component
 * 
 * Main analytics dashboard section that displays regional statistics,
 * violin plots, and membership trends using processed parquet data.
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  SimpleGrid,
  Button,
  ButtonGroup,
  Select,
  Spinner,
  Alert,
  AlertIcon,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  useColorModeValue,
  useToast,
  Collapse,
  IconButton
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon } from '@chakra-ui/icons';
import { Member } from '../../types/index';
import { 
  analyticsService, 
  AnalyticsOverview, 
  RegionalStats, 
  ViolinPlotData,
  MembershipTrends 
} from '../../services/AnalyticsService';
import RegionalStatsCard from './RegionalStatsCard';
import ViolinPlotVisualization from './ViolinPlotVisualization';

// ============================================================================
// TYPES
// ============================================================================

interface AnalyticsSectionProps {
  members: Member[];
  loading?: boolean;
  error?: string | null;
  userRegion?: string;
  onRefreshData?: () => Promise<void>;
}

type ViewMode = 'overview' | 'regional' | 'trends' | 'visualizations';

// ============================================================================
// COMPONENT
// ============================================================================

const AnalyticsSection: React.FC<AnalyticsSectionProps> = ({
  members,
  loading = false,
  error = null,
  userRegion,
  onRefreshData
}) => {
  // State
  const [viewMode, setViewMode] = useState<ViewMode>('overview');
  const [selectedRegion, setSelectedRegion] = useState<string>('all');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showDetails, setShowDetails] = useState(true);
  
  // Analytics data state
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [regionalStats, setRegionalStats] = useState<RegionalStats[]>([]);
  const [ageViolinData, setAgeViolinData] = useState<ViolinPlotData[]>([]);
  const [membershipViolinData, setMembershipViolinData] = useState<ViolinPlotData[]>([]);
  const [membershipTrends, setMembershipTrends] = useState<MembershipTrends | null>(null);

  const toast = useToast();

  // Theme colors
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'orange.400');
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const headingColor = useColorModeValue('gray.800', 'orange.300');

  // Process analytics data when members change
  useEffect(() => {
    if (members && members.length > 0) {
      processAnalyticsData();
    }
  }, [members]);

  // Process analytics data
  const processAnalyticsData = async () => {
    if (!members || members.length === 0) return;

    setIsProcessing(true);
    
    try {
      console.log(`[AnalyticsSection] Processing analytics for ${members.length} members`);

      // Generate all analytics data
      const [
        overviewData,
        regionalData,
        ageViolin,
        membershipViolin,
        trendsData
      ] = await Promise.all([
        Promise.resolve(analyticsService.generateOverview(members)),
        Promise.resolve(analyticsService.generateRegionalStats(members)),
        Promise.resolve(analyticsService.generateAgeViolinData(members)),
        Promise.resolve(analyticsService.generateMembershipViolinData(members)),
        Promise.resolve(analyticsService.generateMembershipTrends(members))
      ]);

      setOverview(overviewData);
      setRegionalStats(regionalData);
      setAgeViolinData(ageViolin);
      setMembershipViolinData(membershipViolin);
      setMembershipTrends(trendsData);

      console.log('[AnalyticsSection] Analytics processing completed', {
        overview: overviewData,
        regions: regionalData.length,
        ageViolinRegions: ageViolin.length,
        membershipViolinRegions: membershipViolin.length,
        trendsYears: trendsData.yearlyGrowth.length
      });

    } catch (err) {
      console.error('[AnalyticsSection] Error processing analytics:', err);
      toast({
        title: 'Fout bij verwerken analytics',
        description: err instanceof Error ? err.message : 'Onbekende fout',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Filter regional stats by selected region
  const filteredRegionalStats = useMemo(() => {
    if (selectedRegion === 'all') return regionalStats;
    return regionalStats.filter(stats => stats.region === selectedRegion);
  }, [regionalStats, selectedRegion]);

  // Get available regions
  const availableRegions = useMemo(() => {
    return regionalStats.map(stats => stats.region).sort();
  }, [regionalStats]);

  // Handle export chart
  const handleExportChart = (chartType: 'age' | 'membership') => {
    toast({
      title: 'Export functie',
      description: `${chartType === 'age' ? 'Leeftijd' : 'Lidmaatschap'} grafiek export wordt geïmplementeerd`,
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  // Handle full screen
  const handleFullScreen = (chartType: 'age' | 'membership') => {
    toast({
      title: 'Volledig scherm',
      description: `${chartType === 'age' ? 'Leeftijd' : 'Lidmaatschap'} grafiek volledig scherm wordt geïmplementeerd`,
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  // Handle refresh
  const handleRefresh = async () => {
    if (onRefreshData) {
      await onRefreshData();
    } else {
      await processAnalyticsData();
    }
  };

  // Render loading state
  if (loading || isProcessing) {
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
          <Text color={textColor}>
            {loading ? 'Laden van member data...' : 'Verwerken van analytics...'}
          </Text>
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
            <Text fontWeight="semibold">Fout bij laden van analytics</Text>
            <Text fontSize="sm">{error}</Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // Render empty state
  if (!members || members.length === 0) {
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
            Geen member data beschikbaar
          </Text>
          <Text color={textColor} fontSize="sm">
            Laad eerst member data om analytics te kunnen bekijken.
          </Text>
          {onRefreshData && (
            <Button colorScheme="orange" onClick={handleRefresh}>
              Data Vernieuwen
            </Button>
          )}
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
            <Heading size="lg" color={headingColor}>
              📊 Analytics Dashboard
            </Heading>
            <HStack spacing={2}>
              <Badge colorScheme="orange" fontSize="sm">
                {members.length} leden
              </Badge>
              <Badge colorScheme="blue" fontSize="sm">
                {regionalStats.length} regio's
              </Badge>
              {userRegion && (
                <Badge colorScheme="green" fontSize="sm">
                  Regio: {userRegion}
                </Badge>
              )}
            </HStack>
          </VStack>

          <HStack spacing={2}>
            <IconButton
              aria-label={showDetails ? 'Verberg details' : 'Toon details'}
              icon={showDetails ? <ChevronUpIcon /> : <ChevronDownIcon />}
              size="sm"
              variant="outline"
              colorScheme="orange"
              onClick={() => setShowDetails(!showDetails)}
            />
            <Button
              size="sm"
              variant="outline"
              colorScheme="orange"
              onClick={handleRefresh}
              isLoading={isProcessing}
            >
              🔄 Vernieuwen
            </Button>
          </HStack>
        </HStack>

        {/* View Mode Selector */}
        <ButtonGroup size="sm" isAttached variant="outline" alignSelf="start">
          <Button
            colorScheme={viewMode === 'overview' ? 'orange' : 'gray'}
            onClick={() => setViewMode('overview')}
          >
            📈 Overzicht
          </Button>
          <Button
            colorScheme={viewMode === 'regional' ? 'orange' : 'gray'}
            onClick={() => setViewMode('regional')}
          >
            📍 Regionaal
          </Button>
          <Button
            colorScheme={viewMode === 'visualizations' ? 'orange' : 'gray'}
            onClick={() => setViewMode('visualizations')}
          >
            🎻 Visualisaties
          </Button>
          <Button
            colorScheme={viewMode === 'trends' ? 'orange' : 'gray'}
            onClick={() => setViewMode('trends')}
          >
            📊 Trends
          </Button>
        </ButtonGroup>

        {/* Content based on view mode */}
        <Collapse in={showDetails}>
          {viewMode === 'overview' && overview && (
            <VStack spacing={6} align="stretch">
              {/* Overview Statistics */}
              <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                <Stat>
                  <StatLabel color={textColor}>Totaal Leden</StatLabel>
                  <StatNumber color={headingColor}>{overview.totalMembers}</StatNumber>
                  <StatHelpText color={textColor}>
                    {overview.activeMembers} actief
                  </StatHelpText>
                </Stat>

                <Stat>
                  <StatLabel color={textColor}>Gemiddelde Leeftijd</StatLabel>
                  <StatNumber color={headingColor}>{overview.averageAge} jaar</StatNumber>
                  <StatHelpText color={textColor}>
                    Alle leden
                  </StatHelpText>
                </Stat>

                <Stat>
                  <StatLabel color={textColor}>Gem. Lidmaatschap</StatLabel>
                  <StatNumber color={headingColor}>{overview.averageMembershipYears} jaar</StatNumber>
                  <StatHelpText color={textColor}>
                    Lidmaatschap duur
                  </StatHelpText>
                </Stat>

                <Stat>
                  <StatLabel color={textColor}>Top Regio</StatLabel>
                  <StatNumber color={headingColor} fontSize="lg">
                    {overview.topRegions[0]?.region || 'N/A'}
                  </StatNumber>
                  <StatHelpText color={textColor}>
                    {overview.topRegions[0]?.memberCount || 0} leden
                  </StatHelpText>
                </Stat>
              </SimpleGrid>

              {/* Top Regions */}
              <VStack spacing={3} align="stretch">
                <Text fontWeight="semibold" color={headingColor}>
                  Top 5 Regio's
                </Text>
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
                  {overview.topRegions.slice(0, 5).map((region, index) => (
                    <HStack key={region.region} justify="space-between" p={3} bg="gray.50" borderRadius="md">
                      <HStack spacing={2}>
                        <Badge colorScheme="orange" fontSize="xs">
                          #{index + 1}
                        </Badge>
                        <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                          {region.region}
                        </Text>
                      </HStack>
                      <VStack spacing={0} align="end">
                        <Text fontSize="sm" fontWeight="bold" color={headingColor}>
                          {region.memberCount}
                        </Text>
                        <Text fontSize="xs" color={textColor}>
                          {region.percentage.toFixed(1)}%
                        </Text>
                      </VStack>
                    </HStack>
                  ))}
                </SimpleGrid>
              </VStack>

              {/* Membership Types */}
              <VStack spacing={3} align="stretch">
                <Text fontWeight="semibold" color={headingColor}>
                  Lidmaatschap Types
                </Text>
                <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>
                  {Object.entries(overview.membershipTypes).map(([type, count]) => (
                    <HStack key={type} justify="space-between" p={3} bg="gray.50" borderRadius="md">
                      <Text fontSize="sm" color={headingColor}>
                        {type}
                      </Text>
                      <Badge colorScheme="blue" fontSize="sm">
                        {count}
                      </Badge>
                    </HStack>
                  ))}
                </SimpleGrid>
              </VStack>
            </VStack>
          )}

          {viewMode === 'regional' && (
            <VStack spacing={6} align="stretch">
              {/* Region Filter */}
              {availableRegions.length > 1 && (
                <HStack spacing={4}>
                  <Text fontSize="sm" color={textColor} fontWeight="medium">
                    Filter regio:
                  </Text>
                  <Select
                    size="sm"
                    value={selectedRegion}
                    onChange={(e) => setSelectedRegion(e.target.value)}
                    bg={cardBg}
                    borderColor={borderColor}
                    maxW="200px"
                  >
                    <option value="all">Alle regio's</option>
                    {availableRegions.map(region => (
                      <option key={region} value={region}>
                        {region}
                      </option>
                    ))}
                  </Select>
                </HStack>
              )}

              {/* Regional Stats Cards */}
              <SimpleGrid columns={{ base: 1, lg: 2, xl: 3 }} spacing={6}>
                {filteredRegionalStats.map(stats => (
                  <RegionalStatsCard
                    key={stats.region}
                    stats={stats}
                    totalMembers={overview?.activeMembers || 0}
                    showDetails={true}
                  />
                ))}
              </SimpleGrid>
            </VStack>
          )}

          {viewMode === 'visualizations' && (
            <VStack spacing={6} align="stretch">
              <ViolinPlotVisualization
                ageData={ageViolinData}
                membershipData={membershipViolinData}
                loading={isProcessing}
                error={null}
                onExportChart={handleExportChart}
                onFullScreen={handleFullScreen}
              />
            </VStack>
          )}

          {viewMode === 'trends' && membershipTrends && (
            <VStack spacing={6} align="stretch">
              <Text color={headingColor} fontWeight="semibold">
                🚧 Trends sectie wordt binnenkort geïmplementeerd
              </Text>
              <Text color={textColor} fontSize="sm">
                Hier komen grafieken voor lidmaatschap groei over tijd en regionale trends.
              </Text>
              
              {/* Preview of trends data */}
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <VStack spacing={2} align="start">
                  <Text fontWeight="semibold" color={headingColor} fontSize="sm">
                    Jaarlijkse Groei (laatste 5 jaar)
                  </Text>
                  {membershipTrends.yearlyGrowth.slice(-5).map(year => (
                    <HStack key={year.year} justify="space-between" w="full">
                      <Text fontSize="sm" color={textColor}>
                        {year.year}
                      </Text>
                      <Badge colorScheme={year.growthRate > 0 ? 'green' : 'red'} fontSize="xs">
                        {year.newMembers} nieuwe leden
                      </Badge>
                    </HStack>
                  ))}
                </VStack>

                <VStack spacing={2} align="start">
                  <Text fontWeight="semibold" color={headingColor} fontSize="sm">
                    Regionale Groei (dit jaar)
                  </Text>
                  {membershipTrends.regionalGrowth.slice(0, 5).map(region => (
                    <HStack key={region.region} justify="space-between" w="full">
                      <Text fontSize="sm" color={textColor}>
                        {region.region}
                      </Text>
                      <Badge 
                        colorScheme={region.growthRate > 0 ? 'green' : region.growthRate < 0 ? 'red' : 'gray'} 
                        fontSize="xs"
                      >
                        {region.growthRate > 0 ? '+' : ''}{region.growthRate.toFixed(1)}%
                      </Badge>
                    </HStack>
                  ))}
                </VStack>
              </SimpleGrid>
            </VStack>
          )}
        </Collapse>
      </VStack>
    </Box>
  );
};

export default AnalyticsSection;