import React from 'react';
import {
  VStack, HStack, Heading, Button, Box,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  Text, NumberInput, NumberInputField, Select
} from '@chakra-ui/react';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { FormControl, FormLabel, Input, Textarea } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { getValidationMessage } from '../../../utils/validationMessages';

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

export interface MembershipFormValues {
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

function useValidationSchema() {
  const { t } = useTranslation('members');
  return Yup.object({
    name: Yup.string()
      .required(() => getValidationMessage(t, 'required', { field: t('form.name', { defaultValue: 'Naam' }) })),
    description: Yup.string()
      .required(() => getValidationMessage(t, 'required', { field: t('form.description', { defaultValue: 'Beschrijving' }) })),
    price: Yup.number()
      .min(0, () => getValidationMessage(t, 'min', { value: 0 }))
      .required(() => getValidationMessage(t, 'required', { field: t('form.price', { defaultValue: 'Prijs' }) })),
    duration_months: Yup.number()
      .min(1, () => getValidationMessage(t, 'min', { value: 1 }))
      .required(() => getValidationMessage(t, 'required', { field: t('form.duration', { defaultValue: 'Duur' }) })),
    status: Yup.string()
      .required(() => getValidationMessage(t, 'required', { field: t('form.status', { defaultValue: 'Status' }) })),
  });
}

interface MembershipFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  editingMembership: Membership | null;
  onSave: (values: MembershipFormValues, helpers: { setSubmitting: (isSubmitting: boolean) => void }) => void;
  onDelete?: (membership: Membership) => void;
}

export function MembershipFormModal({ isOpen, onClose, editingMembership, onSave, onDelete }: MembershipFormModalProps) {
  const validationSchema = useValidationSchema();
  return (
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
          onSubmit={onSave}
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
                      <FormControl isInvalid={!!(errors.name && touched.name)}>
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
                      <FormControl isInvalid={!!(errors.description && touched.description)}>
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
                      <FormControl isInvalid={!!(errors.status && touched.status)}>
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
                        <FormControl isInvalid={!!(errors.price && touched.price)}>
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
                        <FormControl isInvalid={!!(errors.duration_months && touched.duration_months)}>
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
              <ModalFooter justifyContent="space-between">
                {editingMembership && onDelete ? (
                  <Button
                    colorScheme="red"
                    variant="outline"
                    onClick={() => onDelete(editingMembership)}
                  >
                    Verwijderen
                  </Button>
                ) : <Box />}
                <HStack spacing={3}>
                  <Button variant="ghost" onClick={onClose}>
                    Annuleren
                  </Button>
                  <Button 
                    type="submit" 
                    colorScheme="orange" 
                    isLoading={isSubmitting}
                  >
                    Opslaan
                  </Button>
                </HStack>
              </ModalFooter>
            </Form>
          )}
        </Formik>
      </ModalContent>
    </Modal>
  );
}
