/**
 * WebshopManagementPage — Main page for the Webshop Management admin section.
 *
 * Features:
 * - Tab navigation: Producten, Bestellingen, Betalingen, Rapporten
 * - Shared channel filter state via useChannelFilter hook
 * - Independent of PresMeet onboarding flow (no club_id or OnboardingFlow dependency)
 * - Accessible to users with Products_CRUD, Products_Read, or Products_Export roles
 *
 * Validates: Requirements 1.3, 1.7, 8.1, 8.2
 */

import React from 'react';
import {
  Container,
  Heading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  HStack,
} from '@chakra-ui/react';
import { ChannelFilter } from './components/TenantFilter';
import { ProductsTab } from './components/ProductsTab';
import { OrdersTab } from './components/OrdersTab';
import { PaymentsTab } from './components/PaymentsTab';
import { ReportsTab } from './components/ReportsTab';
import { useChannelFilter } from './hooks/useTenantFilter';

const WebshopManagementPage: React.FC = () => {
  const { channel, setChannel } = useChannelFilter();

  return (
    <Container maxW="container.xl" py={6}>
      <HStack justify="space-between" align="center" mb={6}>
        <Heading size="lg" color="orange.400">
          Webshop Beheer
        </Heading>
        <ChannelFilter value={channel} onChange={setChannel} />
      </HStack>

      <Tabs colorScheme="orange" variant="enclosed">
        <TabList>
          <Tab>Producten</Tab>
          <Tab>Bestellingen</Tab>
          <Tab>Betalingen</Tab>
          <Tab>Rapporten</Tab>
        </TabList>

        <TabPanels>
          {/* Products Tab */}
          <TabPanel px={0}>
            <ProductsTab tenant={channel} />
          </TabPanel>

          {/* Orders Tab */}
          <TabPanel px={0}>
            <OrdersTab tenant={channel} />
          </TabPanel>

          {/* Payments Tab */}
          <TabPanel px={0}>
            <PaymentsTab tenant={channel} />
          </TabPanel>

          {/* Reports Tab */}
          <TabPanel px={0}>
            <ReportsTab tenant={channel} />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  );
};

export default WebshopManagementPage;
