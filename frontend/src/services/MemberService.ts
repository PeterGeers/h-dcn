/**
 * Member Service - DynamoDB Integration
 * 
 * Service for real-time member data from DynamoDB.
 * This is the correct service for member administration tables.
 */

import { ApiService } from './apiService';
import { Member } from '../types/index';

export interface MemberListResponse {
  success: boolean;
  data: Member[];
  error?: string;
}

export interface MemberResponse {
  success: boolean;
  data: Member;
  error?: string;
}

export class MemberService {
  /**
   * Get all members from DynamoDB
   * 
   * This calls the /members endpoint which uses the get_members handler.
   * It provides real-time data with regional filtering and permissions.
   */
  static async getMembers(): Promise<MemberListResponse> {
    try {
      console.log('[MemberService] Fetching members from DynamoDB');
      
      const response = await ApiService.get<Member[]>('/members');
      
      if (!response.success) {
        return {
          success: false,
          data: [],
          error: response.error || 'Failed to fetch members'
        };
      }

      const members = response.data || [];
      console.log(`[MemberService] Successfully fetched ${members.length} members`);
      
      return {
        success: true,
        data: members
      };

    } catch (error) {
      console.error('[MemberService] Error fetching members:', error);
      return {
        success: false,
        data: [],
        error: error instanceof Error ? error.message : 'Failed to fetch members'
      };
    }
  }

  /**
   * Get a specific member by ID
   */
  static async getMember(memberId: string): Promise<MemberResponse> {
    try {
      console.log(`[MemberService] Fetching member ${memberId}`);
      
      const response = await ApiService.get<Member>(`/members/${memberId}`);
      
      if (!response.success) {
        return {
          success: false,
          data: {} as Member,
          error: response.error || 'Failed to fetch member'
        };
      }

      return {
        success: true,
        data: response.data
      };

    } catch (error) {
      console.error(`[MemberService] Error fetching member ${memberId}:`, error);
      return {
        success: false,
        data: {} as Member,
        error: error instanceof Error ? error.message : 'Failed to fetch member'
      };
    }
  }

  /**
   * Update a member
   */
  static async updateMember(memberId: string, memberData: Partial<Member>): Promise<MemberResponse> {
    try {
      console.log(`[MemberService] Updating member ${memberId}`);
      
      const response = await ApiService.put<Member>(`/members/${memberId}`, memberData);
      
      if (!response.success) {
        return {
          success: false,
          data: {} as Member,
          error: response.error || 'Failed to update member'
        };
      }

      return {
        success: true,
        data: response.data
      };

    } catch (error) {
      console.error(`[MemberService] Error updating member ${memberId}:`, error);
      return {
        success: false,
        data: {} as Member,
        error: error instanceof Error ? error.message : 'Failed to update member'
      };
    }
  }

  /**
   * Create a new member
   */
  static async createMember(memberData: Omit<Member, 'member_id'>): Promise<MemberResponse> {
    try {
      console.log('[MemberService] Creating new member');
      
      const response = await ApiService.post<Member>('/members', memberData);
      
      if (!response.success) {
        return {
          success: false,
          data: {} as Member,
          error: response.error || 'Failed to create member'
        };
      }

      return {
        success: true,
        data: response.data
      };

    } catch (error) {
      console.error('[MemberService] Error creating member:', error);
      return {
        success: false,
        data: {} as Member,
        error: error instanceof Error ? error.message : 'Failed to create member'
      };
    }
  }

  /**
   * Delete a member
   */
  static async deleteMember(memberId: string): Promise<{ success: boolean; error?: string }> {
    try {
      console.log(`[MemberService] Deleting member ${memberId}`);
      
      const response = await ApiService.delete(`/members/${memberId}`);
      
      if (!response.success) {
        return {
          success: false,
          error: response.error || 'Failed to delete member'
        };
      }

      return {
        success: true
      };

    } catch (error) {
      console.error(`[MemberService] Error deleting member ${memberId}:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to delete member'
      };
    }
  }

  /**
   * Check if the current user has permission to access members
   */
  static async checkMemberPermission(): Promise<{ hasPermission: boolean; error?: string }> {
    try {
      // Try to make a request to see if we have permission
      // The backend will return 403 if no permission
      const response = await ApiService.get('/members');
      
      return {
        hasPermission: response.success
      };
    } catch (error) {
      return {
        hasPermission: false,
        error: error instanceof Error ? error.message : 'Permission check failed'
      };
    }
  }
}

export default MemberService;