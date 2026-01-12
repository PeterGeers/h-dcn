/**
 * Hook for Member DynamoDB Service
 * 
 * Hook for real-time member data from DynamoDB.
 * This is the correct hook for member administration tables.
 */

import { useState, useCallback } from 'react';
import { Member } from '../types/index';
import { MemberService, MemberListResponse } from '../services/MemberService';

interface UseMembersResult {
  members: Member[] | null;
  loading: boolean;
  error: string | null;
  loadMembers: () => Promise<void>;
  hasPermission: boolean | null;
  checkPermission: () => Promise<void>;
  refreshMembers: () => Promise<void>;
}

export const useMembers = (): UseMembersResult => {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const loadMembers = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('[useMembers] Loading members from DynamoDB');
      
      const result = await MemberService.getMembers();
      
      if (result.success) {
        setMembers(result.data);
        console.log(`[useMembers] Successfully loaded ${result.data.length} members`);
      } else {
        setError(result.error || 'Failed to load members');
        setMembers(null);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load members';
      setError(errorMessage);
      setMembers(null);
      console.error('[useMembers] Load failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkPermission = useCallback(async () => {
    try {
      const result = await MemberService.checkMemberPermission();
      setHasPermission(result.hasPermission);
      if (!result.hasPermission && result.error) {
        setError(result.error);
      }
    } catch (err) {
      setHasPermission(false);
      setError(err instanceof Error ? err.message : 'Permission check failed');
    }
  }, []);

  const refreshMembers = useCallback(async () => {
    await loadMembers();
  }, [loadMembers]);

  return {
    members,
    loading,
    error,
    loadMembers,
    hasPermission,
    checkPermission,
    refreshMembers
  };
};

export default useMembers;