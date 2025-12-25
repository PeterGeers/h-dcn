import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Heading, Button, Table, Thead, Tbody, Tr, Th, Td,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  useDisclosure, useToast, Badge, Text, NumberInput, NumberInputField, Select
} from '@chakra-ui/react';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { FormControl, FormLabel, Input, Textarea } from '@chakra-ui/react';
import { getAuthHeaders, getAuthHeadersForGet } from '../utils/authHeaders';
import { FunctionGuard } from '../components/common/FunctionGuard';
import { getUserRoles } from '../utils/functionPermissions';

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

interface FormValues {
  name: string;
  description: string;
  price: number;
  duration_months: number;
  status: string;
  betalingsfrequentie: string;
  kortingen: string;
  betaalmethode_toegestaan: string;
  toegang_activiteiten: string;
  stemrecht: string;
  toegang_documenten: string;
  vrijwilligersmogelijkheden: string;
  toegang_webshop: string;
  leeftijdsgrens: string;
  vereisten: string;
  startdatum: string;
  einddatum: string;
  automatische_verlenging: string;
  opzegtermijn: string;
  promotie_informatie?: string;
  welkomstpakket?: string;
  clubblad_standaard?: string;
}

const validationSchema = Yup.object({
  name: Yup.string().required('Naam is verplicht'),
  description: Yup.string().required('Beschrijving is verplicht'),
  price: Yup.number().min(0, 'Prijs moet positief zijn').required('Prijs is verplicht'),
  duration_months: Yup.number().min(1, 'Duur moet minimaal 1 maand zijn').required('Duur is verplicht'),
  status: Yup.string().required('Status is verplicht')
});

function MembershipManagement({ user }: MembershipManagementProps) {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingMembership, setEditingMembership] = useState<Membership | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  // Check if user has Members_CRUD_All role
  const userRoles = getUserRoles(user);
  const hasMembersCRUDRole = userRoles.includes('Members_CRUD_All');

  // If user doesn't have the required role, show access denied message
  if (!hasMembersCRUDRole) {
    return (
      <Box p={6} bg="black" minH="100vh" textAlign="center">
        <VStack spacing={6}>
          <Heading color="red.400">Toegang Geweigerd</Heading>
          <Text color="white" fontSize="lg">
            Je hebt geen toegang tot het lidmaatschap beheer.
          </Text>
          <Text color="gray.400">
            Deze functionaliteit is alleen beschikbaar voor gebruikers met de Members_CRUD_All rol.
          </Text>
          <Text color="gray.400" fontSize="sm">
            Neem contact op met een beheerder als je denkt dat je toegang zou moeten hebben.
          </Text>
        </VStack>
      </Box>
    );
  }

  useEffect(() => {
    loadMemberships();
  }, []);

  const loadMemberships = async () => {
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/memberships`, {
        headers
      });
      if (response.ok) {
        const data = await response.json();
        // Map backend field names back to frontend expected names
        const mappedData = data.map(item => ({
          ...item,
          name: item.membership_name || item.name,
          status: item.membership_status || item.status
        }));
        setMemberships(mappedData);
      }
    } catch (error) {
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

  const handleSave = async (values: FormValues, { setSubmitting }: { setSubmitting: (isSubmitting: boolean) => void }) => {
    // Check if user has write permissions before attempting to save
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
      console.log('🔍 editingMembership object:', editingMembership);
      
      const membershipId = editingMembership?.membership_type_id;
      console.log('🔍 Using membership ID:', membershipId);
      
      const url = editingMembership 
        ? `${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/memberships/${membershipId}`
        : `${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/memberships`;
      
      const method = editingMembership ? 'PUT' : 'POST';
      
      const payload: any = {
        ...values
      };
      
      // Handle DynamoDB reserved keywords
      if (payload.name) {
        payload.membership_name = payload.name;
        delete payload.name;
      }
      if (payload.status) {
        payload.membership_status = payload.status;
        delete payload.status;
      }
      
      console.log('🔍 Membership API call:', { method, url, payload });
      
      const headers = await getAuthHeaders();
      const response = await fetch(url, {
        method,
        headers,
        body: JSON.stringify(payload)
      });
      
      console.log('🔍 Response status:', response.status);

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
        console.error('🚫 API Error:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
    } catch (error) {
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
    // Check if user has write permissions before attempting to delete
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
          `${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/memberships/${membership.membership_id || membership.id}`,
          { 
            method: 'DELETE',
            headers
          }
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
      } catch (error) {
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
    // Check if user has write permissions before opening modal
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
              fallback={null}
            >
              <Button colorScheme="orange" onClick={() => openModal()}>
                + Nieuw Lidmaatschap
              </Button>
            </FunctionGuard>
          </HStack>

          <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
            <Table variant="simple">
              <Thead bg="gray.700">
                <Tr>
                  <Th color="orange.300">Naam</Th>
                  <Th color="orange.300">Beschrijving</Th>
                  <Th color="orange.300">Prijs</Th>
                  <Th color="orange.300">Duur (maanden)</Th>
                  <Th color="orange.300">Acties</Th>
                </Tr>
              </Thead>
              <Tbody>
                {memberships.map((membership) => (
                  <Tr key={membership.membership_id || membership.id}>
                    <Td color="white" fontWeight="bold">{membership.name}</Td>
                    <Td color="white">{membership.description}</Td>
                    <Td color="white">€{membership.price}</Td>
                    <Td color="white">{membership.duration_months}</Td>
                    <Td>
                      <HStack spacing={2}>
                        <FunctionGuard 
                          user={user} 
                          functionName="memberships" 
                          action="write"
                          fallback={
                            <Text color="gray.500" fontSize="sm">
                              Alleen lezen
                            </Text>
                          }
                        >
                          <Button
                            size="sm"
                            colorScheme="blue"
                            onClick={() => openModal(membership)}
                          >
                            Bewerk
                          </Button>
                        </FunctionGuard>
                        <FunctionGuard 
                          user={user} 
                          functionName="memberships" 
                          action="write"
                          fallback={null}
                        >
                          <Button
                            size="sm"
                            colorScheme="red"
                            onClick={() => handleDelete(membership)}
                          >
                            Verwijder
                          </Button>
                        </FunctionGuard>
                      </HStack>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>

          {memberships.length === 0 && (
            <Text textAlign="center" color="gray.400" py={8}>
              Geen lidmaatschappen gevonden
            </Text>
          )}
        </VStack>

        {/* Modal */}
        <Modal isOpen={isOpen} onClose={onClose} size="lg">
          <ModalOverlay />
          <ModalContent bg="gray.800" borderColor="orange.400" border="1px">
            <ModalHeader color="orange.400">
              {editingMembership ? 'Lidmaatschap Bewerken' : 'Nieuw Lidmaatschap'}
            </ModalHeader>
            <Formik
              initialValues={{
                name: editingMembership?.name || '',
                description: editingMembership?.description || '',
                price: editingMembership?.price || 0,
                duration_months: editingMembership?.duration_months || 12,
                status: editingMembership?.status || 'actief',
                betalingsfrequentie: editingMembership?.betalingsfrequentie || 'jaarlijks',
                kortingen: editingMembership?.kortingen || 'geen',
                betaalmethode_toegestaan: editingMembership?.betaalmethode_toegestaan || 'automatische incasso',
                toegang_activiteiten: editingMembership?.toegang_activiteiten || 'alle evenementen',
                stemrecht: editingMembership?.stemrecht || 'ja',
                toegang_documenten: editingMembership?.toegang_documenten || 'ja',
                vrijwilligersmogelijkheden: editingMembership?.vrijwilligersmogelijkheden || 'ja',
                toegang_webshop: editingMembership?.toegang_webshop || 'ja',
                leeftijdsgrens: editingMembership?.leeftijdsgrens || 'geen',
                vereisten: editingMembership?.vereisten || 'geen',
                startdatum: editingMembership?.startdatum || new Date().toISOString().split('T')[0],
                einddatum: editingMembership?.einddatum || '',
                automatische_verlenging: editingMembership?.automatische_verlenging || 'ja',
                opzegtermijn: editingMembership?.opzegtermijn || '1 maand',
                promotie_informatie: editingMembership?.promotie_informatie || 'zichtbaar op website',
                welkomstpakket: editingMembership?.welkomstpakket || 'ja',
                clubblad_standaard: editingMembership?.clubblad_standaard || 'Digitaal'
              }}
              validationSchema={validationSchema}
              onSubmit={handleSave}
              enableReinitialize={true}
            >
              {({ errors, touched, isSubmitting }) => (
                <Form>
                  <ModalBody maxH="70vh" overflowY="auto">
                    <VStack spacing={4}>
                      {/* Algemene kenmerken */}
                      <Heading size="sm" color="orange.400" alignSelf="start">Algemene Kenmerken</Heading>
                      
                      <Field name="name">
                        {({ field }) => (
                          <FormControl isInvalid={errors.name && touched.name}>
                            <FormLabel color="orange.300">Naam</FormLabel>
                            <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                            {errors.name && touched.name && (
                              <Text color="red.400" fontSize="sm">{errors.name}</Text>
                            )}
                          </FormControl>
                        )}
                      </Field>

                      <Field name="description">
                        {({ field }) => (
                          <FormControl isInvalid={errors.description && touched.description}>
                            <FormLabel color="orange.300">Beschrijving</FormLabel>
                            <Textarea {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                            {errors.description && touched.description && (
                              <Text color="red.400" fontSize="sm">{errors.description}</Text>
                            )}
                          </FormControl>
                        )}
                      </Field>

                      <Field name="status">
                        {({ field }) => (
                          <FormControl isInvalid={errors.status && touched.status}>
                            <FormLabel color="orange.300">Status</FormLabel>
                            <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                              <option value="actief">Actief</option>
                              <option value="gearchiveerd">Gearchiveerd</option>
                              <option value="tijdelijk">Tijdelijk</option>
                            </Select>
                            {errors.status && touched.status && (
                              <Text color="red.400" fontSize="sm">{errors.status}</Text>
                            )}
                          </FormControl>
                        )}
                      </Field>

                      {/* Financiële attributen */}
                      <Heading size="sm" color="orange.400" alignSelf="start" mt={4}>Financiële Attributen</Heading>
                      
                      <HStack spacing={4} width="100%">
                        <Field name="price">
                          {({ field }) => (
                            <FormControl isInvalid={errors.price && touched.price}>
                              <FormLabel color="orange.300">Contributiebedrag (€)</FormLabel>
                              <NumberInput min={0}>
                                <NumberInputField 
                                  {...field} 
                                  bg="gray.200" 
                                  color="black" 
                                  focusBorderColor="orange.400" 
                                />
                              </NumberInput>
                              {errors.price && touched.price && (
                                <Text color="red.400" fontSize="sm">{errors.price}</Text>
                              )}
                            </FormControl>
                          )}
                        </Field>

                        <Field name="duration_months">
                          {({ field }) => (
                            <FormControl isInvalid={errors.duration_months && touched.duration_months}>
                              <FormLabel color="orange.300">Duur (maanden)</FormLabel>
                              <NumberInput min={1}>
                                <NumberInputField 
                                  {...field} 
                                  bg="gray.200" 
                                  color="black" 
                                  focusBorderColor="orange.400" 
                                />
                              </NumberInput>
                              {errors.duration_months && touched.duration_months && (
                                <Text color="red.400" fontSize="sm">{errors.duration_months}</Text>
                              )}
                            </FormControl>
                          )}
                        </Field>
                      </HStack>

                      <HStack spacing={4} width="100%">
                        <Field name="betalingsfrequentie">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Betalingsfrequentie</FormLabel>
                              <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                                <option value="maandelijks">Maandelijks</option>
                                <option value="per kwartaal">Per kwartaal</option>
                                <option value="jaarlijks">Jaarlijks</option>
                              </Select>
                            </FormControl>
                          )}
                        </Field>

                        <Field name="kortingen">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Kortingen</FormLabel>
                              <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" placeholder="bijv. studentenkorting" />
                            </FormControl>
                          )}
                        </Field>
                      </HStack>

                      <Field name="betaalmethode_toegestaan">
                        {({ field }) => (
                          <FormControl>
                            <FormLabel color="orange.300">Betaalmethode Toegestaan</FormLabel>
                            <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                              <option value="automatische incasso">Automatische incasso</option>
                              <option value="factuur">Factuur</option>
                              <option value="online betaling">Online betaling</option>
                            </Select>
                          </FormControl>
                        )}
                      </Field>

                      {/* Toegangsrechten */}
                      <Heading size="sm" color="orange.400" alignSelf="start" mt={4}>Toegangsrechten</Heading>
                      
                      <HStack spacing={4} width="100%">
                        <Field name="toegang_activiteiten">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Toegang Activiteiten</FormLabel>
                              <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" placeholder="alle evenementen" />
                            </FormControl>
                          )}
                        </Field>

                        <Field name="stemrecht">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Stemrecht</FormLabel>
                              <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                                <option value="ja">Ja</option>
                                <option value="nee">Nee</option>
                              </Select>
                            </FormControl>
                          )}
                        </Field>
                      </HStack>

                      <HStack spacing={4} width="100%">
                        <Field name="toegang_documenten">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Toegang Documenten</FormLabel>
                              <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                                <option value="ja">Ja</option>
                                <option value="nee">Nee</option>
                              </Select>
                            </FormControl>
                          )}
                        </Field>

                        <Field name="vrijwilligersmogelijkheden">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Vrijwilligersmogelijkheden</FormLabel>
                              <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                                <option value="ja">Ja</option>
                                <option value="nee">Nee</option>
                              </Select>
                            </FormControl>
                          )}
                        </Field>
                      </HStack>

                      <Field name="toegang_webshop">
                        {({ field }) => (
                          <FormControl>
                            <FormLabel color="orange.300">Toegang Webshop</FormLabel>
                            <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                              <option value="ja">Ja</option>
                              <option value="nee">Nee</option>
                            </Select>
                          </FormControl>
                        )}
                      </Field>

                      {/* Doelgroep */}
                      <Heading size="sm" color="orange.400" alignSelf="start" mt={4}>Doelgroep</Heading>
                      
                      <HStack spacing={4} width="100%">
                        <Field name="leeftijdsgrens">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Leeftijdsgrens</FormLabel>
                              <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" placeholder="bijv. < 25 jaar" />
                            </FormControl>
                          )}
                        </Field>

                        <Field name="vereisten">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Vereisten</FormLabel>
                              <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" placeholder="bijv. Harley-Davidson motor" />
                            </FormControl>
                          )}
                        </Field>
                      </HStack>

                      {/* Administratieve attributen */}
                      <Heading size="sm" color="orange.400" alignSelf="start" mt={4}>Administratieve Attributen</Heading>
                      
                      <HStack spacing={4} width="100%">
                        <Field name="startdatum">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Startdatum</FormLabel>
                              <Input {...field} type="date" bg="gray.200" color="black" focusBorderColor="orange.400" />
                            </FormControl>
                          )}
                        </Field>

                        <Field name="einddatum">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Einddatum (optioneel)</FormLabel>
                              <Input {...field} type="date" bg="gray.200" color="black" focusBorderColor="orange.400" />
                            </FormControl>
                          )}
                        </Field>
                      </HStack>

                      <HStack spacing={4} width="100%">
                        <Field name="automatische_verlenging">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Automatische Verlenging</FormLabel>
                              <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                                <option value="ja">Ja</option>
                                <option value="nee">Nee</option>
                              </Select>
                            </FormControl>
                          )}
                        </Field>

                        <Field name="opzegtermijn">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Opzegtermijn</FormLabel>
                              <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" placeholder="bijv. 1 maand" />
                            </FormControl>
                          )}
                        </Field>
                      </HStack>

                      {/* Communicatie en marketing */}
                      <Heading size="sm" color="orange.400" alignSelf="start" mt={4}>Communicatie en Marketing</Heading>
                      
                      <Field name="promotie_informatie">
                        {({ field }) => (
                          <FormControl>
                            <FormLabel color="orange.300">Promotie Informatie</FormLabel>
                            <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" placeholder="bijv. zichtbaar op website" />
                          </FormControl>
                        )}
                      </Field>

                      <HStack spacing={4} width="100%">
                        <Field name="welkomstpakket">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Welkomstpakket</FormLabel>
                              <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                                <option value="ja">Ja</option>
                                <option value="nee">Nee</option>
                              </Select>
                            </FormControl>
                          )}
                        </Field>

                        <Field name="clubblad_standaard">
                          {({ field }) => (
                            <FormControl>
                              <FormLabel color="orange.300">Clubblad Standaard</FormLabel>
                              <Select {...field} bg="gray.200" color="black" focusBorderColor="orange.400">
                                <option value="Digitaal">Digitaal</option>
                                <option value="Papier">Papier</option>
                                <option value="Nee">Nee</option>
                              </Select>
                            </FormControl>
                          )}
                        </Field>
                      </HStack>
                    </VStack>
                  </ModalBody>
                  <ModalFooter>
                    <Button variant="ghost" mr={3} onClick={onClose}>
                      Annuleren
                    </Button>
                    <Button 
                      type="submit" 
                      colorScheme="orange" 
                      isLoading={isSubmitting}
                    >
                      Opslaan
                    </Button>
                  </ModalFooter>
                </Form>
              )}
            </Formik>
          </ModalContent>
        </Modal>
      </Box>
    </FunctionGuard>
  );
}

export default MembershipManagement;