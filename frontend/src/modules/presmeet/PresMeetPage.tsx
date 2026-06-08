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
  Flex,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthProvider';
import { usePresMeetBooking } from './hooks/usePresMeetBooking';
import BookingForm from './components/BookingForm';
import BookingOverview from './components/BookingOverview';
import AdminDashboard from './components/AdminDashboard';
import OnboardingFlow from './components/OnboardingFlow';
import ClubLogoUploader from './components/ClubLogoUploader';

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

/**
 * Check if user has logo upload admin rights.
 * Only requires Products_CRUD or Webshop_Management role (no region needed).
 */
function isLogoUploadAdmin(groups: string[]): boolean {
  return groups.some((g) =>
    ['Products_CRUD', 'Webshop_Management'].includes(g)
  );
}

const PresMeetPage: React.FC = () => {
  const { t } = useTranslation('presmeet');
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
  } = usePresMeetBooking();

  const userGroups = user?.groups ?? [];
  const isAdmin = isPresMeetAdmin(userGroups);
  const isLogoAdmin = isLogoUploadAdmin(userGroups);
  const clubId = booking?.club_id;

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
            <AlertTitle>{t('page.error_loading')}</AlertTitle>
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
          {t('page.title')}
        </Heading>
        <OnboardingFlow onComplete={handleOnboardingComplete} />
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={6}>
      <Flex align="center" gap={3} mb={6}>
        {clubId && (
          <ClubLogoUploader clubId={clubId} isAdmin={isLogoAdmin} />
        )}
        <Heading size="lg" color="orange.400">
          {t('page.title_booking')}
        </Heading>
      </Flex>

      {error && (
        <Alert status="warning" mb={4} borderRadius="md">
          <AlertIcon />
          <Text>{error}</Text>
        </Alert>
      )}

      <Tabs colorScheme="orange" variant="enclosed">
        <TabList>
          <Tab>{t('page.tab_booking')}</Tab>
          <Tab>{t('page.tab_overview')}</Tab>
          {isAdmin && <Tab>{t('page.tab_admin')}</Tab>}
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
              paymentStatus={booking?.payment_status ?? 'unpaid'}
              totalPaid={0}
              clubName={booking?.club_id ?? ''}
              clubId={booking?.club_id ?? ''}
              submittedAt={booking?.submitted_at ?? null}
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
