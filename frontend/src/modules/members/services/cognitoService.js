import { CognitoIdentityProviderClient, 
  ListUsersCommand, AdminCreateUserCommand, AdminDeleteUserCommand,
  AdminUpdateUserAttributesCommand, AdminSetUserPasswordCommand,
  AdminAddUserToGroupCommand, AdminRemoveUserFromGroupCommand,
  ListGroupsCommand, CreateGroupCommand, DeleteGroupCommand,
  AdminListGroupsForUserCommand, ListUsersInGroupCommand,
  AdminDisableUserCommand, AdminEnableUserCommand,
  DescribeUserPoolCommand
} from '@aws-sdk/client-cognito-identity-provider';

class CognitoService {
  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL;
  }

  async makeRequest(endpoint, options = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
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
  async listUsers(limit = 60) {
    const response = await this.makeRequest('/cognito/users');
    return { Users: response };
  }

  async createUser(username, email, tempPassword, attributes = {}, groups = '') {
    return await this.makeRequest('/cognito/users', {
      method: 'POST',
      body: JSON.stringify({
        username,
        email,
        tempPassword,
        attributes,
        groups
      })
    });
  }

  async deleteUser(username) {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'DELETE'
    });
  }

  async updateUserAttributes(username, attributes) {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'PUT',
      body: JSON.stringify({ attributes })
    });
  }

  async setUserPassword(username, password, permanent = true) {
    return await this.makeRequest(`/cognito/users/${username}/password`, {
      method: 'PUT',
      body: JSON.stringify({ password, permanent })
    });
  }

  async disableUser(username) {
    return await this.makeRequest(`/cognito/users/${username}/disable`, {
      method: 'PUT'
    });
  }

  async enableUser(username) {
    return await this.makeRequest(`/cognito/users/${username}/enable`, {
      method: 'PUT'
    });
  }

  // Group Management
  async listGroups() {
    const response = await this.makeRequest('/cognito/groups');
    return { Groups: response };
  }

  async createGroup(groupName, description) {
    return await this.makeRequest('/cognito/groups', {
      method: 'POST',
      body: JSON.stringify({ groupName, description })
    });
  }

  async deleteGroup(groupName) {
    return await this.makeRequest(`/cognito/groups/${groupName}`, {
      method: 'DELETE'
    });
  }

  async addUserToGroup(username, groupName) {
    return await this.makeRequest(`/cognito/users/${username}/groups/${groupName}`, {
      method: 'POST'
    });
  }

  async removeUserFromGroup(username, groupName) {
    return await this.makeRequest(`/cognito/users/${username}/groups/${groupName}`, {
      method: 'DELETE'
    });
  }

  async getUserGroups(username) {
    const response = await this.makeRequest(`/cognito/users/${username}/groups`);
    return { Groups: response };
  }

  async getUsersInGroup(groupName) {
    const response = await this.makeRequest(`/cognito/groups/${groupName}/users`);
    return { Users: response };
  }

  // Bulk Operations
  async assignGroupsToUsers(users) {
    return await this.makeRequest('/cognito/users/assign-groups', {
      method: 'POST',
      body: JSON.stringify({ users })
    });
  }

  async importUsers(users) {
    return await this.makeRequest('/cognito/users/import', {
      method: 'POST',
      body: JSON.stringify({ users })
    });
  }

  async importGroups(groups) {
    return await this.makeRequest('/cognito/groups/import', {
      method: 'POST',
      body: JSON.stringify({ groups })
    });
  }

  // Pool Settings
  async getPoolSettings() {
    const response = await this.makeRequest('/cognito/pool');
    return { UserPool: response };
  }
}

export default new CognitoService();