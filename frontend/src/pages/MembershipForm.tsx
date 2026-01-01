import React from 'react';
import {
  Box, VStack, HStack, Heading, Text, FormControl, FormLabel, Input, Select,
  Textarea, Checkbox, Button, Divider, Alert, AlertIcon, useToast, SimpleGrid
} from '@chakra-ui/react';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import ParameterSelect from '../components/common/ParameterSelect';
import { getAuthHeaders, getAuthHeadersForGet } from '../utils/authHeaders';
import { API_URLS } from '../config/api';
import { useErrorHandler, apiCall } from '../utils/errorHandler';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
  };
}

interface MembershipFormProps {
  user: User;
}

interface FormValues {
  email: string;
  achternaam: string;
  initialen: string;
  voornaam: string;
  tussenvoegsel?: string;
  straat: string;
  postcode: string;
  woonplaats: string;
  land: string;
  telefoon: string;
  geboortedatum: string;
  bankrekeningnummer: string;
  geslacht: string;
  regio: string;
  clubblad: string;
  lidmaatschap: string;
  motormerk?: string;
  motortype?: string;
  bouwjaar?: string;
  kenteken?: string;
  wiewatwaar: string;
  nieuwsbrief: string;
  ondertekeningsdatum: string;
  akkoord: boolean;
  minderjarigNaam?: string;
  minderjarigAkkoord?: boolean;
}

interface ExistingMember {
  member_id?: string;
  email?: string;
  voornaam?: string;
  achternaam?: string;
  initialen?: string;
  tussenvoegsel?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
  land?: string;
  telefoon?: string;
  phone?: string;
  geboortedatum?: string;
  bankrekeningnummer?: string;
  geslacht?: string;
  regio?: string;
  clubblad?: string;
  lidmaatschap?: string;
  membership_type?: string;
  motormerk?: string;
  motortype?: string;
  bouwjaar?: string;
  kenteken?: string;
  wiewatwaar?: string;
  nieuwsbrief?: string;
  ondertekeningsdatum?: string;
  akkoord?: boolean;
  minderjarigNaam?: string;
  minderjarigAkkoord?: boolean;
  status?: string;
  created_at?: string;
}

const validationSchema = Yup.object().shape({
  email: Yup.string().email('Ongeldig e-mailadres').required('Verplicht'),
  achternaam: Yup.string().required('Verplicht'),
  initialen: Yup.string().required('Verplicht'),
  voornaam: Yup.string().required('Verplicht'),
  straat: Yup.string().required('Verplicht'),
  postcode: Yup.string().required('Verplicht'),
  woonplaats: Yup.string().required('Verplicht'),
  land: Yup.string().required('Verplicht'),
  telefoon: Yup.string().required('Verplicht'),
  geboortedatum: Yup.date().required('Verplicht'),
  bankrekeningnummer: Yup.string()
    .required('Verplicht')
    .matches(/^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$/, 'Ongeldig IBAN nummer (bijv. NL91ABNA0417164300 of DE89370400440532013000)')
    .test('iban-checksum', 'Ongeldig IBAN nummer', function(value) {
      if (!value) return false;
      // IBAN checksum validation for all countries
      const rearranged = value.slice(4) + value.slice(0, 4);
      const numericString = rearranged.replace(/[A-Z]/g, char => (char.charCodeAt(0) - 55).toString());
      const remainder = numericString.split('').reduce((acc, digit) => (acc * 10 + parseInt(digit)) % 97, 0);
      return remainder === 1;
    }),
  geslacht: Yup.string().required('Verplicht'),
  regio: Yup.string().required('Verplicht'),
  clubblad: Yup.string().required('Verplicht'),
  lidmaatschap: Yup.string().required('Verplicht'),
  motormerk: Yup.string().when('lidmaatschap', {
    is: (val) => val === 'Gewoon lid' || val === 'Gezins lid',
    then: (schema) => schema.required('Verplicht'),
    otherwise: (schema) => schema
  }),
  motortype: Yup.string().when('lidmaatschap', {
    is: (val) => val === 'Gewoon lid' || val === 'Gezins lid',
    then: (schema) => schema.required('Verplicht'),
    otherwise: (schema) => schema
  }),
  bouwjaar: Yup.number().when('lidmaatschap', {
    is: (val) => val === 'Gewoon lid' || val === 'Gezins lid',
    then: (schema) => schema.required('Verplicht'),
    otherwise: (schema) => schema
  }),
  kenteken: Yup.string().when('lidmaatschap', {
    is: (val) => val === 'Gewoon lid' || val === 'Gezins lid',
    then: (schema) => schema.required('Verplicht'),
    otherwise: (schema) => schema
  }),
  wiewatwaar: Yup.string().required('Verplicht'),
  nieuwsbrief: Yup.string().required('Verplicht'),
  akkoord: Yup.boolean().oneOf([true], 'Je moet akkoord gaan'),
  ondertekeningsdatum: Yup.date().required('Verplicht'),
  minderjarigNaam: Yup.string().when('geboortedatum', {
    is: (val) => val && Math.floor((new Date().getTime() - new Date(val).getTime()) / (365.25 * 24 * 60 * 60 * 1000)) < 18,
    then: (schema) => schema.required('Naam ouder/verzorger is verplicht voor minderjarigen'),
    otherwise: (schema) => schema
  }),
  minderjarigAkkoord: Yup.boolean().when('geboortedatum', {
    is: (val) => val && Math.floor((new Date().getTime() - new Date(val).getTime()) / (365.25 * 24 * 60 * 60 * 1000)) < 18,
    then: (schema) => schema.oneOf([true], 'Akkoord van ouder/verzorger is verplicht'),
    otherwise: (schema) => schema
  })
});

function MembershipForm({ user }: MembershipFormProps) {
  const { handleError, handleSuccess } = useErrorHandler();
  const [existingMember, setExistingMember] = React.useState<ExistingMember | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const getInitialValues = (): FormValues => {
    if (existingMember) {
      return {
        // Use stored values or defaults
        email: existingMember.email || '',
        voornaam: existingMember.voornaam || '',
        achternaam: existingMember.achternaam || '',
        initialen: existingMember.initialen || '',
        tussenvoegsel: existingMember.tussenvoegsel || '',
        straat: existingMember.straat || '',
        postcode: existingMember.postcode || '',
        woonplaats: existingMember.woonplaats || '',
        land: existingMember.land || '',
        telefoon: existingMember.telefoon || existingMember.phone || '',
        geboortedatum: existingMember.geboortedatum || '',
        bankrekeningnummer: existingMember.bankrekeningnummer || '',
        geslacht: existingMember.geslacht || '',
        regio: existingMember.regio || '',
        clubblad: existingMember.clubblad || '',
        lidmaatschap: existingMember.lidmaatschap || existingMember.membership_type || '',
        motormerk: existingMember.motormerk || '',
        motortype: existingMember.motortype || '',
        bouwjaar: existingMember.bouwjaar || '',
        kenteken: existingMember.kenteken || '',
        wiewatwaar: existingMember.wiewatwaar || '',
        nieuwsbrief: existingMember.nieuwsbrief || '',
        ondertekeningsdatum: existingMember.ondertekeningsdatum || '',
        akkoord: existingMember.akkoord !== undefined ? existingMember.akkoord : true,
        minderjarigNaam: existingMember.minderjarigNaam || '',
        minderjarigAkkoord: existingMember.minderjarigAkkoord || false
      };
    }
    
    return {
      email: user?.attributes?.email || '', achternaam: '', initialen: '', voornaam: user?.attributes?.given_name || '', tussenvoegsel: '',
      straat: '', postcode: '', woonplaats: '', land: '', telefoon: '',
      geboortedatum: '', bankrekeningnummer: '', geslacht: '', regio: '',
      clubblad: '', lidmaatschap: '', motormerk: '', motortype: '', bouwjaar: '',
      kenteken: '', wiewatwaar: '', nieuwsbrief: '', ondertekeningsdatum: '',
      akkoord: false, minderjarigNaam: '', minderjarigAkkoord: false
    };
  };

  React.useEffect(() => {
    const checkExistingMembership = async () => {
      try {
        const headers = await getAuthHeadersForGet();
        const response = await fetch(API_URLS.members(), {
          headers
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const members = await response.json();
        const existing = members.find(m => m.email === user?.attributes?.email);
        setExistingMember(existing);
      } catch (error) {
        console.error('Error checking membership:', error);
        // Continue with null existingMember on error
        setExistingMember(null);
      } finally {
        setIsLoading(false);
      }
    };
    
    if (user?.attributes?.email) {
      checkExistingMembership();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  const handleSubmit = async (values: FormValues, { setSubmitting }: { setSubmitting: (isSubmitting: boolean) => void }) => {
    console.log('Form submission started with values:', values);
    try {
      // Send all form fields since backend now supports dynamic storage
      const payload = {
        name: values.voornaam + ' ' + values.achternaam,
        email: values.email,
        membership_type: values.lidmaatschap || 'Gewoon lid',
        address: `${values.straat}, ${values.postcode} ${values.woonplaats}, ${values.land}`,
        phone: values.telefoon,
        status: existingMember ? existingMember.status : 'Nieuwe aanmelding',
        ...values
      };
      
      // Remove motor fields if membership type doesn't require them
      if (values.lidmaatschap !== 'Gewoon lid' && values.lidmaatschap !== 'Gezins lid') {
        delete payload.motormerk;
        delete payload.motortype;
        delete payload.bouwjaar;
        delete payload.kenteken;
      }
      
      const url = existingMember 
        ? API_URLS.member(existingMember.member_id)
        : API_URLS.members();
      
      const method = existingMember ? 'PUT' : 'POST';
      
      console.log('Sending request:', { method, url, payload });

      const headers = await getAuthHeaders();
      const response = await fetch(url, {
        method,
        headers,
        body: JSON.stringify(payload)
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const result = await response.json();
      console.log('API Success:', result);

      
      handleSuccess(
        existingMember ? 'Je gegevens zijn succesvol bijgewerkt.' : 'Je aanmelding is succesvol opgeslagen.',
        existingMember ? 'Gegevens bijgewerkt' : 'Aanmelding verzonden'
      );
      
      // Refresh the existing member data after successful submission
      if (!existingMember) {
        // For new members, refetch to get the created member data
        setTimeout(async () => {
          try {
            const headers = await getAuthHeadersForGet();
            const response = await fetch(API_URLS.members(), {
              headers
            });
            const members = await response.json();
            const newMember = members.find(m => m.email === values.email);
            setExistingMember(newMember);
          } catch (error) {
            console.error('Error refreshing member data:', error);
          }
        }, 1000);
      }
      
    } catch (error) {
      console.error('Form submission error:', error);
      handleError({ status: 0, message: error.message }, 'verzenden aanmelding');
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <Box maxW="800px" mx="auto" p={6} bg="black" minH="100vh" textAlign="center">
        <Text color="orange.400">Gegevens laden...</Text>
      </Box>
    );
  }

  return (
    <Box maxW="800px" mx="auto" p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        <Heading color="orange.400">
          {existingMember ? 'Mijn Lidmaatschap Gegevens' : 'H-DCN Lidmaatschap Aanmelding'}
        </Heading>
        
        {existingMember && (
          <Alert status="info" bg="gray.800" color="orange.200" borderColor="orange.400">
            <AlertIcon color="orange.400" />
            <Text fontSize="sm">
              Je kunt je eigen gegevens hieronder bekijken en wijzigen.
            </Text>
          </Alert>
        )}
        
        {!existingMember && (
          <Alert status="info" bg="gray.800" color="orange.200" borderColor="orange.400">
            <AlertIcon color="orange.400" />
            <Box>
              <Text fontSize="sm">
                Met dit formulier kun je je aanmelden voor het lidmaatschap van de H-DCN (Harley-Davidson Club Nederland).
                Door je aan te melden verklaar je akkoord te gaan met de statuten en het huishoudelijk reglement.
              </Text>
            </Box>
          </Alert>
        )}

        <Formik
          initialValues={getInitialValues()}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
          enableReinitialize={true}
        >
          {({ errors, touched, isSubmitting, values }) => {
            // Check if user is under 18
            const isUnder18 = values.geboortedatum && 
              Math.floor((new Date().getTime() - new Date(values.geboortedatum).getTime()) / (365.25 * 24 * 60 * 60 * 1000)) < 18;
            
            return (
            <Form>
              <VStack spacing={4} align="stretch">
                
                <Heading size="md" color="orange.400">Persoonsgegevens</Heading>
                
                <HStack>
                  <Box flex="1" />
                  <Field name="email">
                    {({ field }) => (
                      <FormControl isInvalid={errors.email && touched.email} flex="1">
                        <FormLabel color="orange.300">E-mailadres *</FormLabel>
                        <Input {...field} type="email" bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.email && touched.email && <Text color="red.400" fontSize="sm">{errors.email}</Text>}
                      </FormControl>
                    )}
                  </Field>
                  <Box flex="1" />
                </HStack>

                <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                  <Field name="achternaam">
                    {({ field }) => (
                      <FormControl isInvalid={errors.achternaam && touched.achternaam}>
                        <FormLabel color="orange.300">Achternaam *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.achternaam && touched.achternaam && <Text color="red.400" fontSize="sm">{errors.achternaam}</Text>}
                      </FormControl>
                    )}
                  </Field>
                  
                  <Field name="initialen">
                    {({ field }) => (
                      <FormControl isInvalid={errors.initialen && touched.initialen}>
                        <FormLabel color="orange.300">Initialen *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.initialen && touched.initialen && <Text color="red.400" fontSize="sm">{errors.initialen}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="voornaam">
                    {({ field }) => (
                      <FormControl isInvalid={errors.voornaam && touched.voornaam}>
                        <FormLabel color="orange.300">Voornaam *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.voornaam && touched.voornaam && <Text color="red.400" fontSize="sm">{errors.voornaam}</Text>}
                      </FormControl>
                    )}
                  </Field>
                  
                  <Field name="tussenvoegsel">
                    {({ field }) => (
                      <FormControl>
                        <FormLabel color="orange.300">Tussenvoegsel</FormLabel>
                        <Input {...field} placeholder="indien van toepassing" bg="gray.200" color="black" focusBorderColor="orange.400" />
                      </FormControl>
                    )}
                  </Field>
                </SimpleGrid>

                <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                  <Field name="straat">
                    {({ field }) => (
                      <FormControl isInvalid={errors.straat && touched.straat}>
                        <FormLabel color="orange.300">Straat Huisnummer *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.straat && touched.straat && <Text color="red.400" fontSize="sm">{errors.straat}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="postcode">
                    {({ field }) => (
                      <FormControl isInvalid={errors.postcode && touched.postcode}>
                        <FormLabel color="orange.300">Postcode *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.postcode && touched.postcode && <Text color="red.400" fontSize="sm">{errors.postcode}</Text>}
                      </FormControl>
                    )}
                  </Field>
                  
                  <Field name="woonplaats">
                    {({ field }) => (
                      <FormControl isInvalid={errors.woonplaats && touched.woonplaats}>
                        <FormLabel color="orange.300">Woonplaats *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.woonplaats && touched.woonplaats && <Text color="red.400" fontSize="sm">{errors.woonplaats}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="land">
                    {({ field }) => (
                      <FormControl isInvalid={errors.land && touched.land}>
                        <FormLabel color="orange.300">Land *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.land && touched.land && <Text color="red.400" fontSize="sm">{errors.land}</Text>}
                      </FormControl>
                    )}
                  </Field>
                </SimpleGrid>

                <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                  <Field name="telefoon">
                    {({ field }) => (
                      <FormControl isInvalid={errors.telefoon && touched.telefoon}>
                        <FormLabel color="orange.300">Telefoonnummer *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.telefoon && touched.telefoon && <Text color="red.400" fontSize="sm">{errors.telefoon}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="geboortedatum">
                    {({ field }) => (
                      <FormControl isInvalid={errors.geboortedatum && touched.geboortedatum}>
                        <FormLabel color="orange.300">Geboortedatum *</FormLabel>
                        <Input {...field} type="date" bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.geboortedatum && touched.geboortedatum && <Text color="red.400" fontSize="sm">{errors.geboortedatum}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="geslacht">
                    {({ field }) => (
                      <FormControl isInvalid={errors.geslacht && touched.geslacht}>
                        <FormLabel color="orange.300">Geslacht *</FormLabel>
                        <ParameterSelect
                          category="Geslacht"
                          placeholder="Selecteer geslacht"
                          value={field.value}
                          onChange={field.onChange}
                          name={field.name}
                          bg="gray.200"
                          color="black"
                          focusBorderColor="orange.400"
                        />
                        {errors.geslacht && touched.geslacht && <Text color="red.400" fontSize="sm">{errors.geslacht}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="bankrekeningnummer">
                    {({ field }) => (
                      <FormControl isInvalid={errors.bankrekeningnummer && touched.bankrekeningnummer}>
                        <FormLabel color="orange.300">Bankrekening *</FormLabel>
                        <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.bankrekeningnummer && touched.bankrekeningnummer && <Text color="red.400" fontSize="sm">{errors.bankrekeningnummer}</Text>}
                      </FormControl>
                    )}
                  </Field>
                </SimpleGrid>

                <Divider borderColor="orange.400" />
                <Heading size="md" color="orange.400">Lidmaatschap Details</Heading>

                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                  <Field name="regio">
                    {({ field }) => (
                      <FormControl isInvalid={errors.regio && touched.regio}>
                        <FormLabel color="orange.300">Regio *</FormLabel>
                        <ParameterSelect
                          category="Regio"
                          placeholder="Selecteer regio"
                          value={field.value}
                          onChange={field.onChange}
                          name={field.name}
                          bg="gray.200"
                          color="black"
                          focusBorderColor="orange.400"
                        />
                        {errors.regio && touched.regio && <Text color="red.400" fontSize="sm">{errors.regio}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="clubblad">
                    {({ field }) => (
                      <FormControl isInvalid={errors.clubblad && touched.clubblad}>
                        <FormLabel color="orange.300">Clubblad *</FormLabel>
                        <ParameterSelect
                          category="Clubblad"
                          placeholder="Hoe wil je het clubblad ontvangen?"
                          value={field.value}
                          onChange={field.onChange}
                          name={field.name}
                          bg="gray.200"
                          color="black"
                          focusBorderColor="orange.400"
                        />
                        {errors.clubblad && touched.clubblad && <Text color="red.400" fontSize="sm">{errors.clubblad}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="lidmaatschap">
                    {({ field }) => (
                      <FormControl isInvalid={errors.lidmaatschap && touched.lidmaatschap}>
                        <FormLabel color="orange.300">Soort lidmaatschap *</FormLabel>
                        <ParameterSelect
                          category="Lidmaatschap"
                          placeholder="Selecteer lidmaatschap"
                          value={field.value}
                          onChange={field.onChange}
                          name={field.name}
                          bg="gray.200"
                          color="black"
                          focusBorderColor="orange.400"
                        />
                        {errors.lidmaatschap && touched.lidmaatschap && <Text color="red.400" fontSize="sm">{errors.lidmaatschap}</Text>}
                      </FormControl>
                    )}
                  </Field>
                </SimpleGrid>

                {(values.lidmaatschap === 'Gewoon lid' || values.lidmaatschap === 'Gezins lid') && (
                  <>
                    <Divider borderColor="orange.400" />
                    <Heading size="md" color="orange.400">Motor Gegevens</Heading>

                    <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                      <Field name="motormerk">
                        {({ field }) => (
                          <FormControl isInvalid={errors.motormerk && touched.motormerk}>
                            <FormLabel color="orange.300">Motormerk *</FormLabel>
                            <ParameterSelect
                              category="Motormerk"
                              placeholder="Selecteer motormerk"
                              value={field.value}
                              onChange={field.onChange}
                              name={field.name}
                              bg="gray.200"
                              color="black"
                              focusBorderColor="orange.400"
                            />
                            {errors.motormerk && touched.motormerk && <Text color="red.400" fontSize="sm">{errors.motormerk}</Text>}
                          </FormControl>
                        )}
                      </Field>

                      <Field name="motortype">
                        {({ field }) => (
                          <FormControl isInvalid={errors.motortype && touched.motortype}>
                            <FormLabel color="orange.300">Type motor *</FormLabel>
                            <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                            {errors.motortype && touched.motortype && <Text color="red.400" fontSize="sm">{errors.motortype}</Text>}
                          </FormControl>
                        )}
                      </Field>
                      
                      <Field name="bouwjaar">
                        {({ field }) => (
                          <FormControl isInvalid={errors.bouwjaar && touched.bouwjaar}>
                            <FormLabel color="orange.300">Bouwjaar *</FormLabel>
                            <Input {...field} type="number" bg="gray.200" color="black" focusBorderColor="orange.400" />
                            {errors.bouwjaar && touched.bouwjaar && <Text color="red.400" fontSize="sm">{errors.bouwjaar}</Text>}
                          </FormControl>
                        )}
                      </Field>

                      <Field name="kenteken">
                        {({ field }) => (
                          <FormControl isInvalid={errors.kenteken && touched.kenteken}>
                            <FormLabel color="orange.300">Kenteken *</FormLabel>
                            <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                            {errors.kenteken && touched.kenteken && <Text color="red.400" fontSize="sm">{errors.kenteken}</Text>}
                          </FormControl>
                        )}
                      </Field>
                    </SimpleGrid>
                  </>
                )}

                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  <Field name="wiewatwaar">
                    {({ field }) => (
                      <FormControl isInvalid={errors.wiewatwaar && touched.wiewatwaar}>
                        <FormLabel color="orange.300">Hoe heb je ons gevonden? *</FormLabel>
                        <ParameterSelect
                          category="WieWatWaar"
                          placeholder="Selecteer optie"
                          value={field.value}
                          onChange={field.onChange}
                          name={field.name}
                          bg="gray.200"
                          color="black"
                          focusBorderColor="orange.400"
                        />
                        {errors.wiewatwaar && touched.wiewatwaar && <Text color="red.400" fontSize="sm">{errors.wiewatwaar}</Text>}
                      </FormControl>
                    )}
                  </Field>

                  <Field name="nieuwsbrief">
                    {({ field }) => (
                      <FormControl isInvalid={errors.nieuwsbrief && touched.nieuwsbrief}>
                        <FormLabel color="orange.300">Digitale nieuwsbrieven ontvangen? *</FormLabel>
                        <Select {...field} placeholder="Selecteer optie" bg="gray.200" color="black" focusBorderColor="orange.400">
                          <option value="Ja">Ja</option>
                          <option value="Nee">Nee</option>
                        </Select>
                        {errors.nieuwsbrief && touched.nieuwsbrief && <Text color="red.400" fontSize="sm">{errors.nieuwsbrief}</Text>}
                      </FormControl>
                    )}
                  </Field>
                </SimpleGrid>

                <Divider borderColor="orange.400" />
                <Heading size="md" color="orange.400">Verklaringen</Heading>

                <Box p={4} bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400">
                  <VStack spacing={3} align="stretch">
                    <Text fontSize="sm" color="orange.200"><strong>Verklaring:</strong> Ondergetekende verklaart bovenstaande naar waarheid te hebben ingevuld en zich te zullen houden aan de Statuten en het Huishoudelijk Reglement van de H-DCN.</Text>
                    <Text fontSize="sm" color="orange.200"><strong>Machtiging:</strong> Ondergetekende machtigt hierbij de H-DCN de jaarlijkse contributie te innen m.b.v. automatische incasso.</Text>
                    <Text fontSize="sm" color="orange.200"><strong>Vrijwaring:</strong> Met aanvaarding van het lidmaatschap verklaar je dat deelname aan activiteiten geheel voor eigen risico en rekening is.</Text>
                  </VStack>
                </Box>

                <HStack>
                  <Box flex="1" />
                  <Field name="ondertekeningsdatum">
                    {({ field }) => (
                      <FormControl isInvalid={errors.ondertekeningsdatum && touched.ondertekeningsdatum} flex="1">
                        <FormLabel color="orange.300">Datum ondertekening *</FormLabel>
                        <Input {...field} type="date" bg="gray.200" color="black" focusBorderColor="orange.400" />
                        {errors.ondertekeningsdatum && touched.ondertekeningsdatum && <Text color="red.400" fontSize="sm">{errors.ondertekeningsdatum}</Text>}
                      </FormControl>
                    )}
                  </Field>
                  <Box flex="1" />
                </HStack>

                <Field name="akkoord">
                  {({ field }) => (
                    <FormControl isInvalid={errors.akkoord && touched.akkoord}>
                      <Checkbox {...field} isChecked={field.value} colorScheme="orange">
                        <Text color="orange.300">Ik ga akkoord met bovenstaande verklaringen *</Text>
                      </Checkbox>
                      {errors.akkoord && touched.akkoord && <Text color="red.400" fontSize="sm">{errors.akkoord}</Text>}
                    </FormControl>
                  )}
                </Field>

                {isUnder18 && (
                  <>
                    <Divider borderColor="orange.400" />
                    <Heading size="sm" color="orange.400">Voor personen onder 18 jaar</Heading>

                    <Field name="minderjarigNaam">
                      {({ field }) => (
                        <FormControl>
                          <FormLabel color="orange.300">Naam ouder/verzorger/wettelijke vertegenwoordiger</FormLabel>
                          <Input {...field} bg="gray.200" color="black" focusBorderColor="orange.400" />
                        </FormControl>
                      )}
                    </Field>

                    <Field name="minderjarigAkkoord">
                      {({ field }) => (
                        <FormControl>
                          <Checkbox {...field} isChecked={field.value} colorScheme="orange">
                            <Text color="orange.300">Akkoord als ouder/verzorger/wettelijke vertegenwoordiger</Text>
                          </Checkbox>
                        </FormControl>
                      )}
                    </Field>
                  </>
                )}

                <Button
                  type="submit"
                  colorScheme="orange"
                  size="lg"
                  isLoading={isSubmitting}
                  loadingText="Verzenden..."
                >
                  {existingMember ? 'Bijwerken' : 'Aanmelding Verzenden'}
                </Button>
              </VStack>
            </Form>
            );
          }}
        </Formik>
      </VStack>
    </Box>
  );
}

export default MembershipForm;