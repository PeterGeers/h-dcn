// Assign groups using individual API calls
const fs = require('fs');

const baseUrl = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function assignGroupsIndividually() {
  try {
    // Read the CSV with group assignments
    const csv = fs.readFileSync('./cognito-users.csv', 'utf8');
    const lines = csv.split('\n').slice(1).filter(line => line.trim());
    
    let totalAssignments = 0;
    let successCount = 0;
    let errorCount = 0;
    
    console.log(`🚀 Starting group assignments for ${lines.length} users...`);
    
    for (let i = 0; i < lines.length; i++) {
      const columns = lines[i].split(',');
      const username = columns[0]?.trim();
      const groups = columns[5]?.trim();
      
      if (username && groups) {
        const groupList = groups.split(';');
        console.log(`\n👤 Processing ${username} (${i + 1}/${lines.length}):`);
        
        for (const groupName of groupList) {
          const cleanGroupName = groupName.trim();
          if (cleanGroupName) {
            totalAssignments++;
            try {
              const response = await fetch(`${baseUrl}/cognito/users/${encodeURIComponent(username)}/groups/${cleanGroupName}`, {
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
    console.log(`📊 Results: ${successCount}/${totalAssignments} successful, ${errorCount} errors`);
    
  } catch (error) {
    console.log('❌ Error:', error.message);
  }
}

assignGroupsIndividually();