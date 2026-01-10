/**
 * Regional Statistics Card Component
 * 
 * Displays statistics for a specific region including member counts,
 * membership types, age distribution, and membership duration.
 */

import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Progress,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Divider,
  useColorModeValue
} from '@chakra-ui/react';
import { RegionalStats } from '../../services/AnalyticsService';

// ============================================================================
// TYPES
// ============================================================================

interface RegionalStatsCardProps {
  stats: RegionalStats;
  totalMembers: number; // Total across all regions for percentage calculations
  showDetails?: boolean;
  onCardClick?: (region: string) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

const RegionalStatsCard: React.FC<RegionalStatsCardProps> = ({
  stats,
  totalMembers,
  showDetails = true,
  onCardClick
}) => {
  // Theme colors
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'orange.400');
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const headingColor = useColorModeValue('gray.800', 'orange.300');

  // Calculate percentage of total members
  const percentage = totalMembers > 0 ? (stats.totalMembers / totalMembers) * 100 : 0;

  // Get membership type colors
  const getMembershipTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      'Gewoon lid': 'blue',
      'Gezins lid': 'green',
      'Donateur': 'purple',
      'Gezins donateur': 'orange',
      'Onbekend': 'gray'
    };
    return colors[type] || 'gray';
  };

  // Handle card click
  const handleClick = () => {
    if (onCardClick) {
      onCardClick(stats.region);
    }
  };

  return (
    <Box
      bg={cardBg}
      border="1px"
      borderColor={borderColor}
      borderRadius="lg"
      p={6}
      cursor={onCardClick ? 'pointer' : 'default'}
      onClick={handleClick}
      _hover={onCardClick ? { borderColor: 'orange.500', shadow: 'md' } : {}}
      transition="all 0.2s"
    >
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Heading size="md" color={headingColor}>
            📍 {stats.region}
          </Heading>
          <Badge colorScheme="orange" fontSize="sm">
            {percentage.toFixed(1)}%
          </Badge>
        </HStack>

        {/* Main Statistics */}
        <SimpleGrid columns={2} spacing={4}>
          <Stat>
            <StatLabel color={textColor}>Totaal Leden</StatLabel>
            <StatNumber color={headingColor}>{stats.totalMembers}</StatNumber>
            <StatHelpText color={textColor}>
              {percentage.toFixed(1)}% van totaal
            </StatHelpText>
          </Stat>

          <Stat>
            <StatLabel color={textColor}>Gem. Leeftijd</StatLabel>
            <StatNumber color={headingColor}>{stats.averageAge} jaar</StatNumber>
            <StatHelpText color={textColor}>
              {stats.averageMembershipYears} jaar lid
            </StatHelpText>
          </Stat>
        </SimpleGrid>

        {showDetails && (
          <>
            <Divider borderColor={borderColor} />

            {/* Membership Types */}
            <VStack spacing={3} align="stretch">
              <Text fontWeight="semibold" color={headingColor} fontSize="sm">
                Lidmaatschap Types
              </Text>
              {Object.entries(stats.membersByType)
                .sort(([, a], [, b]) => b - a)
                .map(([type, count]) => {
                  const typePercentage = (count / stats.totalMembers) * 100;
                  return (
                    <HStack key={type} justify="space-between">
                      <HStack spacing={2}>
                        <Badge 
                          colorScheme={getMembershipTypeColor(type)} 
                          size="sm"
                        >
                          {type}
                        </Badge>
                        <Text fontSize="sm" color={textColor}>
                          {count} leden
                        </Text>
                      </HStack>
                      <Text fontSize="sm" color={textColor} fontWeight="medium">
                        {typePercentage.toFixed(1)}%
                      </Text>
                    </HStack>
                  );
                })}
            </VStack>

            <Divider borderColor={borderColor} />

            {/* Age Distribution */}
            <VStack spacing={3} align="stretch">
              <Text fontWeight="semibold" color={headingColor} fontSize="sm">
                Leeftijdsverdeling
              </Text>
              <SimpleGrid columns={2} spacing={2}>
                <VStack spacing={1}>
                  <Text fontSize="xs" color={textColor}>Onder 30</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.ageDistribution.under30}
                  </Text>
                </VStack>
                <VStack spacing={1}>
                  <Text fontSize="xs" color={textColor}>30-50</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.ageDistribution.age30to50}
                  </Text>
                </VStack>
                <VStack spacing={1}>
                  <Text fontSize="xs" color={textColor}>50-65</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.ageDistribution.age50to65}
                  </Text>
                </VStack>
                <VStack spacing={1}>
                  <Text fontSize="xs" color={textColor}>65+</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.ageDistribution.over65}
                  </Text>
                </VStack>
              </SimpleGrid>
            </VStack>

            <Divider borderColor={borderColor} />

            {/* Membership Duration Distribution */}
            <VStack spacing={3} align="stretch">
              <Text fontWeight="semibold" color={headingColor} fontSize="sm">
                Lidmaatschap Duur
              </Text>
              <VStack spacing={2}>
                <HStack justify="space-between" w="full">
                  <Text fontSize="xs" color={textColor}>Onder 5 jaar</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.membershipDistribution.under5years}
                  </Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text fontSize="xs" color={textColor}>5-10 jaar</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.membershipDistribution.years5to10}
                  </Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text fontSize="xs" color={textColor}>10-20 jaar</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.membershipDistribution.years10to20}
                  </Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text fontSize="xs" color={textColor}>20+ jaar</Text>
                  <Text fontSize="sm" fontWeight="medium" color={headingColor}>
                    {stats.membershipDistribution.over20years}
                  </Text>
                </HStack>
              </VStack>
            </VStack>
          </>
        )}
      </VStack>
    </Box>
  );
};

export default RegionalStatsCard;