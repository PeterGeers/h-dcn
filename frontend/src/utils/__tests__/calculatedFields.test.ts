/**
 * Tests for Calculated Fields Engine
 * 
 * These tests verify that all compute functions work correctly and that
 * the calculated fields system processes member data as expected.
 */

import {
  computeCalculatedFields,
  computeCalculatedFieldsForArray,
  getCalculatedFieldValue,
  getMemberFullName,
  getMemberAge,
  getMemberBirthday,
  getMemberYearsOfMembership,
  getMemberStartYear,
  validateComputeFunctions,
  testComputeFunctions,
  isComputedField,
  getComputedFieldKeys
} from '../calculatedFields';
import { Member } from '../../types/index';

// Sample member data for testing
const sampleMember: Member = {
  id: 'test-1',
  name: 'Jan van der Berg',
  email: 'jan.vandenberg@example.com',
  region: 'Noord-Holland',
  membershipType: 'individual',
  voornaam: 'Jan',
  tussenvoegsel: 'van der',
  achternaam: 'Berg',
  geboortedatum: '1978-09-26',
  tijdstempel: '2018-04-01',
  ingangsdatum: '2018-04-01',
  regio: 'Noord-Holland'
};

const sampleMemberNoMiddleName: Member = {
  id: 'test-2',
  name: 'Marie Jansen',
  email: 'marie.jansen@example.com',
  region: 'Utrecht',
  membershipType: 'individual',
  voornaam: 'Marie',
  tussenvoegsel: '',
  achternaam: 'Jansen',
  geboortedatum: '1985-12-15',
  tijdstempel: '2020-01-15'
};

describe('Calculated Fields Engine', () => {
  describe('Individual Compute Functions', () => {
    test('concatenateName should combine name parts correctly', () => {
      const result = getMemberFullName(sampleMember);
      expect(result).toBe('Jan van der Berg');
    });

    test('concatenateName should handle missing middle name', () => {
      const result = getMemberFullName(sampleMemberNoMiddleName);
      expect(result).toBe('Marie Jansen');
    });

    test('concatenateName should handle empty values', () => {
      const emptyMember: Member = { 
        id: 'test-empty',
        name: '',
        email: 'empty@example.com',
        region: 'Test',
        membershipType: 'individual',
        voornaam: '', 
        tussenvoegsel: '', 
        achternaam: '' 
      };
      const result = getMemberFullName(emptyMember);
      expect(result).toBe('');
    });

    test('calculateAge should compute age correctly', () => {
      // Note: This test will need to be updated based on current date
      // For 1978-09-26, the age should be current year - 1978, adjusted for month/day
      const result = getMemberAge(sampleMember);
      expect(result).toBeGreaterThan(40); // Should be around 45-46 depending on current date
      expect(result).toBeLessThan(50);
    });

    test('extractBirthday should format birthday in Dutch', () => {
      const result = getMemberBirthday(sampleMember);
      expect(result).toBe('september 26');
    });

    test('extractBirthday should handle December birthday', () => {
      const result = getMemberBirthday(sampleMemberNoMiddleName);
      expect(result).toBe('december 15');
    });

    test('yearsDifference should calculate membership years', () => {
      const result = getMemberYearsOfMembership(sampleMember);
      // Should be current year - 2018, adjusted for month/day
      expect(result).toBeGreaterThan(5);
      expect(result).toBeLessThan(10);
    });

    test('year should extract year from date', () => {
      const result = getMemberStartYear(sampleMember);
      expect(result).toBe(2018);
    });
  });

  describe('Field Processing', () => {
    test('computeCalculatedFields should process all calculated fields', () => {
      const result = computeCalculatedFields(sampleMember);
      
      expect(result.korte_naam).toBe('Jan van der Berg');
      expect(result.verjaardag).toBe('september 26');
      expect(result.aanmeldingsjaar).toBe(2018);
      expect(typeof result.leeftijd).toBe('number');
      expect(typeof result.jaren_lid).toBe('number');
    });

    test('computeCalculatedFields should preserve original fields', () => {
      const result = computeCalculatedFields(sampleMember);
      
      expect(result.voornaam).toBe('Jan');
      expect(result.email).toBe('jan.vandenberg@example.com');
      expect(result.regio).toBe('Noord-Holland');
    });

    test('computeCalculatedFieldsForArray should process multiple members', () => {
      const members = [sampleMember, sampleMemberNoMiddleName];
      const result = computeCalculatedFieldsForArray(members);
      
      expect(result).toHaveLength(2);
      expect(result[0].korte_naam).toBe('Jan van der Berg');
      expect(result[1].korte_naam).toBe('Marie Jansen');
    });

    test('getCalculatedFieldValue should return specific field value', () => {
      const fullName = getCalculatedFieldValue(sampleMember, 'korte_naam');
      const age = getCalculatedFieldValue(sampleMember, 'leeftijd');
      
      expect(fullName).toBe('Jan van der Berg');
      expect(typeof age).toBe('number');
    });
  });

  describe('Utility Functions', () => {
    test('isComputedField should identify computed fields correctly', () => {
      expect(isComputedField('korte_naam')).toBe(true);
      expect(isComputedField('leeftijd')).toBe(true);
      expect(isComputedField('voornaam')).toBe(false);
      expect(isComputedField('email')).toBe(false);
    });

    test('getComputedFieldKeys should return all computed field keys', () => {
      const computedKeys = getComputedFieldKeys();
      
      expect(computedKeys).toContain('korte_naam');
      expect(computedKeys).toContain('leeftijd');
      expect(computedKeys).toContain('verjaardag');
      expect(computedKeys).toContain('jaren_lid');
      expect(computedKeys).toContain('aanmeldingsjaar');
    });

    test('validateComputeFunctions should pass validation', () => {
      const validation = validateComputeFunctions();
      
      expect(validation.valid).toBe(true);
      expect(validation.missing).toHaveLength(0);
      expect(validation.implemented).toContain('concatenateName');
      expect(validation.implemented).toContain('calculateAge');
    });
  });

  describe('Edge Cases', () => {
    test('should handle null/undefined member gracefully', () => {
      expect(computeCalculatedFields(null as any)).toBe(null);
      expect(computeCalculatedFields(undefined as any)).toBe(undefined);
    });

    test('should handle empty member object', () => {
      const emptyMember: Member = {
        id: 'test-empty-obj',
        name: '',
        email: 'empty@example.com',
        region: 'Test',
        membershipType: 'individual'
      };
      const result = computeCalculatedFields(emptyMember);
      expect(result.korte_naam).toBe('');
      expect(result.leeftijd).toBe(null);
      expect(result.verjaardag).toBe('');
      expect(result.jaren_lid).toBe(null);
      expect(result.aanmeldingsjaar).toBe(null);
    });

    test('should handle invalid dates gracefully', () => {
      const invalidMember: Member = {
        id: 'test-invalid',
        name: 'Test User',
        email: 'test@example.com',
        region: 'Test',
        membershipType: 'individual',
        voornaam: 'Test',
        geboortedatum: 'invalid-date',
        tijdstempel: 'invalid-date'
      };
      
      const result = computeCalculatedFields(invalidMember);
      expect(result.leeftijd).toBe(null);
      expect(result.jaren_lid).toBe(null);
      expect(result.verjaardag).toBe('');
      expect(result.aanmeldingsjaar).toBe(null);
    });

    test('should handle missing source fields', () => {
      const incompleteMember: Member = {
        id: 'test-incomplete',
        name: 'Test User',
        email: 'test@example.com',
        region: 'Test',
        membershipType: 'individual',
        voornaam: 'Test'
        // Missing achternaam, geboortedatum, etc.
      };
      
      const result = computeCalculatedFields(incompleteMember);
      expect(result.korte_naam).toBe('Test');
      expect(result.leeftijd).toBe(null);
      expect(result.verjaardag).toBe('');
      expect(result.jaren_lid).toBe(null);
    });
  });

  describe('Development Utilities', () => {
    test('testComputeFunctions should return test results', () => {
      const results = testComputeFunctions();
      
      expect(results).toHaveProperty('korte_naam');
      expect(results).toHaveProperty('leeftijd');
      expect(results).toHaveProperty('verjaardag');
      expect(results).toHaveProperty('jaren_lid');
      expect(results).toHaveProperty('aanmeldingsjaar');
    });
  });
});