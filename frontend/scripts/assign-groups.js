// Script to assign groups to existing users
const fs = require('fs');

// Read the user data
const csv = fs.readFileSync('./cognito-users.csv', 'utf8');
const lines = csv.split('\n').slice(1).filter(line => line.trim());

const baseUrl = 'http://localhost:3001'; // Adjust if different

async function assignGroupsToUsers() {
  console.log(`🚀 Starting group assignment for ${lines.length} users...`);
  
  for (let i = 0; i < lines.length; i++) {
    const columns = lines[i].split(',');
    const username = columns[0]?.trim();
    const groups = columns[5]?.trim();
    
    if (username && groups) {
      const groupList = groups.split(';');
      
      console.log(`\n👤 Processing ${username}:`);
      
      for (const groupName of groupList) {
        const cleanGroupName = groupName.trim();
        if (cleanGroupName) {
          try {
            const response = await fetch(`${baseUrl}/cognito/users/${encodeURIComponent(username)}/groups/${cleanGroupName}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
              console.log(`  ✅ Added to ${cleanGroupName}`);
            } else {
              const error = await response.text();
              console.log(`  ❌ Failed to add to ${cleanGroupName}: ${error}`);
            }
          } catch (error) {
            console.log(`  ❌ Network error for ${cleanGroupName}: ${error.message}`);
          }
          
          // Small delay to avoid rate limiting
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
    }
  }
  
  console.log('\n🎉 Group assignment completed!');
}

assignGroupsToUsers();