/**
 * WebshopManagementPage — Main page for the Webshop Management admin section.
 *
 * Features:
 * - Tab navigation: Producten, Bestellingen, Betalingen, Rapporten
 * - Shared event filter state via useEventFilter hook
 * - Independent of event booking registry flow (no registry_row dependency)
 * - Accessible to users with Products_CRUD, Products_Read, or Products_Export roles
 *
 * Validates: Requirements 1.3, 1.7, 8.1, 8.2, 10.5, 12.6, 12.10
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
import { EventFilter } from './components/EventFilter';
import { ProductsTab } from './components/ProductsTab';
import { OrdersTab } from './components/OrdersTab';
import { PaymentsTab } from './components/PaymentsTab';
import { ReportsTab } from './components/ReportsTab';
import { useEventFilter } from './hooks/useEventFilter';

const WebshopManagementPage: React.FC = () => {
  const { eventFilter, setEventFilter, events, loadingEvents } = useEventFilter();

  return (
    <Container maxW="container.xl" py={6}>
      <HStack justify="space-between" align="center" mb={6}>
        <Heading size="lg" color="orange.400">
          Webshop Beheer
        </Heading>
        <EventFilter
          value={eventFilter}
          onChange={setEventFilter}
          events={events}
          loading={loadingEvents}
        />
      </HStack>

      <Tabs colorScheme="orange" variant="enclosed">
        <TabList>
          <Tab>Producten</Tab>
          <Tab>Bestellingen</Tab>
          <Tab>Betalingen</Tab>
          <Tab>Rapporten</Tab>
        </TabList>

        <TabPanels>
          {/* Products Tab — displays ALL products in single interface, filtered by event */}
          <TabPanel px={0}>
            <ProductsTab eventFilter={eventFilter} />
          </TabPanel>

          {/* Orders Tab */}
          <TabPanel px={0}>
            <OrdersTab eventFilter={eventFilter} />
          </TabPanel>

          {/* Payments Tab */}
          <TabPanel px={0}>
            <PaymentsTab eventFilter={eventFilter} />
          </TabPanel>

          {/* Reports Tab */}
          <TabPanel px={0}>
            <ReportsTab eventFilter={eventFilter} />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  );
};

export default WebshopManagementPage;
