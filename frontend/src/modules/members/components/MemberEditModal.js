import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, HStack, Button, Select, FormControl, FormLabel, Input, SimpleGrid, useToast, Text, Box
} from '@chakra-ui/react';

function MemberEditModal({ isOpen, onClose, member, onSave }) {
  const [formData, setFormData] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [regioOptions, setRegioOptions] = useState([]);
  const [statusOptions, setStatusOptions] = useState([]);
  const [lidmaatschapOptions, setLidmaatschapOptions] = useState([]);
  const [showAddField, setShowAddField] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldValue, setNewFieldValue] = useState('');
  const toast = useToast();

  const hasValue = (value) => value && value !== '' && value !== 'undefined' && value !== null;

  const allFields = {
    // Personal
    voornaam: 'Voornaam', achternaam: 'Achternaam', initialen: 'Initialen', tussenvoegsel: 'Tussenvoegsel',
    geboortedatum: 'Geboortedatum', geslacht: 'Geslacht', bsn: 'BSN', nationaliteit: 'Nationaliteit',
    // Contact
    email: 'Email', telefoon: 'Telefoon', mobiel: 'Mobiel', werktelefoon: 'Werk telefoon',
    // Address
    straat: 'Straat', huisnummer: 'Huisnummer', postcode: 'Postcode', woonplaats: 'Woonplaats', land: 'Land',
    postadres: 'Postadres', postpostcode: 'Post postcode', postwoonplaats: 'Post woonplaats', postland: 'Post land',
    // Membership
    status: 'Status', lidmaatschap: 'Lidmaatschap', lidnummer: 'Lidnummer', ingangsdatum: 'Ingangsdatum',
    einddatum: 'Einddatum', opzegtermijn: 'Opzegtermijn', regio: 'Regio', clubblad: 'Clubblad', nieuwsbrief: 'Nieuwsbrief',
    // Motor
    motormerk: 'Motormerk', motortype: 'Motortype', motormodel: 'Motormodel', motorkleur: 'Motorkleur',
    bouwjaar: 'Bouwjaar', kenteken: 'Kenteken', cilinderinhoud: 'Cilinderinhoud', vermogen: 'Vermogen',
    // Financial
    bankrekeningnummer: 'Bankrekeningnummer', iban: 'IBAN', bic: 'BIC', contributie: 'Contributie',
    betaalwijze: 'Betaalwijze', incasso: 'Incasso',
    // Other
    beroep: 'Beroep', werkgever: 'Werkgever', hobbys: 'Hobby\'s', wiewatwaar: 'Hoe gevonden',
    minderjarigNaam: 'Ouder/Verzorger', notities: 'Notities', opmerkingen: 'Opmerkingen',
    privacy: 'Privacy', toestemmingfoto: 'Toestemming foto\'s'
  };

  const personalFields = ['voornaam', 'achternaam', 'initialen', 'tussenvoegsel', 'geboortedatum', 'geslacht', 'bsn', 'nationaliteit', 'email', 'telefoon', 'mobiel', 'werktelefoon'].filter(field => hasValue((member && member[field]) || formData[field]));
  
  const addressFields = ['straat', 'huisnummer', 'postcode', 'woonplaats', 'land', 'postadres', 'postpostcode', 'postwoonplaats', 'postland'].filter(field => hasValue((member && member[field]) || formData[field]));
  
  const membershipFields = ['lidmaatschap', 'lidnummer', 'ingangsdatum', 'einddatum', 'opzegtermijn', 'regio', 'clubblad', 'nieuwsbrief'].filter(field => hasValue((member && member[field]) || formData[field]));
  
  const motorFields = ['motormerk', 'motortype', 'motormodel', 'motorkleur', 'bouwjaar', 'kenteken', 'cilinderinhoud', 'vermogen'].filter(field => hasValue((member && member[field]) || formData[field]));
  
  const financialFields = ['bankrekeningnummer', 'iban', 'bic', 'contributie', 'betaalwijze', 'incasso'].filter(field => hasValue((member && member[field]) || formData[field]));
  
  const knownFields = new Set(['member_id', 'created_at', 'updated_at', 'name', 'phone', 'membership_type', 'address', 'status', ...personalFields, ...addressFields, ...membershipFields, ...motorFields, ...financialFields]);
  
  const otherFields = member ? Object.keys(member).filter(field => !knownFields.has(field) && hasValue((member && member[field]) || formData[field])) : [];

  useEffect(() => {
    if (member) {
      setFormData({
        voornaam: member.voornaam || '',
        achternaam: member.achternaam || '',
        initialen: member.initialen || '',
        tussenvoegsel: member.tussenvoegsel || '',
        geboortedatum: member.geboortedatum || '',
        geslacht: member.geslacht || '',
        bsn: member.bsn || '',
        nationaliteit: member.nationaliteit || '',
        email: member.email || '',
        telefoon: member.telefoon || member.phone || '',
        mobiel: member.mobiel || '',
        werktelefoon: member.werktelefoon || '',
        straat: member.straat || '',
        huisnummer: member.huisnummer || '',
        postcode: member.postcode || '',
        woonplaats: member.woonplaats || '',
        land: member.land || '',
        postadres: member.postadres || '',
        postpostcode: member.postpostcode || '',
        postwoonplaats: member.postwoonplaats || '',
        postland: member.postland || '',
        status: member.status || '',
        lidmaatschap: member.lidmaatschap || member.membership_type || '',
        lidnummer: member.lidnummer || '',
        ingangsdatum: member.ingangsdatum || '',
        einddatum: member.einddatum || '',
        opzegtermijn: member.opzegtermijn || '',
        regio: member.regio || '',
        clubblad: member.clubblad || '',
        nieuwsbrief: member.nieuwsbrief || '',
        motormerk: member.motormerk || '',
        motortype: member.motortype || '',
        motormodel: member.motormodel || '',
        motorkleur: member.motorkleur || '',
        bouwjaar: member.bouwjaar || '',
        kenteken: member.kenteken || '',
        cilinderinhoud: member.cilinderinhoud || '',
        vermogen: member.vermogen || '',
        bankrekeningnummer: member.bankrekeningnummer || '',
        iban: member.iban || '',
        bic: member.bic || '',
        contributie: member.contributie || '',
        betaalwijze: member.betaalwijze || '',
        incasso: member.incasso || '',
        beroep: member.beroep || '',
        werkgever: member.werkgever || '',
        hobbys: member.hobbys || '',
        wiewatwaar: member.wiewatwaar || '',
        minderjarigNaam: member.minderjarigNaam || '',
        notities: member.notities || '',
        opmerkingen: member.opmerkingen || '',
        privacy: member.privacy || '',
        toestemmingfoto: member.toestemmingfoto || ''
      });
    } else {
      // Initialize with empty values when no member
      setFormData({
        voornaam: '', achternaam: '', initialen: '', tussenvoegsel: '', geboortedatum: '', geslacht: '',
        bsn: '', nationaliteit: '', email: '', telefoon: '', mobiel: '', werktelefoon: '',
        straat: '', huisnummer: '', postcode: '', woonplaats: '', land: '',
        postadres: '', postpostcode: '', postwoonplaats: '', postland: '',
        status: '', lidmaatschap: '', lidnummer: '', ingangsdatum: '', einddatum: '', opzegtermijn: '',
        regio: '', clubblad: '', nieuwsbrief: '',
        motormerk: '', motortype: '', motormodel: '', motorkleur: '', bouwjaar: '', kenteken: '', cilinderinhoud: '', vermogen: '',
        bankrekeningnummer: '', iban: '', bic: '', contributie: '', betaalwijze: '', incasso: '',
        beroep: '', werkgever: '', hobbys: '', wiewatwaar: '', minderjarigNaam: '', notities: '', opmerkingen: '', privacy: '', toestemmingfoto: ''
      });
    }
  }, [member]);

  useEffect(() => {
    loadParameterOptions();
  }, []);

  const loadParameterOptions = async () => {
    try {
      const response = await fetch('https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/parameters');
      if (response.ok) {
        const parameters = await response.json();
        
        // Load regio options
        const regioParam = parameters.find(p => p.name?.toLowerCase() === 'regio');
        if (regioParam) {
          const regios = JSON.parse(regioParam.value);
          setRegioOptions(regios);
        }
        
        // Load status options
        const statusParam = parameters.find(p => p.name?.toLowerCase() === 'statuslidmaatschap');
        if (statusParam) {
          const statuses = JSON.parse(statusParam.value);
          setStatusOptions(statuses);
        }
        
        // Load lidmaatschap options
        const lidmaatschapParam = parameters.find(p => p.name?.toLowerCase() === 'lidmaatschap');
        if (lidmaatschapParam) {
          const lidmaatschappen = JSON.parse(lidmaatschapParam.value);
          setLidmaatschapOptions(lidmaatschappen);
        }
      }
    } catch (error) {
      console.error('Failed to load parameter options:', error);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleAddField = () => {
    if (newFieldName.trim() && newFieldValue.trim()) {
      setFormData(prev => ({
        ...prev,
        [newFieldName.trim()]: newFieldValue.trim()
      }));
      setNewFieldName('');
      setNewFieldValue('');
      setShowAddField(false);
      toast({
        title: 'Veld toegevoegd',
        status: 'success',
        duration: 2000,
      });
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      const updatedMember = {
        member_id: member.member_id,
        ...formData,
        name: `${formData.voornaam} ${formData.achternaam}`.trim(),
        phone: formData.telefoon,
        membership_type: formData.lidmaatschap,
        address: `${formData.straat}, ${formData.postcode} ${formData.woonplaats}, ${formData.land}`.trim()
      };

      await onSave(updatedMember);
      onClose();
      toast({
        title: 'Lid bijgewerkt',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: 'Fout bij opslaan',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderField = (fieldKey) => {
    const label = allFields[fieldKey];
    const value = formData[fieldKey] || '';

    if (['status', 'lidmaatschap', 'regio'].includes(fieldKey)) {
      const options = fieldKey === 'status' ? statusOptions :
                    fieldKey === 'lidmaatschap' ? lidmaatschapOptions : regioOptions;
      return (
        <FormControl key={fieldKey}>
          <FormLabel color="orange.300">{label}</FormLabel>
          <Select
            value={value}
            onChange={(e) => handleChange(fieldKey, e.target.value)}
            bg="gray.700"
            color="orange.400"
            borderColor="orange.400"
          >
            <option value="">Selecteer...</option>
            {options.map((option, index) => (
              <option key={index} value={option.value || option}>
                {option.value || option}
              </option>
            ))}
          </Select>
        </FormControl>
      );
    }

    if (['clubblad', 'nieuwsbrief', 'geslacht', 'betaalwijze', 'incasso', 'privacy', 'toestemmingfoto'].includes(fieldKey)) {
      const options = {
        clubblad: ['Digitaal', 'Papier', 'Beide', 'Geen'],
        nieuwsbrief: ['Ja', 'Nee'],
        geslacht: ['M', 'V', 'X'],
        betaalwijze: ['Incasso', 'Overmaking', 'Contant'],
        incasso: ['Ja', 'Nee'],
        privacy: ['Ja', 'Nee'],
        toestemmingfoto: ['Ja', 'Nee']
      };
      return (
        <FormControl key={fieldKey}>
          <FormLabel color="orange.300">{label}</FormLabel>
          <Select
            value={value}
            onChange={(e) => handleChange(fieldKey, e.target.value)}
            bg="gray.700"
            color="orange.400"
            borderColor="orange.400"
          >
            <option value="">Selecteer...</option>
            {options[fieldKey].map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </Select>
        </FormControl>
      );
    }

    const inputType = ['geboortedatum', 'ingangsdatum', 'einddatum'].includes(fieldKey) ? 'date' :
                     fieldKey === 'email' ? 'email' :
                     fieldKey === 'bouwjaar' ? 'number' : 'text';

    return (
      <FormControl key={fieldKey}>
        <FormLabel color="orange.300">{label}</FormLabel>
        <Input
          type={inputType}
          value={value}
          onChange={(e) => handleChange(fieldKey, e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
        />
      </FormControl>
    );
  };

  if (!member) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          Lid Bewerken - {member.name || `${member.voornaam} ${member.achternaam}`}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={6} align="stretch">
            
            {/* Status */}
            {hasValue(formData.status) && (
              <FormControl>
                <FormLabel color="orange.300">Status</FormLabel>
                {renderField('status')}
              </FormControl>
            )}

            {/* Personal Info */}
            {personalFields.length > 0 && (
              <Box>
                <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                  Persoonlijke Gegevens
                </Text>
                <SimpleGrid columns={2} spacing={4}>
                  {personalFields.map(fieldKey => renderField(fieldKey))}
                </SimpleGrid>
              </Box>
            )}

            {/* Address */}
            {addressFields.length > 0 && (
              <Box>
                <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                  Adresgegevens
                </Text>
                <SimpleGrid columns={2} spacing={4}>
                  {addressFields.map(fieldKey => renderField(fieldKey))}
                </SimpleGrid>
              </Box>
            )}

            {/* Membership */}
            {membershipFields.length > 0 && (
              <Box>
                <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                  Lidmaatschap
                </Text>
                <SimpleGrid columns={2} spacing={4}>
                  {membershipFields.map(fieldKey => renderField(fieldKey))}
                </SimpleGrid>
              </Box>
            )}

            {/* Motor Info */}
            {motorFields.length > 0 && (
              <Box>
                <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                  Motor Gegevens
                </Text>
                <SimpleGrid columns={2} spacing={4}>
                  {motorFields.map(fieldKey => renderField(fieldKey))}
                </SimpleGrid>
              </Box>
            )}

            {/* Financial */}
            {financialFields.length > 0 && (
              <Box>
                <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                  Financiële Gegevens
                </Text>
                <SimpleGrid columns={2} spacing={4}>
                  {financialFields.map(fieldKey => renderField(fieldKey))}
                </SimpleGrid>
              </Box>
            )}

            {/* Other Fields */}
            <Box>
              <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                Overige Informatie
              </Text>
              <SimpleGrid columns={2} spacing={4}>
                {otherFields.map(fieldKey => renderField(fieldKey))}
              </SimpleGrid>
              
              {/* Add New Field */}
              <Box mt={4} p={4} bg="gray.700" borderRadius="md" border="1px" borderColor="orange.400">
                <HStack justify="space-between" mb={3}>
                  <Text color="orange.300" fontWeight="bold">Attribuut toevoegen</Text>
                  <Button
                    size="sm"
                    colorScheme="orange"
                    onClick={() => setShowAddField(!showAddField)}
                  >
                    {showAddField ? 'Annuleren' : '+ Toevoegen'}
                  </Button>
                </HStack>
                
                {showAddField && (
                  <VStack spacing={3}>
                    <HStack w="full">
                      <Input
                        placeholder="Veldnaam"
                        value={newFieldName}
                        onChange={(e) => setNewFieldName(e.target.value)}
                        bg="gray.600"
                        borderColor="orange.400"
                      />
                      <Input
                        placeholder="Waarde"
                        value={newFieldValue}
                        onChange={(e) => setNewFieldValue(e.target.value)}
                        bg="gray.600"
                        borderColor="orange.400"
                      />
                    </HStack>
                    <Button
                      colorScheme="green"
                      size="sm"
                      onClick={handleAddField}
                      isDisabled={!newFieldName.trim() || !newFieldValue.trim()}
                    >
                      Veld toevoegen
                    </Button>
                  </VStack>
                )}
              </Box>
            </Box>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Annuleren
          </Button>
          <Button
            colorScheme="orange"
            onClick={handleSave}
            isLoading={isLoading}
            loadingText="Opslaan..."
          >
            Opslaan
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default MemberEditModal;