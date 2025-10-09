// Bulk assign groups using the new API endpoint
const fs = require('fs');

const baseUrl = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'; // Your actual API URL

async function bulkAssignGroups() {
  try {
    // Read the CSV with group assignments
    const csv = fs.readFileSync('./cognito-users.csv', 'utf8');
    const lines = csv.split('\n').slice(1).filter(line => line.trim());
    
    const users = [];
    
    for (const line of lines) {
      const columns = line.split(',');
      const username = columns[0]?.trim();
      const groups = columns[5]?.trim();
      
      if (username && groups) {
        users.push({
          username: username,
          groups: groups
        });
      }
    }
    
    console.log(`🚀 Assigning groups to ${users.length} users...`);
    
    // Use the bulk assign endpoint
    const response = await fetch(`${baseUrl}/cognito/users/assign-groups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ users })
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('✅ Bulk group assignment completed!');
      console.log(result);
    } else {
      const error = await response.text();
      console.log('❌ Bulk assignment failed:', response.status, error);
    }
    
  } catch (error) {
    console.log('❌ Error:', error.message);
  }
}

bulkAssignGroups();