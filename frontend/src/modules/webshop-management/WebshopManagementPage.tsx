/**
 * WebshopManagementPage — Main page for the Webshop Management admin section.
 *
 * Features:
 * - Tab navigation: Producten, Bestellingen, Betalingen, Rapporten
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
} from '@chakra-ui/react';
import { ProductsTab } from './components/ProductsTab';
import { OrdersTab } from './components/OrdersTab';
import { PaymentsTab } from './components/PaymentsTab';
import { ReportsTab } from './components/ReportsTab';

const WebshopManagementPage: React.FC = () => {
  return (
    <Container maxW="container.xl" py={6}>
      <Heading size="lg" color="orange.400" mb={6}>
        Webshop Beheer
      </Heading>

      <Tabs colorScheme="orange" variant="enclosed">
        <TabList>
          <Tab>Producten</Tab>
          <Tab>Bestellingen</Tab>
          <Tab>Betalingen</Tab>
          <Tab>Rapporten</Tab>
        </TabList>

        <TabPanels>
          {/* Products Tab — displays ALL products in single interface */}
          <TabPanel px={0}>
            <ProductsTab />
          </TabPanel>

          {/* Orders Tab */}
          <TabPanel px={0}>
            <OrdersTab />
          </TabPanel>

          {/* Payments Tab */}
          <TabPanel px={0}>
            <PaymentsTab />
          </TabPanel>

          {/* Reports Tab */}
          <TabPanel px={0}>
            <ReportsTab />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  );
};

export default WebshopManagementPage;
