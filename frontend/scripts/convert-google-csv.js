// Convert Google Workspace CSV to Cognito format
const fs = require('fs');

function convertGoogleCsvToCognito(inputFile, outputFile) {
  const csv = fs.readFileSync(inputFile, 'utf8');
  const lines = csv.split('\n');
  
  // Skip header line
  const dataLines = lines.slice(1).filter(line => line.trim());
  
  const cognitoUsers = [];
  
  dataLines.forEach((line, index) => {
    const columns = line.split(',');
    
    if (columns.length >= 3) {
      const firstName = columns[0]?.trim() || '';
      const lastName = columns[1]?.trim() || '';
      const email = columns[2]?.trim() || '';
      
      if (email && email.includes('@')) {
        // Use email as username
        const username = email;
        
        // Determine groups based on email domain and content
        let groups = ['hdcnLeden']; // Default group
        
        // Add region groups based on email content
        if (email.includes('noordholland') || email.includes('noord-holland')) {
          groups.push('hdcnRegio_NoordHolland');
        } else if (email.includes('zuid-holland')) {
          groups.push('hdcnRegio_ZuidHolland');
        } else if (email.includes('utrecht')) {
          groups.push('hdcnRegio_Utrecht');
        } else if (email.includes('limburg')) {
          groups.push('hdcnRegio_Limburg');
        } else if (email.includes('oost')) {
          groups.push('hdcnRegio_Oost');
        } else if (email.includes('friesland')) {
          groups.push('hdcnRegio_Friesland');
        } else if (email.includes('groningen') || email.includes('drenthe')) {
          groups.push('hdcnRegio_Groningen');
        } else if (email.includes('brabant') || email.includes('zeeland')) {
          groups.push('hdcnRegio_NoordBrabantZeeland');
        } else if (email.includes('duitsland')) {
          groups.push('hdcnRegio_Duitsland');
        }
        
        // Add admin groups for specific roles
        if (email.includes('president') || email.includes('secretaris@') || email.includes('penningmeester@')) {
          groups.push('hdcnBestuur');
          groups.push('hdcnAdmins');
        } else if (email.includes('webmaster') || email.includes('ledenadministratie')) {
          groups.push('hdcnAdmins');
        }
        
        cognitoUsers.push({
          username: username,
          email: email,
          given_name: firstName,
          family_name: lastName,
          groups: groups.join(';'),
          tempPassword: 'WelkomHDCN2024!'
        });
      }
    }
  });
  
  // Create CSV header
  const header = 'username,email,given_name,family_name,phone_number,groups,tempPassword';
  
  // Create CSV rows
  const csvRows = cognitoUsers.map(user => 
    `${user.username},${user.email},${user.given_name},${user.family_name},,${user.groups},${user.tempPassword}`
  );
  
  // Write to file
  const outputCsv = [header, ...csvRows].join('\n');
  fs.writeFileSync(outputFile, outputCsv);
  
  console.log(`✅ Converted ${cognitoUsers.length} users`);
  console.log(`📁 Output saved to: ${outputFile}`);
  
  // Show sample
  console.log('\n📋 Sample entries:');
  cognitoUsers.slice(0, 3).forEach(user => {
    console.log(`${user.username} | ${user.email} | Groups: ${user.groups}`);
  });
}

// Convert the file
const inputFile = './google-users.csv';
const outputFile = './cognito-users.csv';

convertGoogleCsvToCognito(inputFile, outputFile);