/**
 * Membership Service - API calls for membership applications
 * Updated to use main ApiService for authentication
 * I am not sure if it matters but these 2 fields should belong to membership  status?: string;
  tijdstempel?: string; 
 */

import { apiCall } from './errorHandler';
import { API_URLS } from '../config/api';
import { ApiService } from '../services/apiService';
import { emailService } from './emailService';
import { MEMBERSHIP_EMAIL_CONFIG } from '../config/memberFields';

export interface MembershipApplicationData {
  // Personal Information
  voornaam: string;
  tussenvoegsel?: string;
  achternaam: string;
  geboortedatum: string;
  geslacht: string;
  email: string;
  telefoon: string;
  nationaliteit?: string;
  minderjarigNaam?: string;
  
  // Address
  straat: string;
  postcode: string;
  woonplaats: string;
  land: string;
  
  // Membership
  lidmaatschap: string;
  regio: string;
  wiewatwaar: string;
  
  // Motor (conditional)
  motormerk?: string;
  motortype?: string;
  bouwjaar?: number;
  kenteken?: string;
  
  // Preferences
  clubblad: string;
  nieuwsbrief: string;
  privacy: string;
  
  // Payment
  betaalwijze: string;
  bankrekeningnummer?: string;
  
  // Agreement
  akkoord: boolean;
  
  // System fields
  status?: string;
  tijdstempel?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Check if a user already exists as a member by email
 * Now uses main ApiService for authentication
 */
export const getMemberByEmail = async (email: string): Promise<any> => {
  try {
    const response = await ApiService.get('/members');
    
    if (!response.success) {
      throw new Error(response.error || 'Failed to get members');
    }
    
    const memberData = Array.isArray(response.data) ? response.data : (response.data?.members || []);
    const existingMember = memberData.find((m: any) => m.email === email);
    
    return existingMember || null;
  } catch (error) {
    console.error('Error checking existing member:', error);
    return null;
  }
};

/**
 * Submit a new membership application with Cognito integration
 * Now uses main ApiService for authentication
 */
export const submitMembershipApplication = async (data: any): Promise<any> => {
  try {
    const submissionData = {
      ...data,
      status: 'Aangemeld',
      tijdstempel: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    // Submit the application to the database using main ApiService
    const response = await ApiService.post('/members', submissionData);
    
    if (!response.success) {
      throw new Error(response.error || 'Failed to submit membership application');
    }

    // Send confirmation and admin notification emails
    try {
      await emailService.sendMembershipApplicationEmails(submissionData, MEMBERSHIP_EMAIL_CONFIG);
      console.log('✅ Membership application emails sent successfully');
    } catch (emailError) {
      console.error('⚠️ Application submitted but email sending failed:', emailError);
      // Don't throw error - application was successful even if emails failed
    }

    return response.data;
  } catch (error) {
    console.error('Error submitting membership application:', error);
    throw error;
  }
};

/**
 * Check if a user already exists as a member
 */
export const checkExistingMember = async (email: string): Promise<any> => {
  return getMemberByEmail(email);
};

/**
 * Get membership application status
 * Now uses main ApiService for authentication
 */
export const getMembershipApplicationStatus = async (applicationId: string): Promise<any> => {
  try {
    const response = await ApiService.get(`/members/${applicationId}`);
    
    if (!response.success) {
      throw new Error(response.error || 'Failed to get application status');
    }
    
    return response.data;
  } catch (error) {
    console.error('Error getting application status:', error);
    throw error;
  }
};

// Default export with all methods
export const membershipService = {
  submitMembershipApplication,
  getMemberByEmail,
  checkExistingMember,
  getMembershipApplicationStatus
};