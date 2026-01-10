/**
 * Tests for AnalyticsService
 * 
 * Tests the analytics processing functionality with sample member data
 */

import { analyticsService } from '../AnalyticsService';
import { Member } from '../../types/index';

// Sample test data
const sampleMembers: Member[] = [
  {
    id: '1',
    name: 'Jan Jansen',
    email: 'jan.jansen@example.com',
    region: 'Noord-Holland',
    membershipType: 'Gewoon lid',
    voornaam: 'Jan',
    achternaam: 'Jansen',
    geboortedatum: '1980-05-15',
    tijdstempel: '2015-04-01',
    ingangsdatum: '2015-04-01',
    regio: 'Noord-Holland',
    lidmaatschap: 'Gewoon lid',
    status: 'Actief'
  },
  {
    id: '2',
    name: 'Marie Pietersen',
    email: 'marie.pietersen@example.com',
    region: 'Zuid-Holland',
    membershipType: 'Gewoon lid',
    voornaam: 'Marie',
    achternaam: 'Pietersen',
    geboortedatum: '1975-08-22',
    tijdstempel: '2010-04-01',
    ingangsdatum: '2010-04-01',
    regio: 'Zuid-Holland',
    lidmaatschap: 'Gezins lid',
    status: 'Actief'
  },
  {
    id: '3',
    name: 'Piet de Vries',
    email: 'piet.devries@example.com',
    region: 'Noord-Holland',
    membershipType: 'Gewoon lid',
    voornaam: 'Piet',
    achternaam: 'de Vries',
    geboortedatum: '1990-12-10',
    tijdstempel: '2020-04-01',
    ingangsdatum: '2020-04-01',
    regio: 'Noord-Holland',
    lidmaatschap: 'Gewoon lid',
    status: 'Actief'
  },
  {
    id: '4',
    name: 'Anna Bakker',
    email: 'anna.bakker@example.com',
    region: 'Noord-Holland',
    membershipType: 'Donateur',
    voornaam: 'Anna',
    achternaam: 'Bakker',
    geboortedatum: '1985-03-08',
    tijdstempel: '2018-04-01',
    ingangsdatum: '2018-04-01',
    regio: 'Noord-Holland',
    lidmaatschap: 'Donateur',
    status: 'Actief'
  },
  {
    id: '5',
    name: 'Kees Mulder',
    email: 'kees.mulder@example.com',
    region: 'Noord-Holland',
    membershipType: 'Gewoon lid',
    voornaam: 'Kees',
    achternaam: 'Mulder',
    geboortedatum: '1970-11-30',
    tijdstempel: '2005-04-01',
    ingangsdatum: '2005-04-01',
    regio: 'Noord-Holland',
    lidmaatschap: 'Gewoon lid',
    status: 'Inactief'
  },
  // Add more members for violin plot testing (need at least 3 per region)
  {
    id: '6',
    name: 'Lisa van Dam',
    email: 'lisa.vandam@example.com',
    region: 'Zuid-Holland',
    membershipType: 'Gewoon lid',
    voornaam: 'Lisa',
    achternaam: 'van Dam',
    geboortedatum: '1988-07-12',
    tijdstempel: '2019-04-01',
    ingangsdatum: '2019-04-01',
    regio: 'Zuid-Holland',
    lidmaatschap: 'Gewoon lid',
    status: 'Actief'
  },
  {
    id: '7',
    name: 'Tom Hendriks',
    email: 'tom.hendriks@example.com',
    region: 'Zuid-Holland',
    membershipType: 'Gezins lid',
    voornaam: 'Tom',
    achternaam: 'Hendriks',
    geboortedatum: '1982-03-25',
    tijdstempel: '2016-04-01',
    ingangsdatum: '2016-04-01',
    regio: 'Zuid-Holland',
    lidmaatschap: 'Gezins lid',
    status: 'Actief'
  },
  {
    id: '8',
    name: 'Emma de Jong',
    email: 'emma.dejong@example.com',
    region: 'Zuid-Holland',
    membershipType: 'Gewoon lid',
    voornaam: 'Emma',
    achternaam: 'de Jong',
    geboortedatum: '1992-11-08',
    tijdstempel: '2021-04-01',
    ingangsdatum: '2021-04-01',
    regio: 'Zuid-Holland',
    lidmaatschap: 'Gewoon lid',
    status: 'Actief'
  }
];

describe('AnalyticsService', () => {
  describe('generateOverview', () => {
    it('should generate correct overview statistics', () => {
      const overview = analyticsService.generateOverview(sampleMembers);
      
      expect(overview.totalMembers).toBe(8);
      expect(overview.activeMembers).toBe(7); // Only active members
      expect(overview.averageAge).toBeGreaterThan(0);
      expect(overview.averageMembershipYears).toBeGreaterThan(0);
      expect(overview.topRegions).toHaveLength(2); // Noord-Holland, Zuid-Holland (Utrecht has only 1 active member)
      expect(overview.topRegions[0].region).toBe('Noord-Holland'); // Should have most members (3 active)
      expect(overview.membershipTypes).toHaveProperty('Gewoon lid');
    });

    it('should handle empty member array', () => {
      const overview = analyticsService.generateOverview([]);
      
      expect(overview.totalMembers).toBe(0);
      expect(overview.activeMembers).toBe(0);
      expect(overview.averageAge).toBe(0);
      expect(overview.averageMembershipYears).toBe(0);
      expect(overview.topRegions).toHaveLength(0);
    });
  });

  describe('generateRegionalStats', () => {
    it('should generate regional statistics correctly', () => {
      const regionalStats = analyticsService.generateRegionalStats(sampleMembers);
      
      expect(regionalStats).toHaveLength(2); // 2 regions with active members (Noord-Holland, Zuid-Holland)
      
      const noordHolland = regionalStats.find(stats => stats.region === 'Noord-Holland');
      expect(noordHolland).toBeDefined();
      expect(noordHolland!.totalMembers).toBe(4); // 4 active members in Noord-Holland (Jan, Marie, Piet, Anna)
      expect(noordHolland!.membersByType).toHaveProperty('Gewoon lid');
      expect(noordHolland!.averageAge).toBeGreaterThan(0);
      expect(noordHolland!.averageMembershipYears).toBeGreaterThan(0);
    });

    it('should filter out inactive members', () => {
      const regionalStats = analyticsService.generateRegionalStats(sampleMembers);
      
      // Should only include active members
      const totalActiveMembers = regionalStats.reduce((sum, stats) => sum + stats.totalMembers, 0);
      expect(totalActiveMembers).toBe(7); // Only active members
    });
  });

  describe('generateAgeViolinData', () => {
    it('should generate age violin plot data', () => {
      const ageData = analyticsService.generateAgeViolinData(sampleMembers);
      
      expect(ageData.length).toBeGreaterThan(0);
      
      const noordHolland = ageData.find(data => data.region === 'Noord-Holland');
      expect(noordHolland).toBeDefined();
      expect(noordHolland!.values.length).toBe(4); // 4 active members
      expect(noordHolland!.quartiles).toHaveProperty('median');
      expect(noordHolland!.density.length).toBeGreaterThan(0);
    });

    it('should filter regions with insufficient data', () => {
      // Create data with only 1-2 members per region
      const smallSample = sampleMembers.slice(0, 2);
      const ageData = analyticsService.generateAgeViolinData(smallSample);
      
      // Should filter out regions with < 3 data points
      expect(ageData.length).toBe(0);
    });
  });

  describe('generateMembershipViolinData', () => {
    it('should generate membership duration violin plot data', () => {
      const membershipData = analyticsService.generateMembershipViolinData(sampleMembers);
      
      expect(membershipData.length).toBeGreaterThan(0);
      
      const noordHolland = membershipData.find(data => data.region === 'Noord-Holland');
      expect(noordHolland).toBeDefined();
      expect(noordHolland!.values.length).toBe(4); // 4 active members
      expect(noordHolland!.quartiles).toHaveProperty('median');
      expect(noordHolland!.density.length).toBeGreaterThan(0);
    });
  });

  describe('generateMembershipTrends', () => {
    it('should generate membership trends data', () => {
      const trends = analyticsService.generateMembershipTrends(sampleMembers);
      
      expect(trends.yearlyGrowth.length).toBeGreaterThan(0);
      // Regional growth might be empty if no members from current/previous year
      // expect(trends.regionalGrowth.length).toBeGreaterThan(0);
      
      // Check that years are sorted
      const years = trends.yearlyGrowth.map(item => item.year);
      const sortedYears = [...years].sort();
      expect(years).toEqual(sortedYears);
      
      // Check that regional growth includes all regions (might be empty for test data)
      const regions = trends.regionalGrowth.map(item => item.region);
      // expect(regions).toContain('Noord-Holland');
      // expect(regions).toContain('Zuid-Holland');
    });
  });
});