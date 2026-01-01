import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, HStack, Button, Select, FormControl, FormLabel, Input, SimpleGrid, useToast, Text, Box
} from '@chakra-ui/react';
import { Member } from '../../../types';
import { getAuthHeadersForGet, getAuthHeaders } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';
import { useErrorHandler, apiCall } from '../../../utils/errorHandler';
import { getUserRoles } from '../../../utils/functionPermissions';
import { hasRegionalAccess } from '../../../utils/regionalMapping';

interface ParameterOption {
  value?: string;
}

interface MemberEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  member: Member | null;
  onSave: (member: Member) => Promise<void>;
  user?: any; // Add user prop for permission checking
}

function MemberEditModal({ isOpen, onClose, member, onSave, user }: MemberEditModalProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [regioOptions, setRegioOptions] = useState<ParameterOption[]>([]);
  const [statusOptions, setStatusOptions] = useState<ParameterOption[]>([]);
  const [lidmaatschapOptions, setLidmaatschapOptions] = useState<ParameterOption[]>([]);
  const [geslachtOptions, setGeslachtOptions] = useState<ParameterOption[]>([]);
  const [showAddField, setShowAddField] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldValue, setNewFieldValue] = useState('');
  const { handleError, handleSuccess } = useErrorHandler();

  const userRoles = getUserRoles(user || {});
  const isOwnRecord = member?.email === user?.attributes?.email;

  const hasValue = (value: any) => value && value !== '' && value !== 'undefined' && value !== null;

  // Convert date from various formats to ISO format (yyyy-MM-dd) for HTML date inputs
  const convertToISODate = (dateValue: string): string => {
    if (!dateValue) return '';
    
    // If already in ISO format, return as is
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateValue)) {
      return dateValue;
    }
    
    // Handle Dutch format variations (d-M-yyyy, dd-MM-yyyy, d/M/yyyy, dd/MM/yyyy)
    if (/^\d{1,2}[-/]\d{1,2}[-/]\d{4}$/.test(dateValue)) {
      const parts = dateValue.split(/[-/]/);
      const [day, month, year] = parts;
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    }
    
    // Handle European format with dots (d.M.yyyy, dd.MM.yyyy)
    if (/^\d{1,2}\.\d{1,2}\.\d{4}$/.test(dateValue)) {
      const [day, month, year] = dateValue.split('.');
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    }
    
    // Handle US format (M/d/yyyy, MM/dd/yyyy)
    if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateValue)) {
      const [month, day, year] = dateValue.split('/');
      // Check if this looks like US format (month > 12 would indicate day/month swap)
      if (parseInt(month) <= 12) {
        return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
      } else {
        // Treat as European format
        return `${year}-${day.padStart(2, '0')}-${month.padStart(2, '0')}`;
      }
    }
    
    // Handle reverse format (yyyy-M-d, yyyy/M/d)
    if (/^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/.test(dateValue)) {
      const parts = dateValue.split(/[-/]/);
      const [year, month, day] = parts;
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    }
    
    // Handle timestamp or other formats
    try {
      const date = new Date(dateValue);
      if (!isNaN(date.getTime())) {
        return date.toISOString().split('T')[0];
      }
    } catch (e) {
      // Silent fail for invalid dates
    }
    
    // If all else fails, try to parse common text formats
    try {
      // Handle formats like "3 februari 1974"
      const months = {
        'januari': '01', 'februari': '02', 'maart': '03', 'april': '04',
        'mei': '05', 'juni': '06', 'juli': '07', 'augustus': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'december': '12'
      };
      
      const dutchDateMatch = dateValue.toLowerCase().match(/(\d{1,2})\s+(\w+)\s+(\d{4})/);
      if (dutchDateMatch) {
        const [, day, monthName, year] = dutchDateMatch;
        const month = months[monthName];
        if (month) {
          return `${year}-${month}-${day.padStart(2, '0')}`;
        }
      }
    } catch (e) {
      // Silent fail
    }
    
    console.warn('Could not convert date format:', dateValue);
    return '';
  };

  // Convert date from ISO format back to display format when saving
  const convertFromISODate = (isoDate: string): string => {
    if (!isoDate) return '';
    
    try {
      const date = new Date(isoDate);
      if (!isNaN(date.getTime())) {
        // Return in original format or keep ISO format for backend
        return isoDate; // Keep ISO format for backend compatibility
      }
    } catch (e) {
      console.warn('Could not convert ISO date:', isoDate);
    }
    
    return isoDate;
  };

  /**
   * Check if current user can edit a specific field type based on their roles AND membership type restrictions
   */
  const canEditFieldType = (fieldType: 'personal' | 'address' | 'membership' | 'motor' | 'financial' | 'administrative' | 'status'): boolean => {
    // Admin roles can edit all fields
    if (userRoles.includes('hdcnAdmins') || userRoles.includes('Members_CRUD_All')) {
      return true;
    }

    // Status field - only specific admin roles can edit
    if (fieldType === 'status') {
      return userRoles.includes('hdcnAdmins') || 
             userRoles.includes('Members_CRUD_All') ||
             userRoles.includes('Members_Status_Approve');
    }

    // Own record - members can edit their personal, address, and motor fields
    if (isOwnRecord && userRoles.includes('hdcnLeden')) {
      // PRESERVE EXISTING MEMBERSHIP TYPE RESTRICTIONS
      // Motor fields are only editable for specific membership types
      if (fieldType === 'motor') {
        const membershipType = member?.lidmaatschap || member?.membership_type;
        const motorRequiredTypes = ['Gewoon lid', 'Gezins lid'];
        return motorRequiredTypes.includes(membershipType);
      }
      
      return ['personal', 'address'].includes(fieldType);
    }

    // Financial fields - only specific roles can edit
    if (fieldType === 'financial') {
      return userRoles.some(role => 
        role.includes('Treasurer') || 
        role.includes('Members_CRUD_All') ||
        role.includes('hdcnAdmins')
      );
    }

    // Administrative fields - only admin roles can edit
    if (fieldType === 'administrative') {
      return userRoles.includes('hdcnAdmins') || 
             userRoles.includes('Members_CRUD_All');
    }

    // Membership fields - admin and regional roles can edit
    if (fieldType === 'membership') {
      if (userRoles.includes('hdcnAdmins') || userRoles.includes('Members_CRUD_All')) {
        return true;
      }
      
      // Regional roles can edit membership fields for their region
      if (member?.regio) {
        return hasRegionalAccess(userRoles, member.regio) && 
               userRoles.some(role => role.includes('Regional_Chairman_'));
      }
    }

    // Webmaster has full edit access
    if (userRoles.includes('Webmaster')) {
      return true;
    }

    return false;
  };

  const allFields: Record<string, string> = {
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
    // Administrative fields that should be in membership section
    tijdstempel: 'Tijdstempel', aanmeldingsjaar: 'Aanmeldingsjaar', datum_ondertekening: 'Datum ondertekening',
    ingangsdatum_lidmaatschap: 'Ingangsdatum lidmaatschap', aanmeldingsdatum: 'Aanmeldingsdatum',
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

  // Show all fields that are in the view modal, regardless of whether they have values
  // This allows users to fill in empty fields
  const personalFields = ['voornaam', 'achternaam', 'initialen', 'tussenvoegsel', 'geboortedatum', 'geslacht', 'bsn', 'nationaliteit', 'email', 'telefoon', 'mobiel', 'werktelefoon'];
  
  const addressFields = ['straat', 'huisnummer', 'postcode', 'woonplaats', 'land', 'postadres', 'postpostcode', 'postwoonplaats', 'postland'];
  
  // Updated membership fields to match view modal grouping - show all fields
  const membershipFields = ['lidmaatschap', 'regio', 'clubblad', 'nieuwsbrief', 'lidnummer', 'ingangsdatum', 'einddatum', 'opzegtermijn', 'tijdstempel', 'aanmeldingsjaar', 'datum_ondertekening', 'ingangsdatum_lidmaatschap', 'aanmeldingsdatum'];
  
  const motorFields = ['motormerk', 'motortype', 'motormodel', 'motorkleur', 'bouwjaar', 'kenteken', 'cilinderinhoud', 'vermogen'];
  
  const financialFields = ['bankrekeningnummer', 'iban', 'bic', 'contributie', 'betaalwijze', 'incasso'];
  
  const knownFields = new Set(['member_id', 'created_at', 'updated_at', 'name', 'phone', 'membership_type', 'address', 'status', 'datumOndertekening', 'ingangsdatumLidmaatschap', 'aanmeldingsDatum', ...personalFields, ...addressFields, ...membershipFields, ...motorFields, ...financialFields]);
  
  // Only filter other fields that actually have values
  const otherFields = member ? Object.keys(member).filter(field => !knownFields.has(field) && hasValue((member && member[field]) || formData[field])) : [];

  useEffect(() => {
    if (member) {
      setFormData({
        voornaam: member.voornaam || '',
        achternaam: member.achternaam || '',
        initialen: member.initialen || '',
        tussenvoegsel: member.tussenvoegsel || '',
        geboortedatum: convertToISODate(member.geboortedatum || ''),
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
        lidnummer: String(member.lidnummer || ''),
        ingangsdatum: convertToISODate(member.ingangsdatum || ''),
        einddatum: convertToISODate(member.einddatum || ''),
        opzegtermijn: member.opzegtermijn || '',
        regio: member.regio || '',
        clubblad: member.clubblad || '',
        nieuwsbrief: member.nieuwsbrief || '',
        // Administrative fields that should be in membership section
        tijdstempel: convertToISODate(member.tijdstempel || ''),
        aanmeldingsjaar: member.aanmeldingsjaar || '',
        datum_ondertekening: convertToISODate(member.datum_ondertekening || member.datumOndertekening || ''),
        ingangsdatum_lidmaatschap: convertToISODate(member.ingangsdatum_lidmaatschap || member.ingangsdatumLidmaatschap || ''),
        aanmeldingsdatum: convertToISODate(member.aanmeldingsdatum || member.aanmeldingsDatum || ''),
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
        tijdstempel: '', aanmeldingsjaar: '', datum_ondertekening: '', ingangsdatum_lidmaatschap: '', aanmeldingsdatum: '',
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
      // Load parameters from JSON file only - no API calls
      // Add timestamp to force cache refresh
      const timestamp = new Date().getTime();
      const version = process.env.REACT_APP_CACHE_VERSION || '1.0';
      const response = await fetch(`/parameters.json?v=${version}&t=${timestamp}`);
      
      if (response.ok) {
        const parameters = await response.json();
        console.log('🔍 Loaded parameters from JSON:', parameters);
        
        // Set parameter options directly from JSON structure
        setRegioOptions(parameters.regio || []);
        setStatusOptions(parameters.statuslidmaatschap || []);
        setLidmaatschapOptions(parameters.lidmaatschap || []);
        setGeslachtOptions(parameters.geslacht || []);
        
        console.log('🔍 Loaded membership options:', parameters.lidmaatschap);
        console.log('🔍 Loaded wiewatwaar options:', parameters.wiewatwaar);
      } else {
        console.error('Failed to load parameters.json:', response.status);
        // Set fallback options
        setRegioOptions([]);
        setStatusOptions([]);
        setGeslachtOptions([]);
        setLidmaatschapOptions([
          { value: 'Gewoon lid' },
          { value: 'Gezins lid' },
          { value: 'Donateur zonder motor' },
          { value: 'Gezins donateur zonder motor' }
        ]);
      }
    } catch (error: any) {
      console.error('Error loading parameters from JSON:', error);
      handleError(error, 'laden parameters');
      // Set fallback options
      setRegioOptions([]);
      setStatusOptions([]);
      setGeslachtOptions([]);
      setLidmaatschapOptions([
        { value: 'Gewoon lid' },
        { value: 'Gezins lid' },
        { value: 'Donateur zonder motor' },
        { value: 'Gezins donateur zonder motor' }
      ]);
    }
  };

  const handleChange = (field: string, value: string) => {
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
      handleSuccess('Veld succesvol toegevoegd');
    }
  };

  const handleSave = async () => {
    // Validate required fields
    const requiredFields = ['voornaam', 'achternaam', 'email'];
    const missingFields = requiredFields.filter(field => !formData[field]?.trim());
    
    if (missingFields.length > 0) {
      handleError({
        status: 400,
        message: `Vul de volgende velden in: ${missingFields.map(f => allFields[f]).join(', ')}`
      }, 'validatie');
      return;
    }

    setIsLoading(true);
    try {
      // Create the update payload with only the changed fields
      const updatePayload: any = {};
      
      // Always include basic required fields
      updatePayload.voornaam = formData.voornaam;
      updatePayload.achternaam = formData.achternaam;
      updatePayload.email = formData.email;
      
      // Include other fields that have values
      Object.keys(formData).forEach(key => {
        if (formData[key] && formData[key] !== '' && key !== 'member_id' && key !== 'updated_at') {
          updatePayload[key] = formData[key];
        }
      });
      
      // Ensure name field is updated
      updatePayload.name = `${formData.voornaam} ${formData.achternaam}`;
      
      console.log('🔄 Sending member update:', updatePayload);
      
      // Call the backend update endpoint directly
      const headers = await getAuthHeaders();
      const response = await fetch(API_URLS.member(member.member_id), {
        method: 'PUT',
        headers,
        body: JSON.stringify(updatePayload)
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Member update failed:', response.status, errorText);
        throw new Error(`Update failed: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('✅ Member update successful:', result);
      
      // Create updated member object for parent component
      const updatedMember: Member = {
        ...member,
        ...updatePayload,
        id: member.id,
        member_id: member.member_id,
        created_at: member.created_at
        // updated_at will come from backend or be preserved from original member
      };

      await onSave(updatedMember);
      onClose();
      handleSuccess('Lid succesvol bijgewerkt');
    } catch (error: any) {
      console.error('❌ Error updating member:', error);
      handleError({ status: 0, message: error.message }, 'opslaan lid');
    } finally {
      setIsLoading(false);
    }
  };

  const renderField = (fieldKey: string) => {
    const label = allFields[fieldKey];
    const value = formData[fieldKey] || '';
    const isRequired = ['voornaam', 'achternaam', 'email'].includes(fieldKey);

    // Determine field type for permission checking
    let fieldType: 'personal' | 'address' | 'membership' | 'motor' | 'financial' | 'administrative' | 'status' = 'personal';
    
    if (['status'].includes(fieldKey)) {
      fieldType = 'status';
    } else if (['voornaam', 'achternaam', 'initialen', 'tussenvoegsel', 'geboortedatum', 'geslacht', 'bsn', 'nationaliteit', 'email', 'telefoon', 'mobiel', 'werktelefoon'].includes(fieldKey)) {
      fieldType = 'personal';
    } else if (['straat', 'huisnummer', 'postcode', 'woonplaats', 'land', 'postadres', 'postpostcode', 'postwoonplaats', 'postland'].includes(fieldKey)) {
      fieldType = 'address';
    } else if (['lidmaatschap', 'lidnummer', 'ingangsdatum', 'einddatum', 'opzegtermijn', 'regio', 'clubblad', 'nieuwsbrief'].includes(fieldKey)) {
      fieldType = 'membership';
    } else if (['motormerk', 'motortype', 'motormodel', 'motorkleur', 'bouwjaar', 'kenteken', 'cilinderinhoud', 'vermogen'].includes(fieldKey)) {
      fieldType = 'motor';
    } else if (['bankrekeningnummer', 'iban', 'bic', 'contributie', 'betaalwijze', 'incasso'].includes(fieldKey)) {
      fieldType = 'financial';
    } else {
      fieldType = 'administrative';
    }

    // Check if user can edit this field type
    const canEdit = canEditFieldType(fieldType);

    if (['status', 'lidmaatschap', 'regio', 'geslacht'].includes(fieldKey)) {
      const options = fieldKey === 'status' ? statusOptions :
                    fieldKey === 'lidmaatschap' ? lidmaatschapOptions : 
                    fieldKey === 'geslacht' ? geslachtOptions : regioOptions;
      return (
        <FormControl key={fieldKey} isRequired={isRequired} isDisabled={!canEdit}>
          <FormLabel color="orange.300">{label}{isRequired && ' *'}{!canEdit && ' (Alleen-lezen)'}</FormLabel>
          <Select
            value={value}
            onChange={(e) => canEdit && handleChange(fieldKey, e.target.value)}
            bg="gray.700"
            color="orange.400"
            borderColor="orange.400"
            isDisabled={!canEdit}
          >
            <option value="">Selecteer...</option>
            {options.map((option, index) => {
              const value = typeof option === 'string' ? option : option.value || '';
              return (
                <option key={index} value={value}>
                  {value}
                </option>
              );
            })}
          </Select>
        </FormControl>
      );
    }

    if (['clubblad', 'nieuwsbrief', 'betaalwijze', 'incasso', 'privacy', 'toestemmingfoto'].includes(fieldKey)) {
      const options: Record<string, string[]> = {
        clubblad: ['Digitaal', 'Papier', 'Beide', 'Geen'],
        nieuwsbrief: ['Ja', 'Nee'],
        betaalwijze: ['Incasso', 'Overmaking', 'Contant'],
        incasso: ['Ja', 'Nee'],
        privacy: ['Ja', 'Nee'],
        toestemmingfoto: ['Ja', 'Nee']
      };
      return (
        <FormControl key={fieldKey} isRequired={isRequired} isDisabled={!canEdit}>
          <FormLabel color="orange.300">{label}{isRequired && ' *'}{!canEdit && ' (Alleen-lezen)'}</FormLabel>
          <Select
            value={value}
            onChange={(e) => canEdit && handleChange(fieldKey, e.target.value)}
            bg="gray.700"
            color="orange.400"
            borderColor="orange.400"
            isDisabled={!canEdit}
          >
            <option value="">Selecteer...</option>
            {options[fieldKey]?.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </Select>
        </FormControl>
      );
    }

    const inputType = ['geboortedatum', 'ingangsdatum', 'einddatum', 'tijdstempel', 'datum_ondertekening', 'aanmeldingsdatum', 'ingangsdatum_lidmaatschap'].includes(fieldKey) ? 'date' :
                     fieldKey === 'email' ? 'email' :
                     ['bouwjaar', 'aanmeldingsjaar'].includes(fieldKey) ? 'number' : 'text';

    return (
      <FormControl key={fieldKey} isRequired={isRequired} isDisabled={!canEdit}>
        <FormLabel color="orange.300">{label}{isRequired && ' *'}{!canEdit && ' (Alleen-lezen)'}</FormLabel>
        <Input
          type={inputType}
          value={value}
          onChange={(e) => canEdit && handleChange(fieldKey, e.target.value)}
          bg="gray.700"
          borderColor="orange.400"
          isDisabled={!canEdit}
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
            {hasValue(formData.status) && canEditFieldType('status') && (
              <FormControl>
                <FormLabel color="orange.300">Status</FormLabel>
                {renderField('status')}
              </FormControl>
            )}

            {/* Personal Info */}
            {canEditFieldType('personal') && (
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
            {canEditFieldType('address') && (
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
            {canEditFieldType('membership') && (
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
            {canEditFieldType('motor') && (
              <Box>
                <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                  Motor Gegevens
                </Text>
                <SimpleGrid columns={2} spacing={4}>
                  {motorFields.map(fieldKey => renderField(fieldKey))}
                </SimpleGrid>
              </Box>
            )}

            {/* Show message if motor fields are hidden due to membership type */}
            {!canEditFieldType('motor') && isOwnRecord && (member?.lidmaatschap === 'Gezins donateur zonder motor' || member?.lidmaatschap === 'Donateur zonder motor') && (
              <Box>
                <Text fontSize="lg" fontWeight="bold" color="orange.400" mb={3}>
                  Motor Gegevens
                </Text>
                <Text color="gray.400" fontStyle="italic">
                  Motor gegevens zijn niet van toepassing voor uw lidmaatschap type: {member?.lidmaatschap}
                </Text>
              </Box>
            )}

            {/* Financial */}
            {canEditFieldType('financial') && (
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