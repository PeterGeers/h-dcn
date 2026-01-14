import React, { useMemo } from 'react';
import {
  Box, VStack, HStack, Heading, SimpleGrid, Stat, StatLabel, StatNumber,
  Table, Thead, Tbody, Tr, Th, Td, Text, Progress, Alert, AlertIcon
} from '@chakra-ui/react';
import CSVExportButton from './CSVExportButton';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';

interface Event {
  event_id?: string;
  name?: string;
  event_date?: string;
  datum_van?: string;
  location?: string;
  locatie?: string;
  participants?: string | number;
  aantal_deelnemers?: string | number;
  revenue?: string | number;
  inkomsten?: string | number;
  cost?: string | number;
  kosten?: string | number;
}

interface AnalyticsDashboardProps {
  events: Event[];
  permissionManager?: FunctionPermissionManager | null;
  user?: any;
}

interface MonthlyData {
  events: number;
  participants: number;
  revenue: number;
  costs: number;
}

interface MonthlyStat extends MonthlyData {
  month: string;
  profit: number;
  avgAttendance: number;
}

interface LocationStat extends MonthlyData {
  location: string;
  profit: number;
  avgAttendance: number;
}

function AnalyticsDashboard({ events, permissionManager, user }: AnalyticsDashboardProps) {
  // Get user roles for permission checks within the component
  const userRoles = user ? getUserRoles(user) : [];
  
  // Check financial and export access for conditional rendering within the dashboard
  const hasFinancialRole = userRoles.some(role => 
    role === 'Events_CRUD' ||
    role === 'System_User_Management'
  );
  
  const canViewFinancials = permissionManager?.hasFieldAccess('events', 'read', { fieldType: 'financial' }) || hasFinancialRole;
  
  const hasExportRole = userRoles.some(role => 
    role === 'Events_CRUD' ||
    role === 'Events_Export' ||
    role === 'System_User_Management' ||
    role === 'Communication_Export'
  );
  
  const canExportAnalytics = permissionManager?.hasFieldAccess('events', 'read', { fieldType: 'export' }) || 
                            permissionManager?.hasAccess('communication', 'write') || 
                            hasExportRole;

  // Access check is now handled by FunctionGuard wrapper - no need for duplicate check here
  const analytics = useMemo(() => {
    if (!events || events.length === 0) {
      return {
        totalEvents: 0,
        totalParticipants: 0,
        averageAttendance: 0,
        totalRevenue: 0,
        totalCosts: 0,
        totalProfit: 0,
        avgCostPerParticipant: 0,
        monthlyStats: [],
        locationStats: [],
        profitableEvents: 0
      };
    }

    const totalEvents = events.length;
    const totalParticipants = events.reduce((sum, event) => sum + (parseInt(String(event.participants || event.aantal_deelnemers)) || 0), 0);
    const averageAttendance = totalEvents > 0 ? Math.round(totalParticipants / totalEvents) : 0;
    
    const totalRevenue = events.reduce((sum, event) => sum + (parseFloat(String(event.revenue || event.inkomsten)) || 0), 0);
    const totalCosts = events.reduce((sum, event) => sum + (parseFloat(String(event.cost || event.kosten)) || 0), 0);
    const totalProfit = totalRevenue - totalCosts;
    
    const avgCostPerParticipant = totalParticipants > 0 ? totalCosts / totalParticipants : 0;
    const profitableEvents = events.filter(event => 
      (parseFloat(String(event.revenue || event.inkomsten)) || 0) > (parseFloat(String(event.cost || event.kosten)) || 0)
    ).length;

    // Monthly statistics
    const monthlyData: Record<string, MonthlyData> = {};
    events.forEach(event => {
      const eventDate = event.event_date || event.datum_van;
      if (eventDate) {
        const month = new Date(eventDate).toLocaleDateString('nl-NL', { year: 'numeric', month: 'long' });
        if (!monthlyData[month]) {
          monthlyData[month] = { events: 0, participants: 0, revenue: 0, costs: 0 };
        }
        monthlyData[month].events += 1;
        monthlyData[month].participants += parseInt(String(event.participants || event.aantal_deelnemers)) || 0;
        monthlyData[month].revenue += parseFloat(String(event.revenue || event.inkomsten)) || 0;
        monthlyData[month].costs += parseFloat(String(event.cost || event.kosten)) || 0;
      }
    });

    const monthlyStats: MonthlyStat[] = Object.entries(monthlyData).map(([month, data]) => ({
      month,
      ...data,
      profit: data.revenue - data.costs,
      avgAttendance: data.events > 0 ? Math.round(data.participants / data.events) : 0
    }));

    // Location statistics
    const locationData: Record<string, MonthlyData> = {};
    events.forEach(event => {
      const location = event.location || event.locatie;
      if (location) {
        if (!locationData[location]) {
          locationData[location] = { events: 0, participants: 0, revenue: 0, costs: 0 };
        }
        locationData[location].events += 1;
        locationData[location].participants += parseInt(String(event.participants || event.aantal_deelnemers)) || 0;
        locationData[location].revenue += parseFloat(String(event.revenue || event.inkomsten)) || 0;
        locationData[location].costs += parseFloat(String(event.cost || event.kosten)) || 0;
      }
    });

    const locationStats: LocationStat[] = Object.entries(locationData)
      .map(([location, data]) => ({
        location,
        ...data,
        profit: data.revenue - data.costs,
        avgAttendance: data.events > 0 ? Math.round(data.participants / data.events) : 0
      }))
      .sort((a, b) => b.profit - a.profit);

    return {
      totalEvents,
      totalParticipants,
      averageAttendance,
      totalRevenue,
      totalCosts,
      totalProfit,
      avgCostPerParticipant,
      monthlyStats,
      locationStats,
      profitableEvents
    };
  }, [events]);

  const formatCurrency = (amount: number): string => `€${amount.toFixed(2)}`;

  const profitMargin = analytics.totalRevenue > 0 
    ? ((analytics.totalProfit / analytics.totalRevenue) * 100).toFixed(1)
    : '0';

  return (
    <VStack spacing={6} align="stretch">
      <HStack justify="space-between">
        <Heading size="lg" color="orange.400">Analytics Dashboard</Heading>
        {canExportAnalytics && (
          <CSVExportButton 
            data={analytics.monthlyStats} 
            filename="analytics_monthly"
            columns={[]}
          />
        )}
      </HStack>

      {/* Key Metrics */}
      <SimpleGrid columns={4} spacing={4}>
        <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="orange.400">
          <Stat>
            <StatLabel color="orange.300">Totaal Evenementen</StatLabel>
            <StatNumber color="white">{analytics.totalEvents}</StatNumber>
          </Stat>
        </Box>
        <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="blue.400">
          <Stat>
            <StatLabel color="blue.300">Totaal Deelnemers</StatLabel>
            <StatNumber color="white">{analytics.totalParticipants}</StatNumber>
          </Stat>
        </Box>
        <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="green.400">
          <Stat>
            <StatLabel color="green.300">Gem. Opkomst</StatLabel>
            <StatNumber color="white">{analytics.averageAttendance}</StatNumber>
          </Stat>
        </Box>
        <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="purple.400">
          <Stat>
            <StatLabel color="purple.300">Winstgevende Events</StatLabel>
            <StatNumber color="white">{analytics.profitableEvents}</StatNumber>
          </Stat>
        </Box>
      </SimpleGrid>

      {/* Financial Overview - Only show if user has financial access */}
      {canViewFinancials && (
        <SimpleGrid columns={4} spacing={4}>
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="green.400">
            <Stat>
              <StatLabel color="green.300">Totale Inkomsten</StatLabel>
              <StatNumber color="green.400">{formatCurrency(analytics.totalRevenue)}</StatNumber>
            </Stat>
          </Box>
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="red.400">
            <Stat>
              <StatLabel color="red.300">Totale Kosten</StatLabel>
              <StatNumber color="red.400">{formatCurrency(analytics.totalCosts)}</StatNumber>
            </Stat>
          </Box>
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor={analytics.totalProfit >= 0 ? "green.400" : "red.400"}>
            <Stat>
              <StatLabel color={analytics.totalProfit >= 0 ? "green.300" : "red.300"}>Totale Winst</StatLabel>
              <StatNumber color={analytics.totalProfit >= 0 ? "green.400" : "red.400"}>
                {formatCurrency(analytics.totalProfit)}
              </StatNumber>
            </Stat>
          </Box>
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="yellow.400">
            <Stat>
              <StatLabel color="yellow.300">Kosten per Deelnemer</StatLabel>
              <StatNumber color="white">{formatCurrency(analytics.avgCostPerParticipant)}</StatNumber>
            </Stat>
          </Box>
        </SimpleGrid>
      )}

      {/* Profit Margin - Only show if user has financial access */}
      {canViewFinancials && (
        <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="orange.400">
          <Text color="orange.300" mb={2}>Winstmarge: {profitMargin}%</Text>
          <Progress 
            value={Math.max(0, Math.min(100, parseFloat(profitMargin)))} 
            colorScheme={parseFloat(profitMargin) > 0 ? "green" : "red"}
            size="lg"
          />
        </Box>
      )}

      {/* Monthly Statistics */}
      <Box>
        <HStack justify="space-between" mb={4}>
          <Heading size="md" color="orange.400">Maandelijkse Statistieken</Heading>
          {canExportAnalytics && (
            <CSVExportButton 
              data={analytics.monthlyStats} 
              filename="monthly_stats"
              columns={[]}
            />
          )}
        </HStack>
        <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
          <Table variant="simple">
            <Thead bg="gray.700">
              <Tr>
                <Th color="orange.300">Maand</Th>
                <Th color="orange.300">Events</Th>
                <Th color="orange.300">Deelnemers</Th>
                <Th color="orange.300">Gem. Opkomst</Th>
                {canViewFinancials && <Th color="orange.300">Inkomsten</Th>}
                {canViewFinancials && <Th color="orange.300">Kosten</Th>}
                {canViewFinancials && <Th color="orange.300">Winst</Th>}
              </Tr>
            </Thead>
            <Tbody>
              {analytics.monthlyStats.map((stat, index) => (
                <Tr key={index}>
                  <Td color="white">{stat.month}</Td>
                  <Td color="white">{stat.events}</Td>
                  <Td color="white">{stat.participants}</Td>
                  <Td color="white">{stat.avgAttendance}</Td>
                  {canViewFinancials && <Td color="white">{formatCurrency(stat.revenue)}</Td>}
                  {canViewFinancials && <Td color="white">{formatCurrency(stat.costs)}</Td>}
                  {canViewFinancials && (
                    <Td color={stat.profit >= 0 ? "green.400" : "red.400"}>
                      {formatCurrency(stat.profit)}
                    </Td>
                  )}
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Location Statistics */}
      <Box>
        <HStack justify="space-between" mb={4}>
          <Heading size="md" color="orange.400">Locatie Prestaties</Heading>
          {canExportAnalytics && (
            <CSVExportButton 
              data={analytics.locationStats} 
              filename="location_stats"
              columns={[]}
            />
          )}
        </HStack>
        <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
          <Table variant="simple">
            <Thead bg="gray.700">
              <Tr>
                <Th color="orange.300">Locatie</Th>
                <Th color="orange.300">Events</Th>
                <Th color="orange.300">Deelnemers</Th>
                <Th color="orange.300">Gem. Opkomst</Th>
                {canViewFinancials && <Th color="orange.300">Winst</Th>}
              </Tr>
            </Thead>
            <Tbody>
              {analytics.locationStats.slice(0, 10).map((stat, index) => (
                <Tr key={index}>
                  <Td color="white">{stat.location}</Td>
                  <Td color="white">{stat.events}</Td>
                  <Td color="white">{stat.participants}</Td>
                  <Td color="white">{stat.avgAttendance}</Td>
                  {canViewFinancials && (
                    <Td color={stat.profit >= 0 ? "green.400" : "red.400"}>
                      {formatCurrency(stat.profit)}
                    </Td>
                  )}
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>
    </VStack>
  );
}

export default AnalyticsDashboard;