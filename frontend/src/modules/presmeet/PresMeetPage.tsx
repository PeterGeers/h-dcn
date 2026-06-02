/**
 * PresMeetPage — Main page for the PresMeet booking module.
 *
 * Features:
 * - Tab navigation: Booking, Overview, Admin
 * - Admin tab visible to users with management role + region role (v2 logic)
 * - Uses usePresMeetBooking hook for state management
 * - Uses useAuth from AuthProvider context for user role detection
 * - Shows OnboardingFlow if user has no club_id assigned
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 10.1, 10.2, 10.5
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
import OnboardingFlow from './components/OnboardingFlow';

/**
 * Check if the user has admin access for the PresMeet admin tab.
 * Requires BOTH a management role AND a region role:
 * - Management: Products_CRUD, Products_Read, or Webshop_Management
 * - Region: Regio_Pressmeet or Regio_All
 */
function isPresMeetAdmin(groups: string[]): boolean {
  const hasManagementRole = groups.some((g) =>
    ['Products_CRUD', 'Products_Read', 'Webshop_Management'].includes(g)
  );
  const hasRegionRole = groups.some((g) =>
    ['Regio_Pressmeet', 'Regio_All'].includes(g)
  );
  return hasManagementRole && hasRegionRole;
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
    needsOnboarding,
    loadBooking,
    reloadAll,
    saveBooking,
    submitBooking,
  } = usePresMeetBooking();

  const userGroups = user?.groups ?? [];
  const isAdmin = isPresMeetAdmin(userGroups);

  // Handle onboarding completion: reload all state to show the booking form
  const handleOnboardingComplete = async (_clubId: string) => {
    await reloadAll();
  };

  if (isLoading) {
    return (
      <Center h="300px">
        <Spinner size="xl" color="orange.400" />
      </Center>
    );
  }

  if (error && !config && !needsOnboarding) {
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

  // Show onboarding flow if user has no club_id assigned
  if (needsOnboarding) {
    return (
      <Container maxW="container.xl" py={6}>
        <Heading size="lg" color="orange.400" mb={6}>
          Presidents' Meeting
        </Heading>
        <OnboardingFlow onComplete={handleOnboardingComplete} />
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
