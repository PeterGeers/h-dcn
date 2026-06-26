import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Heading, Button, Text,
  useDisclosure, useToast
} from '@chakra-ui/react';
import { getAuthHeaders, getAuthHeadersForGet } from '../utils/authHeaders';
import { FunctionGuard } from '../components/common/FunctionGuard';
import { checkUIPermission } from '../utils/functionPermissions';
import { MembershipTable } from '../modules/members/components/MembershipTable';
import { MembershipFormModal, MembershipFormValues } from '../modules/members/components/MembershipFormModal';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
  };
}

interface MembershipManagementProps {
  user: User;
}

interface Membership {
  membership_id?: string;
  membership_type_id?: string;
  id?: string;
  name?: string;
  membership_name?: string;
  description?: string;
  price?: number;
  duration_months?: number;
  status?: string;
  membership_status?: string;
  betalingsfrequentie?: string;
  kortingen?: string;
  betaalmethode_toegestaan?: string;
  toegang_activiteiten?: string;
  stemrecht?: string;
  toegang_documenten?: string;
  vrijwilligersmogelijkheden?: string;
  toegang_webshop?: string;
  leeftijdsgrens?: string;
  vereisten?: string;
  startdatum?: string;
  einddatum?: string;
  automatische_verlenging?: string;
  opzegtermijn?: string;
  promotie_informatie?: string;
  welkomstpakket?: string;
  clubblad_standaard?: string;
}

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

function MembershipManagement({ user }: MembershipManagementProps) {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingMembership, setEditingMembership] = useState<Membership | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  // Check if user has Members_CRUD permissions with any region
  const hasMembersCRUDRole = checkUIPermission(user, 'members', 'write');

  useEffect(() => {
    if (hasMembersCRUDRole) {
      loadMemberships();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMembersCRUDRole]);

  // If user doesn't have the required permission, show access denied message
  if (!hasMembersCRUDRole) {
    return (
      <Box p={6} bg="black" minH="100vh" textAlign="center">
        <VStack spacing={6}>
          <Heading color="red.400">Toegang Geweigerd</Heading>
          <Text color="white" fontSize="lg">
            Je hebt geen toegang tot het lidmaatschap beheer.
          </Text>
          <Text color="gray.400">
            Deze functionaliteit is alleen beschikbaar voor gebruikers met Members_CRUD permissies en een regionale toewijzing.
          </Text>
          <Text color="gray.400" fontSize="sm">
            Neem contact op met een beheerder als je denkt dat je toegang zou moeten hebben.
          </Text>
        </VStack>
      </Box>
    );
  }

  const loadMemberships = async () => {
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(`${API_BASE_URL}/memberships`, { headers });
      if (response.ok) {
        const data = await response.json();
        // Map backend field names back to frontend expected names
        const mappedData = data.map((item: Membership) => ({
          ...item,
          name: item.membership_name || item.name,
          status: item.membership_status || item.status
        }));
        setMemberships(mappedData);
      }
    } catch (error: any) {
      toast({
        title: 'Fout bij laden lidmaatschappen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: MembershipFormValues, { setSubmitting }: { setSubmitting: (isSubmitting: boolean) => void }) => {
    if (!hasMembersCRUDRole) {
      toast({
        title: 'Toegang geweigerd',
        description: 'Je hebt geen rechten om lidmaatschappen te wijzigen.',
        status: 'error',
        duration: 5000,
      });
      setSubmitting(false);
      return;
    }

    try {
      const membershipId = editingMembership?.membership_type_id;
      const url = editingMembership 
        ? `${API_BASE_URL}/memberships/${membershipId}`
        : `${API_BASE_URL}/memberships`;
      const method = editingMembership ? 'PUT' : 'POST';
      
      const payload: any = { ...values };
      
      // Handle DynamoDB reserved keywords
      if (payload.name) {
        payload.membership_name = payload.name;
        delete payload.name;
      }
      if (payload.status) {
        payload.membership_status = payload.status;
        delete payload.status;
      }
      
      const headers = await getAuthHeaders();
      const response = await fetch(url, {
        method,
        headers,
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        await loadMemberships();
        onClose();
        setEditingMembership(null);
        toast({
          title: editingMembership ? 'Lidmaatschap bijgewerkt' : 'Lidmaatschap aangemaakt',
          status: 'success',
          duration: 3000,
        });
      } else {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
    } catch (error: any) {
      toast({
        title: 'Fout bij opslaan',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (membership: Membership) => {
    if (!hasMembersCRUDRole) {
      toast({
        title: 'Toegang geweigerd',
        description: 'Je hebt geen rechten om lidmaatschappen te verwijderen.',
        status: 'error',
        duration: 5000,
      });
      return;
    }

    if (window.confirm(`Weet je zeker dat je "${membership.name}" wilt verwijderen?`)) {
      try {
        const headers = await getAuthHeadersForGet();
        const response = await fetch(
          `${API_BASE_URL}/memberships/${membership.membership_id || membership.id}`,
          { method: 'DELETE', headers }
        );

        if (response.ok) {
          await loadMemberships();
          toast({
            title: 'Lidmaatschap verwijderd',
            status: 'success',
            duration: 3000,
          });
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error: any) {
        toast({
          title: 'Fout bij verwijderen',
          description: error.message,
          status: 'error',
          duration: 5000,
        });
      }
    }
  };

  const openModal = (membership: Membership | null = null) => {
    if (!hasMembersCRUDRole) {
      toast({
        title: 'Toegang geweigerd',
        description: 'Je hebt geen rechten om lidmaatschappen te bewerken.',
        status: 'error',
        duration: 5000,
      });
      return;
    }
    setEditingMembership(membership);
    onOpen();
  };

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Text color="orange.400">Lidmaatschappen laden...</Text>
      </Box>
    );
  }

  return (
    <FunctionGuard 
      user={user} 
      functionName="memberships" 
      action="read"
      requiredRoles={['Members_CRUD']}
      fallback={
        <Box p={6} bg="black" minH="100vh" textAlign="center">
          <VStack spacing={6}>
            <Heading color="red.400">Toegang Geweigerd</Heading>
            <Text color="white" fontSize="lg">
              Je hebt geen toegang tot het lidmaatschap beheer.
            </Text>
            <Text color="gray.400">
              Deze functionaliteit is alleen beschikbaar voor geautoriseerde gebruikers.
            </Text>
            <Text color="gray.400" fontSize="sm">
              Neem contact op met een beheerder als je denkt dat je toegang zou moeten hebben.
            </Text>
          </VStack>
        </Box>
      }
    >
      <Box p={6} bg="black" minH="100vh">
        <VStack spacing={6} align="stretch">
          <HStack justify="space-between">
            <Heading color="orange.400">Lidmaatschap Beheer</Heading>
            <FunctionGuard 
              user={user} 
              functionName="memberships" 
              action="write"
              requiredRoles={['Members_CRUD']}
              fallback={null}
            >
              <Button colorScheme="orange" onClick={() => openModal()}>
                + Nieuw Lidmaatschap
              </Button>
            </FunctionGuard>
          </HStack>

          <MembershipTable
            user={user}
            memberships={memberships}
            onEdit={openModal}
            onDelete={handleDelete}
          />
        </VStack>

        <MembershipFormModal
          isOpen={isOpen}
          onClose={onClose}
          editingMembership={editingMembership}
          onSave={handleSave}
        />
      </Box>
    </FunctionGuard>
  );
}

export default MembershipManagement;
