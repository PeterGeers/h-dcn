// Member-Cognito Integration Example

// 1. Add cognito_id to members table
const addCognitoIdToMembers = `
  ALTER TABLE members 
  ADD COLUMN cognito_id VARCHAR(255) UNIQUE;
  
  CREATE INDEX idx_members_cognito_id 
  ON members(cognito_id);
`;

// 2. Update existing members with cognito_id
const linkExistingMembers = async () => {
  const members = await fetch('/api/members').then(r => r.json());
  const cognitoUsers = await fetch('/api/cognito/users').then(r => r.json());
  
  for (const member of members) {
    const cognitoUser = cognitoUsers.find(u => 
      u.Attributes?.find(attr => 
        attr.Name === 'email' && attr.Value === member.email
      )
    );
    
    if (cognitoUser) {
      await fetch(`/api/members/${member.member_id}`, {
        method: 'PUT',
        body: JSON.stringify({
          ...member,
          cognito_id: cognitoUser.Username
        })
      });
    }
  }
};

// 3. Enhanced member lookup
const getMemberByCognitoId = async (cognitoId) => {
  const response = await fetch(`/api/members?cognito_id=${cognitoId}`);
  return response.json();
};

// 4. Create member when Cognito user is created
const createMemberFromCognito = async (cognitoUser) => {
  const email = cognitoUser.Attributes?.find(attr => attr.Name === 'email')?.Value;
  const givenName = cognitoUser.Attributes?.find(attr => attr.Name === 'given_name')?.Value;
  const familyName = cognitoUser.Attributes?.find(attr => attr.Name === 'family_name')?.Value;
  
  return await fetch('/api/members', {
    method: 'POST',
    body: JSON.stringify({
      cognito_id: cognitoUser.Username,
      email: email,
      voornaam: givenName,
      achternaam: familyName,
      status: 'active',
      lidmaatschap: 'basis'
    })
  });
};