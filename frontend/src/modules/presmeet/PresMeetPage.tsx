/**
 * PresMeetPage — Main page for the PresMeet booking module.
 *
 * Features:
 * - Tab navigation: Booking, Overview, Admin
 * - Admin tab only visible to webmaster role (System_User_Management)
 * - Uses usePresMeetBooking hook for state management
 * - Uses useAuth from AuthProvider context for user role detection
 *
 * Validates: Requirements 3.1, 3.4, 3.8, 7.7
 */

import React from 'react';
import {
  Box,
  Container,
  Heading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Spinner,
  Center,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Text,
} from '@chakra-ui/react';
import { useAuth } from '../../context/AuthProvider';
import { usePresMeetBooking } from './hooks/usePresMeetBooking';
import BookingForm from './components/BookingForm';
import BookingOverview from './components/BookingOverview';
import AdminDashboard from './components/AdminDashboard';

/**
 * Check if the user has admin/webmaster access for the PresMeet admin tab.
 * Admins are users with System_User_Management or Products_CRUD role.
 */
function isPresMeetAdmin(groups: string[]): boolean {
  return groups.some(
    (g) => g === 'System_User_Management' || g === 'Products_CRUD'
  );
}

const PresMeetPage: React.FC = () => {
  const { user } = useAuth();
  const {
    config,
    booking,
    formData,
    productTypes,
    isLoading,
    error,
    loadBooking,
    saveBooking,
    submitBooking,
  } = usePresMeetBooking();

  const userGroups = user?.groups ?? [];
  const isAdmin = isPresMeetAdmin(userGroups);

  if (isLoading) {
    return (
      <Center h="300px">
        <Spinner size="xl" color="orange.400" />
      </Center>
    );
  }

  if (error && !config) {
    return (
      <Container maxW="container.lg" py={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Error loading PresMeet</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={6}>
      <Heading size="lg" color="orange.400" mb={6}>
        Presidents' Meeting Booking
      </Heading>

      {error && (
        <Alert status="warning" mb={4} borderRadius="md">
          <AlertIcon />
          <Text>{error}</Text>
        </Alert>
      )}

      <Tabs colorScheme="orange" variant="enclosed">
        <TabList>
          <Tab>Booking</Tab>
          <Tab>Overview</Tab>
          {isAdmin && <Tab>Admin</Tab>}
        </TabList>

        <TabPanels>
          {/* Booking Form Tab */}
          <TabPanel px={0}>
            <BookingForm
              config={productTypes}
              eventStartDate={config?.event?.start_date}
              eventEndDate={config?.event?.end_date}
              existingBooking={booking}
              initialFormData={formData}
              onSaved={loadBooking}
              onSubmitted={loadBooking}
            />
          </TabPanel>

          {/* Overview Tab */}
          <TabPanel px={0}>
            <BookingOverview
              items={booking?.items ?? []}
              status={booking?.status ?? 'draft'}
              totalPaid={0}
            />
          </TabPanel>

          {/* Admin Tab (conditionally rendered) */}
          {isAdmin && (
            <TabPanel px={0}>
              <AdminDashboard isAdmin={isAdmin} />
            </TabPanel>
          )}
        </TabPanels>
      </Tabs>
    </Container>
  );
};

export default PresMeetPage;
