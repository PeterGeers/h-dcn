// Cognito management via your existing API instead of direct AWS calls
class CognitoApiService {
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
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // User Management via API
  async listUsers() {
    return await this.makeRequest('/cognito/users');
  }

  async createUser(userData) {
    return await this.makeRequest('/cognito/users', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }

  async updateUser(username, userData) {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'PUT',
      body: JSON.stringify(userData)
    });
  }

  async deleteUser(username) {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'DELETE'
    });
  }

  // Group Management via API
  async listGroups() {
    return await this.makeRequest('/cognito/groups');
  }

  async createGroup(groupData) {
    return await this.makeRequest('/cognito/groups', {
      method: 'POST',
      body: JSON.stringify(groupData)
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
}

export default new CognitoApiService();