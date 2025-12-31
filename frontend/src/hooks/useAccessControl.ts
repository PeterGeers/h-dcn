/**
 * Custom hook for access control
 */

import { useState, useEffect } from 'react';
import { useToast } from '@chakra-ui/react';
import { FunctionPermissionManager, getUserRoles } from '../utils/functionPermissions';

export const useAccessControl = (user: any) => {
  const [hasAccess, setHasAccess] = useState<boolean>(false);
  const [accessLoading, setAccessLoading] = useState<boolean>(true);
  const [userRoles, setUserRoles] = useState<string[]>([]);
  const toast = useToast();

  useEffect(() => {
    const checkAccess = async () => {
      try {
        setAccessLoading(true);
        
        // Extract user roles from Cognito JWT token
        const roles = getUserRoles(user);
        setUserRoles(roles);
        console.log('🔍 ParameterManagement - User roles:', roles);
        
        // Create permission manager and check access
        const permissions = await FunctionPermissionManager.create(user);
        const canAccessParameters = permissions.hasAccess('parameters', 'read');
        
        console.log('🔍 ParameterManagement - Can access parameters:', canAccessParameters);
        
        // Additional check for administrative roles
        const hasAdminRole = roles.some(role => 
          role === 'hdcnAdmins' ||
          role === 'System_User_Management' ||
          role === 'System_CRUD_All' ||
          role === 'Webmaster' ||
          role === 'Members_CRUD_All' ||
          role === 'hdcnWebmaster' ||
          role === 'hdcnLedenadministratie' ||
          role === 'National_Chairman' ||
          role === 'National_Secretary'
        );
        
        console.log('🔍 ParameterManagement - Has admin role:', hasAdminRole);
        
        // Grant access if user has parameter permissions OR administrative roles
        const finalAccess = canAccessParameters || hasAdminRole;
        setHasAccess(finalAccess);
        
        if (!finalAccess) {
          console.log('❌ ParameterManagement - Access denied. User roles:', roles);
          toast({
            title: 'Toegang geweigerd',
            description: 'Je hebt geen toestemming om parameters te beheren. Neem contact op met een beheerder.',
            status: 'error',
            duration: 5000,
            isClosable: true
          });
        }
      } catch (error) {
        console.error('❌ ParameterManagement - Permission check failed:', error);
        setHasAccess(false);
        toast({
          title: 'Fout bij toegangscontrole',
          description: 'Er is een fout opgetreden bij het controleren van je toegangsrechten.',
          status: 'error',
          duration: 5000,
          isClosable: true
        });
      } finally {
        setAccessLoading(false);
      }
    };

    if (user) {
      checkAccess();
    } else {
      setAccessLoading(false);
      setHasAccess(false);
    }
  }, [user, toast]);

  return {
    hasAccess,
    accessLoading,
    userRoles
  };
};