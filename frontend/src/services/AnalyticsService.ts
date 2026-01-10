/**
 * Analytics Service for H-DCN Member Reporting
 * 
 * This service processes parquet member data to generate analytics and statistics
 * for regional reporting, age distributions, and membership trends.
 */

import { Member } from '../types/index';
import { computeCalculatedFieldsForArray } from '../utils/calculatedFields';

// ============================================================================
// TYPES
// ============================================================================

export interface RegionalStats {
  region: string;
  totalMembers: number;
  membersByType: Record<string, number>;
  averageAge: number;
  averageMembershipYears: number;
  ageDistribution: {
    under30: number;
    age30to50: number;
    age50to65: number;
    over65: number;
  };
  membershipDistribution: {
    under5years: number;
    years5to10: number;
    years10to20: number;
    over20years: number;
  };
}

export interface ViolinPlotData {
  region: string;
  values: number[];
  quartiles: {
    q1: number;
    median: number;
    q3: number;
    min: number;
    max: number;
  };
  density: Array<{
    value: number;
    density: number;
  }>;
}

export interface MembershipTrends {
  yearlyGrowth: Array<{
    year: number;
    newMembers: number;
    totalMembers: number;
    growthRate: number;
  }>;
  regionalGrowth: Array<{
    region: string;
    currentYear: number;
    previousYear: number;
    growthRate: number;
  }>;
}

export interface AnalyticsOverview {
  totalMembers: number;
  activeMembers: number;
  averageAge: number;
  averageMembershipYears: number;
  topRegions: Array<{
    region: string;
    memberCount: number;
    percentage: number;
  }>;
  membershipTypes: Record<string, number>;
}

// ============================================================================
// ANALYTICS SERVICE CLASS
// ============================================================================

export class AnalyticsService {
  private static instance: AnalyticsService;

  private constructor() {}

  public static getInstance(): AnalyticsService {
    if (!AnalyticsService.instance) {
      AnalyticsService.instance = new AnalyticsService();
    }
    return AnalyticsService.instance;
  }

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  private log(message: string, data?: any): void {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[AnalyticsService] ${message}`, data || '');
    }
  }

  private calculateQuartiles(values: number[]): ViolinPlotData['quartiles'] {
    if (values.length === 0) {
      return { q1: 0, median: 0, q3: 0, min: 0, max: 0 };
    }

    const sorted = [...values].sort((a, b) => a - b);
    const n = sorted.length;

    const q1Index = Math.floor(n * 0.25);
    const medianIndex = Math.floor(n * 0.5);
    const q3Index = Math.floor(n * 0.75);

    return {
      q1: sorted[q1Index] || 0,
      median: sorted[medianIndex] || 0,
      q3: sorted[q3Index] || 0,
      min: sorted[0] || 0,
      max: sorted[n - 1] || 0
    };
  }

  private calculateDensity(values: number[], bins: number = 20): Array<{ value: number; density: number }> {
    if (values.length === 0) return [];

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    const binWidth = range / bins;

    if (binWidth === 0) {
      return [{ value: min, density: 1 }];
    }

    const histogram = new Array(bins).fill(0);
    
    values.forEach(value => {
      const binIndex = Math.min(Math.floor((value - min) / binWidth), bins - 1);
      histogram[binIndex]++;
    });

    // Normalize to density
    const total = values.length;
    return histogram.map((count, index) => ({
      value: min + (index + 0.5) * binWidth,
      density: count / total
    }));
  }

  // ============================================================================
  // MAIN ANALYTICS FUNCTIONS
  // ============================================================================

  /**
   * Generate overview analytics from member data
   */
  public generateOverview(rawMembers: Member[]): AnalyticsOverview {
    this.log(`Generating overview analytics for ${rawMembers.length} members`);

    // Apply calculated fields
    const members = computeCalculatedFieldsForArray(rawMembers);

    // Filter active members
    const activeMembers = members.filter(member => 
      member.status === 'Actief' || member.status === 'Active'
    );

    // Calculate averages
    const ages = members
      .map(member => member.leeftijd)
      .filter((age): age is number => typeof age === 'number' && age > 0);
    
    const membershipYears = members
      .map(member => member.jaren_lid)
      .filter((years): years is number => typeof years === 'number' && years >= 0);

    const averageAge = ages.length > 0 ? ages.reduce((sum, age) => sum + age, 0) / ages.length : 0;
    const averageMembershipYears = membershipYears.length > 0 
      ? membershipYears.reduce((sum, years) => sum + years, 0) / membershipYears.length 
      : 0;

    // Count by region
    const regionCounts: Record<string, number> = {};
    activeMembers.forEach(member => {
      const region = member.regio || member.region || 'Onbekend';
      regionCounts[region] = (regionCounts[region] || 0) + 1;
    });

    // Top regions
    const topRegions = Object.entries(regionCounts)
      .map(([region, count]) => ({
        region,
        memberCount: count,
        percentage: (count / activeMembers.length) * 100
      }))
      .sort((a, b) => b.memberCount - a.memberCount)
      .slice(0, 5);

    // Membership types
    const membershipTypes: Record<string, number> = {};
    activeMembers.forEach(member => {
      const type = member.lidmaatschap || 'Onbekend';
      membershipTypes[type] = (membershipTypes[type] || 0) + 1;
    });

    return {
      totalMembers: members.length,
      activeMembers: activeMembers.length,
      averageAge: Math.round(averageAge * 10) / 10,
      averageMembershipYears: Math.round(averageMembershipYears * 10) / 10,
      topRegions,
      membershipTypes
    };
  }

  /**
   * Generate regional statistics from member data
   */
  public generateRegionalStats(rawMembers: Member[]): RegionalStats[] {
    this.log(`Generating regional statistics for ${rawMembers.length} members`);

    // Apply calculated fields
    const members = computeCalculatedFieldsForArray(rawMembers);

    // Filter active members
    const activeMembers = members.filter(member => 
      member.status === 'Actief' || member.status === 'Active'
    );

    // Group by region
    const regionGroups: Record<string, Member[]> = {};
    activeMembers.forEach(member => {
      const region = member.regio || member.region || 'Onbekend';
      if (!regionGroups[region]) {
        regionGroups[region] = [];
      }
      regionGroups[region].push(member);
    });

    // Generate stats for each region
    return Object.entries(regionGroups).map(([region, regionMembers]) => {
      // Count by membership type
      const membersByType: Record<string, number> = {};
      regionMembers.forEach(member => {
        const type = member.lidmaatschap || 'Onbekend';
        membersByType[type] = (membersByType[type] || 0) + 1;
      });

      // Calculate averages
      const ages = regionMembers
        .map(member => member.leeftijd)
        .filter((age): age is number => typeof age === 'number' && age > 0);
      
      const membershipYears = regionMembers
        .map(member => member.jaren_lid)
        .filter((years): years is number => typeof years === 'number' && years >= 0);

      const averageAge = ages.length > 0 ? ages.reduce((sum, age) => sum + age, 0) / ages.length : 0;
      const averageMembershipYears = membershipYears.length > 0 
        ? membershipYears.reduce((sum, years) => sum + years, 0) / membershipYears.length 
        : 0;

      // Age distribution
      const ageDistribution = {
        under30: ages.filter(age => age < 30).length,
        age30to50: ages.filter(age => age >= 30 && age < 50).length,
        age50to65: ages.filter(age => age >= 50 && age < 65).length,
        over65: ages.filter(age => age >= 65).length
      };

      // Membership duration distribution
      const membershipDistribution = {
        under5years: membershipYears.filter(years => years < 5).length,
        years5to10: membershipYears.filter(years => years >= 5 && years < 10).length,
        years10to20: membershipYears.filter(years => years >= 10 && years < 20).length,
        over20years: membershipYears.filter(years => years >= 20).length
      };

      return {
        region,
        totalMembers: regionMembers.length,
        membersByType,
        averageAge: Math.round(averageAge * 10) / 10,
        averageMembershipYears: Math.round(averageMembershipYears * 10) / 10,
        ageDistribution,
        membershipDistribution
      };
    }).sort((a, b) => b.totalMembers - a.totalMembers);
  }

  /**
   * Generate violin plot data for age distribution by region
   */
  public generateAgeViolinData(rawMembers: Member[]): ViolinPlotData[] {
    this.log(`Generating age violin plot data for ${rawMembers.length} members`);

    // Apply calculated fields
    const members = computeCalculatedFieldsForArray(rawMembers);

    // Filter active members with valid ages
    const activeMembers = members.filter(member => 
      (member.status === 'Actief' || member.status === 'Active') &&
      typeof member.leeftijd === 'number' && member.leeftijd > 0
    );

    // Group by region
    const regionGroups: Record<string, number[]> = {};
    activeMembers.forEach(member => {
      const region = member.regio || member.region || 'Onbekend';
      if (!regionGroups[region]) {
        regionGroups[region] = [];
      }
      regionGroups[region].push(member.leeftijd as number);
    });

    // Generate violin data for each region
    return Object.entries(regionGroups)
      .filter(([_, ages]) => ages.length >= 3) // Need at least 3 data points for meaningful violin plot
      .map(([region, ages]) => ({
        region,
        values: ages,
        quartiles: this.calculateQuartiles(ages),
        density: this.calculateDensity(ages)
      }))
      .sort((a, b) => b.values.length - a.values.length);
  }

  /**
   * Generate violin plot data for membership duration by region
   */
  public generateMembershipViolinData(rawMembers: Member[]): ViolinPlotData[] {
    this.log(`Generating membership violin plot data for ${rawMembers.length} members`);

    // Apply calculated fields
    const members = computeCalculatedFieldsForArray(rawMembers);

    // Filter active members with valid membership years
    const activeMembers = members.filter(member => 
      (member.status === 'Actief' || member.status === 'Active') &&
      typeof member.jaren_lid === 'number' && member.jaren_lid >= 0
    );

    // Group by region
    const regionGroups: Record<string, number[]> = {};
    activeMembers.forEach(member => {
      const region = member.regio || member.region || 'Onbekend';
      if (!regionGroups[region]) {
        regionGroups[region] = [];
      }
      regionGroups[region].push(member.jaren_lid as number);
    });

    // Generate violin data for each region
    return Object.entries(regionGroups)
      .filter(([_, years]) => years.length >= 3) // Need at least 3 data points for meaningful violin plot
      .map(([region, years]) => ({
        region,
        values: years,
        quartiles: this.calculateQuartiles(years),
        density: this.calculateDensity(years)
      }))
      .sort((a, b) => b.values.length - a.values.length);
  }

  /**
   * Generate membership trends over time
   */
  public generateMembershipTrends(rawMembers: Member[]): MembershipTrends {
    this.log(`Generating membership trends for ${rawMembers.length} members`);

    // Apply calculated fields
    const members = computeCalculatedFieldsForArray(rawMembers);

    // Group by registration year
    const yearGroups: Record<number, Member[]> = {};
    members.forEach(member => {
      const year = member.aanmeldingsjaar;
      if (typeof year === 'number' && year > 1900 && year <= new Date().getFullYear()) {
        if (!yearGroups[year]) {
          yearGroups[year] = [];
        }
        yearGroups[year].push(member);
      }
    });

    // Calculate yearly growth
    const years = Object.keys(yearGroups).map(Number).sort();
    let cumulativeMembers = 0;
    const yearlyGrowth = years.map((year, index) => {
      const newMembers = yearGroups[year].length;
      cumulativeMembers += newMembers;
      const previousYear = index > 0 ? years[index - 1] : year;
      const previousTotal = index > 0 ? cumulativeMembers - newMembers : 0;
      const growthRate = previousTotal > 0 ? ((newMembers / previousTotal) * 100) : 0;

      return {
        year,
        newMembers,
        totalMembers: cumulativeMembers,
        growthRate: Math.round(growthRate * 10) / 10
      };
    });

    // Calculate regional growth (current year vs previous year)
    const currentYear = new Date().getFullYear();
    const previousYear = currentYear - 1;

    const currentYearMembers = members.filter(member => member.aanmeldingsjaar === currentYear);
    const previousYearMembers = members.filter(member => member.aanmeldingsjaar === previousYear);

    const currentRegionCounts: Record<string, number> = {};
    const previousRegionCounts: Record<string, number> = {};

    currentYearMembers.forEach(member => {
      const region = member.regio || member.region || 'Onbekend';
      currentRegionCounts[region] = (currentRegionCounts[region] || 0) + 1;
    });

    previousYearMembers.forEach(member => {
      const region = member.regio || member.region || 'Onbekend';
      previousRegionCounts[region] = (previousRegionCounts[region] || 0) + 1;
    });

    const allRegions = new Set([...Object.keys(currentRegionCounts), ...Object.keys(previousRegionCounts)]);
    const regionalGrowth = Array.from(allRegions).map(region => {
      const current = currentRegionCounts[region] || 0;
      const previous = previousRegionCounts[region] || 0;
      const growthRate = previous > 0 ? ((current - previous) / previous) * 100 : (current > 0 ? 100 : 0);

      return {
        region,
        currentYear: current,
        previousYear: previous,
        growthRate: Math.round(growthRate * 10) / 10
      };
    }).sort((a, b) => b.growthRate - a.growthRate);

    return {
      yearlyGrowth,
      regionalGrowth
    };
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const analyticsService = AnalyticsService.getInstance();
export default AnalyticsService;