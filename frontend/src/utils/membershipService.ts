/**
 * Membership Service - API calls for membership applications
 */

import { apiCall } from './errorHandler';
import { API_URLS } from '../config/api';
import { getAuthHeaders, getAuthHeadersForGet } from './authHeaders';
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
 */
export const getMemberByEmail = async (email: string): Promise<any> => {
  try {
    const headers = await getAuthHeadersForGet();
    const allMembers = await apiCall<any>(
      fetch(API_URLS.members(), { headers }),
      'controleren bestaand lid'
    );
    
    const memberData = Array.isArray(allMembers) ? allMembers : (allMembers?.members || []);
    const existingMember = memberData.find((m: any) => m.email === email);
    
    return existingMember || null;
  } catch (error) {
    console.error('Error checking existing member:', error);
    return null;
  }
};

/**
 * Submit a new membership application with Cognito integration
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

    // Submit the application to the database
    const result = await apiCall(
      fetch(API_URLS.members(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(await getAuthHeaders())
        },
        body: JSON.stringify(submissionData)
      }),
      'aanmelden nieuw lid'
    );

    // Send confirmation and admin notification emails
    try {
      await emailService.sendMembershipApplicationEmails(submissionData, MEMBERSHIP_EMAIL_CONFIG);
      console.log('✅ Membership application emails sent successfully');
    } catch (emailError) {
      console.error('⚠️ Application submitted but email sending failed:', emailError);
      // Don't throw error - application was successful even if emails failed
    }

    return result;
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
 */
export const getMembershipApplicationStatus = async (applicationId: string): Promise<any> => {
  try {
    const headers = await getAuthHeadersForGet();
    const member = await apiCall<any>(
      fetch(API_URLS.member(applicationId), { headers }),
      'ophalen aanmeldingsstatus'
    );
    
    return member;
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