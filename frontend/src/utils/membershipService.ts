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
 * Uses self-lookup endpoint for authenticated users with proper role validation
 */
export const getMemberByEmail = async (email: string): Promise<any> => {
  try {
    // Check if user is authenticated and has valid roles
    if (!ApiService.isAuthenticated()) {
      console.log('User not authenticated, cannot check member status');
      return null;
    }

    const currentUserEmail = ApiService.getCurrentUserEmail();
    const userRoles = ApiService.getCurrentUserRoles();
    
    // Validate that the user is checking their own email
    if (currentUserEmail !== email) {
      console.error('User can only check their own member record');
      return null;
    }

    // Check if user has valid roles (verzoek_lid or hdcnLeden)
    const hasValidRole = userRoles.some(role => 
      role === 'verzoek_lid' || role === 'hdcnLeden'
    );

    if (!hasValidRole) {
      console.log('User does not have valid role (verzoek_lid or hdcnLeden) for member lookup');
      return null;
    }

    console.log('Performing self-lookup for user with roles:', userRoles);

    // Use the self-lookup endpoint
    const response = await ApiService.get('/members/me');
    
    if (!response.success) {
      // For verzoek_lid users, not having a record yet is normal
      if (userRoles.includes('verzoek_lid') && !userRoles.includes('hdcnLeden')) {
        console.log('verzoek_lid user not found in members table - this is expected for new applicants');
        return null;
      }
      
      // For hdcnLeden users, this is unexpected
      if (userRoles.includes('hdcnLeden')) {
        console.error('hdcnLeden user not found in members table - this should not happen');
      }
      
      throw new Error(response.error || 'Failed to get member record');
    }
    
    return response.data || null;
  } catch (error) {
    console.error('Error checking existing member:', error);
    
    // Get user roles for better error handling
    const userRoles = ApiService.getCurrentUserRoles();
    
    // For verzoek_lid users, API errors might be expected (no record yet)
    if (userRoles.includes('verzoek_lid') && !userRoles.includes('hdcnLeden')) {
      console.log('API error for verzoek_lid user - likely no member record exists yet');
      return null;
    }
    
    // For hdcnLeden users, API errors are more concerning
    if (userRoles.includes('hdcnLeden')) {
      console.error('API error for hdcnLeden user - this may indicate a system issue');
    }
    
    return null;
  }
};

/**
 * Submit a new membership application with Cognito integration
 * Now uses /members/me POST endpoint for self-service member creation
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

    // Submit the application using /members/me POST endpoint
    const response = await ApiService.post('/members/me', submissionData);
    
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

    return response.data.member || response.data;
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