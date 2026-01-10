/**
 * Google Mail Distribution Lists Service for H-DCN Reporting
 * 
 * This service handles creating and managing distribution lists in Google Contacts
 * that can be used directly in Gmail for member communications.
 * 
 * Key Features:
 * - OAuth 2.0 authentication with Google APIs
 * - Create contact groups for distribution lists
 * - Add filtered member lists to Google Contacts
 * - Regional and membership-based filtering
 * - Privacy-compliant member data handling
 * - Integration with existing export views
 */

import { Member } from '../types/index';
import { getMemberFullName } from '../utils/calculatedFields';
import { EXPORT_VIEWS, ExportViewConfig } from './MemberExportService';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface GoogleAuthConfig {
  clientId: string;
  clientSecret: string;
  redirectUri: string;
  scopes: string[];
}

export interface GoogleAuthResult {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
  user: {
    email: string;
    name?: string;
    id: string;
  };
}

export interface DistributionListConfig {
  name: string;
  description: string;
  members: Member[];
  filters?: {
    region?: string;
    status?: string;
    membership?: string;
    clubblad?: string;
  };
  includeFields: ('email' | 'name' | 'phone' | 'address')[];
}

export interface GoogleContact {
  resourceName?: string;
  names?: Array<{
    displayName: string;
    givenName?: string;
    familyName?: string;
  }>;
  emailAddresses?: Array<{
    value: string;
    type?: string;
  }>;
  phoneNumbers?: Array<{
    value: string;
    type?: string;
  }>;
  addresses?: Array<{
    formattedValue: string;
    streetAddress?: string;
    city?: string;
    postalCode?: string;
    country?: string;
  }>;
  memberships?: Array<{
    contactGroupMembership: {
      contactGroupResourceName: string;
    };
  }>;
}

export interface GoogleContactGroup {
  resourceName?: string;
  name: string;
  groupType: 'USER_CONTACT_GROUP';
  memberCount?: number;
  formattedName?: string;
}

export interface DistributionListResult {
  success: boolean;
  groupName?: string;
  groupId?: string;
  memberCount?: number;
  gmailAddress?: string;
  error?: string;
  contactsAdded?: number;
  contactsUpdated?: number;
}

// ============================================================================
// GOOGLE MAIL SERVICE CLASS
// ============================================================================

export class GoogleMailService {
  private static instance: GoogleMailService;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private expiresAt: number = 0;

  // Google APIs configuration
  private readonly config: GoogleAuthConfig = {
    clientId: process.env.REACT_APP_GOOGLE_CLIENT_ID || '',
    clientSecret: process.env.REACT_APP_GOOGLE_CLIENT_SECRET || '',
    redirectUri: `${window.location.origin}/auth/google-callback`,
    scopes: [
      'https://www.googleapis.com/auth/contacts',
      'https://www.googleapis.com/auth/contacts.readonly',
      'https://www.googleapis.com/auth/userinfo.email',
      'https://www.googleapis.com/auth/userinfo.profile'
    ]
  };

  private constructor() {
    this.loadStoredTokens();
  }

  public static getInstance(): GoogleMailService {
    if (!GoogleMailService.instance) {
      GoogleMailService.instance = new GoogleMailService();
    }
    return GoogleMailService.instance;
  }

  // ============================================================================
  // AUTHENTICATION METHODS
  // ============================================================================

  /**
   * Check if user is authenticated with Google
   */
  public isAuthenticated(): boolean {
    return !!(this.accessToken && Date.now() < this.expiresAt);
  }

  /**
   * Initiate Google OAuth flow
   */
  public initiateAuth(): void {
    const params = new URLSearchParams({
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      scope: this.config.scopes.join(' '),
      response_type: 'code',
      access_type: 'offline',
      prompt: 'consent'
    });

    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
    window.open(authUrl, 'google-auth', 'width=500,height=600');
  }

  /**
   * Handle OAuth callback and exchange code for tokens
   */
  public async handleAuthCallback(code: string): Promise<GoogleAuthResult> {
    try {
      const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          client_id: this.config.clientId,
          client_secret: this.config.clientSecret,
          code: code,
          grant_type: 'authorization_code',
          redirect_uri: this.config.redirectUri,
        }),
      });

      if (!tokenResponse.ok) {
        const errorText = await tokenResponse.text();
        throw new Error(`Token exchange failed: ${tokenResponse.status} - ${errorText}`);
      }

      const tokens = await tokenResponse.json();
      
      // Get user info
      const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (!userInfoResponse.ok) {
        throw new Error('Failed to get user info');
      }

      const userInfo = await userInfoResponse.json();

      // Store tokens
      this.accessToken = tokens.access_token;
      this.refreshToken = tokens.refresh_token;
      this.expiresAt = Date.now() + (tokens.expires_in * 1000);
      
      this.storeTokens();

      return {
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        expiresAt: this.expiresAt,
        user: {
          email: userInfo.email,
          name: userInfo.name,
          id: userInfo.id
        }
      };
    } catch (error) {
      console.error('Google auth callback error:', error);
      throw error;
    }
  }

  /**
   * Refresh access token using refresh token
   */
  private async refreshAccessToken(): Promise<void> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          client_id: this.config.clientId,
          client_secret: this.config.clientSecret,
          refresh_token: this.refreshToken,
          grant_type: 'refresh_token',
        }),
      });

      if (!response.ok) {
        throw new Error(`Token refresh failed: ${response.status}`);
      }

      const tokens = await response.json();
      this.accessToken = tokens.access_token;
      this.expiresAt = Date.now() + (tokens.expires_in * 1000);
      
      this.storeTokens();
    } catch (error) {
      console.error('Token refresh error:', error);
      this.clearTokens();
      throw error;
    }
  }

  /**
   * Ensure we have a valid access token
   */
  private async ensureValidToken(): Promise<void> {
    if (!this.accessToken) {
      throw new Error('Not authenticated with Google');
    }

    if (Date.now() >= this.expiresAt - 60000) { // Refresh 1 minute before expiry
      await this.refreshAccessToken();
    }
  }

  // ============================================================================
  // DISTRIBUTION LIST METHODS
  // ============================================================================

  /**
   * Create a distribution list from an export view
   */
  public async createDistributionListFromView(
    viewName: string,
    members: Member[],
    customName?: string
  ): Promise<DistributionListResult> {
    try {
      await this.ensureValidToken();

      const view = EXPORT_VIEWS[viewName];
      if (!view) {
        throw new Error(`Export view '${viewName}' not found`);
      }

      // Apply view filter to get relevant members
      const filteredMembers = view.filter ? members.filter(view.filter) : members;

      // Create distribution list config
      const config: DistributionListConfig = {
        name: customName || `H-DCN ${view.name}`,
        description: view.description,
        members: filteredMembers,
        includeFields: this.getFieldsForView(viewName)
      };

      return await this.createDistributionList(config);
    } catch (error) {
      console.error('Create distribution list from view error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to create distribution list'
      };
    }
  }

  /**
   * Create a custom distribution list
   */
  public async createDistributionList(config: DistributionListConfig): Promise<DistributionListResult> {
    try {
      await this.ensureValidToken();

      // Step 1: Create contact group
      const group = await this.createContactGroup(config.name, config.description);
      if (!group.resourceName) {
        throw new Error('Failed to create contact group');
      }

      // Step 2: Process members and create/update contacts
      const contactResults = await this.processMembers(config.members, group.resourceName, config.includeFields);

      // Step 3: Generate Gmail-compatible address (if possible)
      const gmailAddress = this.generateGmailAddress(group.resourceName);

      return {
        success: true,
        groupName: config.name,
        groupId: group.resourceName,
        memberCount: config.members.length,
        gmailAddress,
        contactsAdded: contactResults.added,
        contactsUpdated: contactResults.updated
      };
    } catch (error) {
      console.error('Create distribution list error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to create distribution list'
      };
    }
  }

  /**
   * Create a contact group in Google Contacts
   */
  private async createContactGroup(name: string, description?: string): Promise<GoogleContactGroup> {
    const response = await fetch('https://people.googleapis.com/v1/contactGroups', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contactGroup: {
          name: name,
          groupType: 'USER_CONTACT_GROUP'
        }
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create contact group: ${response.status} - ${errorText}`);
    }

    return await response.json();
  }

  /**
   * Process members and add them to the contact group
   */
  private async processMembers(
    members: Member[],
    groupResourceName: string,
    includeFields: ('email' | 'name' | 'phone' | 'address')[]
  ): Promise<{ added: number; updated: number }> {
    let added = 0;
    let updated = 0;

    // Process members in batches to avoid rate limits
    const batchSize = 10;
    for (let i = 0; i < members.length; i += batchSize) {
      const batch = members.slice(i, i + batchSize);
      
      for (const member of batch) {
        try {
          // Check if contact already exists
          const existingContact = await this.findContactByEmail(member.email);
          
          if (existingContact) {
            // Update existing contact and add to group
            await this.updateContactWithGroup(existingContact.resourceName!, groupResourceName);
            updated++;
          } else {
            // Create new contact
            await this.createContact(member, groupResourceName, includeFields);
            added++;
          }
        } catch (error) {
          console.warn(`Failed to process member ${getMemberFullName(member)}:`, error);
        }
      }

      // Add delay between batches to respect rate limits
      if (i + batchSize < members.length) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    return { added, updated };
  }

  /**
   * Find a contact by email address
   */
  private async findContactByEmail(email: string): Promise<GoogleContact | null> {
    if (!email) return null;

    try {
      const response = await fetch(
        `https://people.googleapis.com/v1/people:searchContacts?query=${encodeURIComponent(email)}&readMask=names,emailAddresses`,
        {
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
          },
        }
      );

      if (!response.ok) {
        return null;
      }

      const result = await response.json();
      const contacts = result.results || [];
      
      // Find exact email match
      for (const contact of contacts) {
        const person = contact.person;
        if (person.emailAddresses) {
          for (const emailAddr of person.emailAddresses) {
            if (emailAddr.value.toLowerCase() === email.toLowerCase()) {
              return person;
            }
          }
        }
      }

      return null;
    } catch (error) {
      console.warn('Error searching for contact:', error);
      return null;
    }
  }

  /**
   * Create a new contact
   */
  private async createContact(
    member: Member,
    groupResourceName: string,
    includeFields: ('email' | 'name' | 'phone' | 'address')[]
  ): Promise<GoogleContact> {
    const contact: GoogleContact = {
      memberships: [{
        contactGroupMembership: {
          contactGroupResourceName: groupResourceName
        }
      }]
    };

    // Add name if requested
    if (includeFields.includes('name') && getMemberFullName(member)) {
      contact.names = [{
        displayName: getMemberFullName(member),
        givenName: member.voornaam || '',
        familyName: member.achternaam || ''
      }];
    }

    // Add email if requested and available
    if (includeFields.includes('email') && member.email) {
      contact.emailAddresses = [{
        value: member.email,
        type: 'home'
      }];
    }

    // Add phone if requested and available
    if (includeFields.includes('phone') && member.telefoon) {
      contact.phoneNumbers = [{
        value: member.telefoon,
        type: 'home'
      }];
    }

    // Add address if requested and available
    if (includeFields.includes('address') && (member.straat || member.woonplaats)) {
      const addressParts = [
        member.straat,
        member.postcode,
        member.woonplaats,
        member.land || 'Nederland'
      ].filter(Boolean);

      contact.addresses = [{
        formattedValue: addressParts.join(', '),
        streetAddress: member.straat || '',
        city: member.woonplaats || '',
        postalCode: member.postcode || '',
        country: member.land || 'Nederland'
      }];
    }

    const response = await fetch('https://people.googleapis.com/v1/people:createContact', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(contact),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create contact: ${response.status} - ${errorText}`);
    }

    return await response.json();
  }

  /**
   * Update existing contact to add to group
   */
  private async updateContactWithGroup(contactResourceName: string, groupResourceName: string): Promise<void> {
    const response = await fetch(`https://people.googleapis.com/v1/${contactResourceName}:updateContactPhoto`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contactGroupMembership: {
          contactGroupResourceName: groupResourceName
        }
      }),
    });

    if (!response.ok) {
      // Try alternative method - modify contact group membership
      await this.addContactToGroup(contactResourceName, groupResourceName);
    }
  }

  /**
   * Add contact to group using group modification
   */
  private async addContactToGroup(contactResourceName: string, groupResourceName: string): Promise<void> {
    const response = await fetch(`https://people.googleapis.com/v1/${groupResourceName}/members:modify`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        resourceNamesToAdd: [contactResourceName]
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.warn(`Failed to add contact to group: ${response.status} - ${errorText}`);
    }
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Get appropriate fields for an export view
   */
  private getFieldsForView(viewName: string): ('email' | 'name' | 'phone' | 'address')[] {
    switch (viewName) {
      case 'emailGroupsDigital':
      case 'emailGroupsRegional':
        return ['name', 'email'];
      case 'addressStickersPaper':
      case 'addressStickersRegional':
        return ['name', 'email', 'address'];
      case 'birthdayList':
        return ['name', 'email', 'phone', 'address'];
      default:
        return ['name', 'email'];
    }
  }

  /**
   * Generate Gmail-compatible address (note: this is conceptual as Google doesn't provide direct group emails)
   */
  private generateGmailAddress(groupResourceName: string): string {
    // Extract group ID from resource name
    const groupId = groupResourceName.split('/').pop() || 'unknown';
    return `group-${groupId}@contacts.google.com`;
  }

  /**
   * Get list of available distribution list templates
   */
  public getDistributionListTemplates(): Array<{
    key: string;
    name: string;
    description: string;
    useCase: string;
  }> {
    return [
      {
        key: 'emailGroupsDigital',
        name: 'Digital Clubblad Recipients',
        description: 'Members who receive the digital clubblad',
        useCase: 'Newsletter distribution, digital communications'
      },
      {
        key: 'emailGroupsRegional',
        name: 'Regional Communication List',
        description: 'Members in your region for local communications',
        useCase: 'Regional events, local announcements'
      },
      {
        key: 'addressStickersPaper',
        name: 'Paper Clubblad Recipients',
        description: 'Members who receive the paper clubblad',
        useCase: 'Physical mail distribution, address labels'
      },
      {
        key: 'birthdayList',
        name: 'Birthday Contact List',
        description: 'All active members with contact information',
        useCase: 'Birthday cards, personal communications'
      }
    ];
  }

  /**
   * Logout and clear stored tokens
   */
  public logout(): void {
    this.clearTokens();
  }

  // ============================================================================
  // TOKEN STORAGE METHODS
  // ============================================================================

  private storeTokens(): void {
    if (this.accessToken) {
      localStorage.setItem('google_access_token', this.accessToken);
      localStorage.setItem('google_expires_at', this.expiresAt.toString());
    }
    if (this.refreshToken) {
      localStorage.setItem('google_refresh_token', this.refreshToken);
    }
  }

  private loadStoredTokens(): void {
    this.accessToken = localStorage.getItem('google_access_token');
    this.refreshToken = localStorage.getItem('google_refresh_token');
    const expiresAt = localStorage.getItem('google_expires_at');
    this.expiresAt = expiresAt ? parseInt(expiresAt) : 0;
  }

  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.expiresAt = 0;
    localStorage.removeItem('google_access_token');
    localStorage.removeItem('google_refresh_token');
    localStorage.removeItem('google_expires_at');
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const googleMailService = GoogleMailService.getInstance();
export default GoogleMailService;