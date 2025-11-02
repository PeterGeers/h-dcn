// Cognito management via your existing API instead of direct AWS calls

interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
}

interface UserData {
  username?: string;
  email?: string;
  given_name?: string;
  family_name?: string;
  phone_number?: string;
  password?: string;
  [key: string]: any;
}

interface GroupData {
  groupName: string;
  description?: string;
  [key: string]: any;
}

class CognitoApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || '';
  }

  async makeRequest(endpoint: string, options: RequestOptions = {}): Promise<any> {
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
  async listUsers(): Promise<any> {
    return await this.makeRequest('/cognito/users');
  }

  async createUser(userData: UserData): Promise<any> {
    return await this.makeRequest('/cognito/users', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }

  async updateUser(username: string, userData: UserData): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'PUT',
      body: JSON.stringify(userData)
    });
  }

  async deleteUser(username: string): Promise<any> {
    return await this.makeRequest(`/cognito/users/${username}`, {
      method: 'DELETE'
    });
  }

  // Group Management via API
  async listGroups(): Promise<any> {
    return await this.makeRequest('/cognito/groups');
  }

  async createGroup(groupData: GroupData): Promise<any> {
    return await this.makeRequest('/cognito/groups', {
      method: 'POST',
      body: JSON.stringify(groupData)
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
}

export default new CognitoApiService();