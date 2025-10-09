import React, { useState, useEffect } from 'react';
import { FunctionPermissionManager } from '../utils/functionPermissions';

export function FunctionGuard({ 
  user, 
  children, 
  functionName, 
  action = 'read',
  fallback = null 
}) {
  const [hasAccess, setHasAccess] = useState(false);
  const [loading, setLoading] = useState(true);

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