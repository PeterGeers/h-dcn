import React, { useState, useEffect, ReactNode } from 'react';
import { FunctionPermissionManager } from '../../utils/functionPermissions';

interface FunctionGuardProps {
  user: any; // TODO: Add proper User type
  children: ReactNode;
  functionName: string;
  action?: 'read' | 'write';
  fallback?: ReactNode;
}

export function FunctionGuard({ 
  user, 
  children, 
  functionName, 
  action = 'read',
  fallback = null 
}: FunctionGuardProps) {
  const [hasAccess, setHasAccess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const checkAccess = async () => {
      try {
        const permissions = await FunctionPermissionManager.create(user);
        setHasAccess(permissions.hasAccess(functionName, action));
      } catch (error) {
        console.error('Permission check failed:', error);
        // Fallback: Allow access for admins, deny for others
        const userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
        const isAdmin = userGroups.includes('hdcnAdmins');
        setHasAccess(isAdmin);
      } finally {
        setLoading(false);
      }
    };

    checkAccess();
  }, [user, functionName, action]);

  if (loading) return null;
  return hasAccess ? children : fallback;
}