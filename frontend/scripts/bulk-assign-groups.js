// Bulk assign groups to existing users using new API
const fs = require('fs');

const baseUrl = 'http://localhost:3001'; // Adjust if different

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
    
    // Use the new bulk assign endpoint
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
      console.log('❌ Bulk assignment failed:', error);
    }
    
  } catch (error) {
    console.log('❌ Error:', error.message);
  }
}

bulkAssignGroups();