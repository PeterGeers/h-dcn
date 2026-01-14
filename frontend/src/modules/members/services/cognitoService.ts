import { CognitoIdentityProviderClient, 
  ListUsersCommand, AdminCreateUserCommand, AdminDeleteUserCommand,
  AdminUpdateUserAttributesCommand,
  AdminAddUserToGroupCommand, AdminRemoveUserFromGroupCommand,
  ListGroupsCommand, CreateGroupCommand, DeleteGroupCommand,
  AdminListGroupsForUserCommand, ListUsersInGroupCommand,
  AdminDisableUserCommand, AdminEnableUserCommand,
  DescribeUserPoolCommand
} from '@aws-sdk/client-cognito-identity-provider';
import { getAuthHeaders } from '../../../utils/authHeaders';

interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
}

interface UserAttributes {
  given_name?: string;
  family_name?: string;
  phone_number?: string;
  [key: string]: any;
}

interface BulkUser {
  username: string;
  email: string;
  groups?: string[];
  attributes?: UserAttributes;
}

interface BulkGroup {
  groupName: string;
  description?: string;
}

class CognitoService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || '';
  }

  async makeRequest(endpoint: string, options: RequestOptions = {}): Promise<any> {
    // Get auth headers
    const authHeaders = await getAuthHeaders();
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  // User Management
  async listUsers(limit: number = 60): Promise<any> {
    const response = await this.makeRequest('/cognito/users');
    return { Users: response };
  }

  async createUser(username: string, email: string, attributes: UserAttributes = {}, groups: string = ''): Promise<any> {
    return await this.makeRequest('/cognito/users', {
      method: 'POST',
      body: JSON.stringify({
        username,
        email,
        attributes,
        groups
      })
    });
  }

  async deleteUser(username: string): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'DELETE'
    });
  }

  async updateUserAttributes(username: string, attributes: UserAttributes): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'PUT',
      body: JSON.stringify({ attributes })
    });
  }

  async disableUser(username: string): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}/disable`, {
      method: 'PUT'
    });
  }

  async enableUser(username: string): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}/enable`, {
      method: 'PUT'
    });
  }

  // Group Management
  async listGroups(): Promise<any> {
    const response = await this.makeRequest('/cognito/groups');
    return { Groups: response };
  }

  async createGroup(groupName: string, description?: string): Promise<any> {
    return await this.makeRequest('/cognito/groups', {
      method: 'POST',
      body: JSON.stringify({ groupName, description })
    });
  }

  async deleteGroup(groupName: string): Promise<any> {
    return await this.makeRequest(`/cognito/groups/${groupName}`, {
      method: 'DELETE'
    });
  }

  async addUserToGroup(username: string, groupName: string): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}/groups/${groupName}`, {
      method: 'POST'
    });
  }

  async removeUserFromGroup(username: string, groupName: string): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}/groups/${groupName}`, {
      method: 'DELETE'
    });
  }

  async getUserGroups(username: string): Promise<any> {
    const response = await this.makeRequest(`/cognito/users/${username}/groups`);
    return { Groups: response };
  }

  async getUsersInGroup(groupName: string): Promise<any> {
    const encodedGroupName = encodeURIComponent(groupName);
    const response = await this.makeRequest(`/cognito/groups/${encodedGroupName}/users`);
    return { Users: response };
  }

  // Bulk Operations
  async assignGroupsToUsers(users: BulkUser[]): Promise<any> {
    return await this.makeRequest('/cognito/users/assign-groups', {
      method: 'POST',
      body: JSON.stringify({ users })
    });
  }

  async importUsers(users: BulkUser[]): Promise<any> {
    return await this.makeRequest('/cognito/users/import', {
      method: 'POST',
      body: JSON.stringify({ users })
    });
  }

  async importGroups(groups: BulkGroup[]): Promise<any> {
    return await this.makeRequest('/cognito/groups/import', {
      method: 'POST',
      body: JSON.stringify({ groups })
    });
  }

  // Pool Settings
  async getPoolSettings(): Promise<any> {
    const response = await this.makeRequest('/cognito/pool');
    return { UserPool: response };
  }
}

export default new CognitoService();