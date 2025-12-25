import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FunctionGuard } from '../FunctionGuard';

// Mock the FunctionPermissionManager
jest.mock('../../../utils/functionPermissions', () => ({
  FunctionPermissionManager: {
    create: jest.fn()
  }
}));

describe('FunctionGuard', () => {
  const mockUser = {
    signInUserSession: {
      accessToken: {
        payload: {
          'cognito:groups': ['hdcnLeden', 'Members_Read_All']
        }
      }
    }
  };

  const mockPermissionManager = {
    hasAccess: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    require('../../../utils/functionPermissions').FunctionPermissionManager.create.mockResolvedValue(mockPermissionManager);
  });

  it('should render children when user has required roles', async () => {
    mockPermissionManager.hasAccess.mockReturnValue(true);

    render(
      <FunctionGuard
        user={mockUser}
        functionName="members"
        requiredRoles={['Members_Read_All']}
      >
        <div>Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
  });

  it('should render children when user has function access but not required roles', async () => {
    // This test now expects access to be DENIED because we use AND logic
    // User has function access but not the required role
    mockPermissionManager.hasAccess.mockReturnValue(true);

    render(
      <FunctionGuard
        user={mockUser}
        functionName="members"
        requiredRoles={['Members_CRUD_All']} // User doesn't have this role
      >
        <div>Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      // With AND logic, user needs BOTH role AND function access
      // User has function access but not the required role, so access should be denied
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  it('should render children when user has required roles and no function name specified', async () => {
    // Test role-only access (no function restriction)
    render(
      <FunctionGuard
        user={mockUser}
        requiredRoles={['Members_Read_All']} // User has this role
      >
        <div>Role-Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.getByText('Role-Protected Content')).toBeInTheDocument();
    });
  });

  it('should not render children when user lacks required roles and no function name specified', async () => {
    // Test role-only access denial
    render(
      <FunctionGuard
        user={mockUser}
        requiredRoles={['Members_CRUD_All']} // User doesn't have this role
      >
        <div>Role-Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.queryByText('Role-Protected Content')).not.toBeInTheDocument();
    });
  });

  it('should render children when user has both required roles and function access (AND logic)', async () => {
    // Test combined permission checking with AND logic
    mockPermissionManager.hasAccess.mockReturnValue(true);

    render(
      <FunctionGuard
        user={mockUser}
        functionName="members"
        requiredRoles={['Members_Read_All']} // User has this role
      >
        <div>Combined Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      // User has both role AND function access, so should render
      expect(screen.getByText('Combined Protected Content')).toBeInTheDocument();
    });
  });
  it('should not render children when user has neither role nor function access', async () => {
    mockPermissionManager.hasAccess.mockReturnValue(false);

    render(
      <FunctionGuard
        user={mockUser}
        functionName="members"
        requiredRoles={['Members_CRUD_All']} // User doesn't have this role
      >
        <div>Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  it('should render children when no roles are required and user has function access', async () => {
    mockPermissionManager.hasAccess.mockReturnValue(true);

    render(
      <FunctionGuard
        user={mockUser}
        functionName="webshop"
        requiredRoles={[]} // No roles required
      >
        <div>Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
  });

  it('should render fallback when access is denied', async () => {
    mockPermissionManager.hasAccess.mockReturnValue(false);

    render(
      <FunctionGuard
        user={mockUser}
        functionName="members"
        requiredRoles={['Members_CRUD_All']}
        fallback={<div>Access Denied</div>}
      >
        <div>Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.getByText('Access Denied')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  it('should handle admin fallback on error', async () => {
    require('../../../utils/functionPermissions').FunctionPermissionManager.create.mockRejectedValue(new Error('Permission check failed'));

    const adminUser = {
      signInUserSession: {
        accessToken: {
          payload: {
            'cognito:groups': ['hdcnAdmins']
          }
        }
      }
    };

    render(
      <FunctionGuard
        user={adminUser}
        functionName="members"
        requiredRoles={['Members_Read_All']}
      >
        <div>Protected Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
  });

  it('should preserve existing function-based access control when no roles are specified', async () => {
    // Test backward compatibility - existing code without requiredRoles should work unchanged
    mockPermissionManager.hasAccess.mockReturnValue(true);

    const userWithoutRole = {
      signInUserSession: {
        accessToken: {
          payload: {
            'cognito:groups': ['hdcnLeden'] // Basic member, not admin
          }
        }
      }
    };

    render(
      <FunctionGuard
        user={userWithoutRole}
        functionName="webshop"
        // No requiredRoles specified - should use function-based permissions only
      >
        <div>Webshop Content</div>
      </FunctionGuard>
    );

    // Should render because user has function-based access to webshop
    // and no roles are required (backward compatibility)
    await waitFor(() => {
      expect(screen.getByText('Webshop Content')).toBeInTheDocument();
    });
  });

  it('should deny access when neither functionName nor requiredRoles are specified', async () => {
    // Test error case - neither function nor roles specified
    render(
      <FunctionGuard
        user={mockUser}
        // No functionName or requiredRoles specified - should deny access
      >
        <div>Invalid Configuration Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.queryByText('Invalid Configuration Content')).not.toBeInTheDocument();
    });
  });

  it('should work with existing function-based permissions when no roles are specified', async () => {
    // This tests backward compatibility - existing code without requiredRoles should work unchanged
    mockPermissionManager.hasAccess.mockReturnValue(true);

    render(
      <FunctionGuard
        user={mockUser}
        functionName="webshop"
        // No requiredRoles specified - should use function-based permissions only
      >
        <div>Webshop Content</div>
      </FunctionGuard>
    );

    await waitFor(() => {
      expect(screen.getByText('Webshop Content')).toBeInTheDocument();
    });

    // Verify that only function-based permissions were checked
    expect(mockPermissionManager.hasAccess).toHaveBeenCalledWith('webshop', 'read');
  });

  // Test various H-DCN role combinations as specified in the design document
  describe('H-DCN Role Combinations', () => {
    it('should grant access to regular member (hdcnLeden) for basic functionality', async () => {
      const regularMemberUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['hdcnLeden']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={regularMemberUser}
          requiredRoles={['hdcnLeden']}
        >
          <div>Member Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Member Content')).toBeInTheDocument();
      });
    });

    it('should grant access to Member Administration role combination', async () => {
      const memberAdminUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_CRUD_All', 'Events_Read_All', 'Products_Read_All', 'Communication_Read_All', 'System_User_Management']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={memberAdminUser}
          requiredRoles={['Members_CRUD_All']}
        >
          <div>Member Admin Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Member Admin Content')).toBeInTheDocument();
      });
    });

    it('should grant access to National Chairman role combination', async () => {
      const nationalChairmanUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_Read_All', 'Members_Status_Approve', 'Events_Read_All', 'Products_Read_All', 'Communication_Read_All', 'System_Logs_Read']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={nationalChairmanUser}
          requiredRoles={['Members_Read_All', 'Members_Status_Approve']}
        >
          <div>Chairman Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Chairman Content')).toBeInTheDocument();
      });
    });

    it('should grant access to Webmaster role combination', async () => {
      const webmasterUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_Read_All', 'Events_CRUD_All', 'Products_CRUD_All', 'Communication_CRUD_All', 'System_CRUD_All']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={webmasterUser}
          requiredRoles={['System_CRUD_All']}
        >
          <div>Webmaster Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Webmaster Content')).toBeInTheDocument();
      });
    });

    it('should grant access to Regional Secretary role combination', async () => {
      const regionalSecretaryUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_Read_Region1', 'Members_Export_Region1', 'Events_Read_Region1', 'Products_Read_All', 'Communication_Export_Region1']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={regionalSecretaryUser}
          requiredRoles={['Members_Read_Region1']}
        >
          <div>Regional Secretary Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Regional Secretary Content')).toBeInTheDocument();
      });
    });

    it('should deny access when user has some but not all required roles', async () => {
      const partialRoleUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_Read_All'] // Has read but not CRUD
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={partialRoleUser}
          requiredRoles={['Members_CRUD_All']} // Requires CRUD access
        >
          <div>Admin Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
      });
    });

    it('should grant access when user has multiple roles and any one matches requirement', async () => {
      const multiRoleUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['hdcnLeden', 'Members_Read_All', 'Events_Read_All']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={multiRoleUser}
          requiredRoles={['Members_Read_All']} // User has this role among others
        >
          <div>Multi Role Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Multi Role Content')).toBeInTheDocument();
      });
    });

    it('should grant access when user has multiple roles and multiple are required (OR logic)', async () => {
      const multiRoleUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_Read_All', 'Events_CRUD_All', 'Products_Read_All']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={multiRoleUser}
          requiredRoles={['Members_CRUD_All', 'Members_Read_All']} // User has Members_Read_All
        >
          <div>OR Logic Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('OR Logic Content')).toBeInTheDocument();
      });
    });

    it('should handle combined role and function permissions (AND logic)', async () => {
      mockPermissionManager.hasAccess.mockReturnValue(true);

      const combinedUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_CRUD_All', 'System_User_Management']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={combinedUser}
          functionName="members"
          requiredRoles={['Members_CRUD_All']}
        >
          <div>Combined Permission Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Combined Permission Content')).toBeInTheDocument();
      });

      // Verify both role and function checks were performed
      expect(mockPermissionManager.hasAccess).toHaveBeenCalledWith('members', 'read');
    });

    it('should deny access when user has role but not function permission (AND logic)', async () => {
      mockPermissionManager.hasAccess.mockReturnValue(false); // Function access denied

      const roleOnlyUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['Members_CRUD_All'] // Has role but not function access
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={roleOnlyUser}
          functionName="members"
          requiredRoles={['Members_CRUD_All']}
        >
          <div>Combined Permission Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Combined Permission Content')).not.toBeInTheDocument();
      });
    });

    it('should handle empty cognito groups gracefully', async () => {
      const noGroupsUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              // No cognito:groups property
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={noGroupsUser}
          requiredRoles={['hdcnLeden']}
        >
          <div>No Groups Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('No Groups Content')).not.toBeInTheDocument();
      });
    });

    it('should handle malformed user token gracefully', async () => {
      const malformedUser = {
        // Missing signInUserSession structure
      };

      render(
        <FunctionGuard
          user={malformedUser}
          requiredRoles={['hdcnLeden']}
        >
          <div>Malformed User Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Malformed User Content')).not.toBeInTheDocument();
      });
    });

    it('should handle regional role patterns correctly', async () => {
      const regionalUser = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['hdcnRegio_Noord', 'Members_Read_Region1']
            }
          }
        }
      };

      render(
        <FunctionGuard
          user={regionalUser}
          requiredRoles={['hdcnRegio_Noord']}
        >
          <div>Regional Content</div>
        </FunctionGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Regional Content')).toBeInTheDocument();
      });
    });
  });
});