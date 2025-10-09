// Assign groups to existing users by matching email addresses
const fs = require('fs');

const baseUrl = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function assignGroupsToExistingUsers() {
  try {
    // First, get all existing users from Cognito
    console.log('🔍 Fetching existing users from Cognito...');
    const usersResponse = await fetch(`${baseUrl}/cognito/users`);
    if (!usersResponse.ok) {
      throw new Error(`Failed to fetch users: ${usersResponse.status}`);
    }
    const existingUsers = await usersResponse.json();
    
    // Create a map of email -> username
    const emailToUsername = {};
    existingUsers.forEach(user => {
      const email = user.Attributes?.find(attr => attr.Name === 'email')?.Value;
      if (email) {
        emailToUsername[email] = user.Username;
      }
    });
    
    console.log(`📋 Found ${Object.keys(emailToUsername).length} users with email addresses`);
    
    // Read the CSV with group assignments
    const csv = fs.readFileSync('./cognito-users.csv', 'utf8');
    const lines = csv.split('\n').slice(1).filter(line => line.trim());
    
    let totalAssignments = 0;
    let successCount = 0;
    let errorCount = 0;
    let userNotFoundCount = 0;
    
    console.log(`🚀 Starting group assignments for ${lines.length} CSV entries...`);
    
    for (let i = 0; i < lines.length; i++) {
      const columns = lines[i].split(',');
      const csvEmail = columns[1]?.trim(); // Email is in column 1
      const groups = columns[5]?.trim();   // Groups are in column 5
      
      if (csvEmail && groups) {
        // Find the actual username for this email
        const actualUsername = emailToUsername[csvEmail];
        
        if (!actualUsername) {
          console.log(`⚠️  User not found for email: ${csvEmail}`);
          userNotFoundCount++;
          continue;
        }
        
        const groupList = groups.split(';');
        console.log(`\n👤 Processing ${csvEmail} -> ${actualUsername} (${i + 1}/${lines.length}):`);
        
        for (const groupName of groupList) {
          const cleanGroupName = groupName.trim();
          if (cleanGroupName) {
            totalAssignments++;
            try {
              const response = await fetch(`${baseUrl}/cognito/users/${encodeURIComponent(actualUsername)}/groups/${cleanGroupName}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
              });
              
              if (response.ok) {
                console.log(`  ✅ Added to ${cleanGroupName}`);
                successCount++;
              } else {
                const error = await response.text();
                console.log(`  ❌ Failed to add to ${cleanGroupName}: ${error}`);
                errorCount++;
              }
            } catch (error) {
              console.log(`  ❌ Network error for ${cleanGroupName}: ${error.message}`);
              errorCount++;
            }
            
            // Small delay to avoid rate limiting
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        }
      }
    }
    
    console.log(`\n🎉 Group assignment completed!`);
    console.log(`📊 Results:`);
    console.log(`   ✅ ${successCount}/${totalAssignments} assignments successful`);
    console.log(`   ❌ ${errorCount} assignment errors`);
    console.log(`   ⚠️  ${userNotFoundCount} users not found`);
    
  } catch (error) {
    console.log('❌ Error:', error.message);
  }
}

assignGroupsToExistingUsers();