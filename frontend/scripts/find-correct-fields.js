// Find the correct field names the backend expects
const API_BASE = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function findCorrectFields() {
  console.log('🔍 Finding correct field names...\n');

  // Based on error messages, try different combinations
  const testCases = [
    {
      name: 'Case 1: title + event_date',
      data: {
        title: "Test Event",
        event_date: "2024-12-25",
        location: "Test Location"
      }
    },
    {
      name: 'Case 2: title + date',
      data: {
        title: "Test Event", 
        date: "2024-12-25",
        location: "Test Location"
      }
    },
    {
      name: 'Case 3: name + event_date',
      data: {
        name: "Test Event",
        event_date: "2024-12-25", 
        location: "Test Location"
      }
    },
    {
      name: 'Case 4: Minimal required fields',
      data: {
        title: "Test Event",
        event_date: "2024-12-25"
      }
    },
    {
      name: 'Case 5: All possible fields',
      data: {
        title: "Test Event",
        event_date: "2024-12-25",
        location: "Test Location",
        participants: 10,
        cost: 100.50,
        revenue: 250.00,
        notes: "Test notes"
      }
    }
  ];

  for (const testCase of testCases) {
    console.log(`\n📦 ${testCase.name}`);
    console.log('Payload:', JSON.stringify(testCase.data, null, 2));
    
    try {
      const response = await fetch(`${API_BASE}/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(testCase.data)
      });
      
      console.log(`Status: ${response.status}`);
      const responseText = await response.text();
      
      if (response.ok) {
        console.log('✅ SUCCESS! This format works!');
        console.log('Response:', responseText);
        
        const data = JSON.parse(responseText);
        if (data.event_id) {
          // Clean up
          await fetch(`${API_BASE}/events/${data.event_id}`, { method: 'DELETE' });
          console.log('🗑️ Test event cleaned up');
        }
        return testCase.data; // Return the working format
      } else {
        console.log('❌ Failed');
        console.log('Error:', responseText);
      }
    } catch (error) {
      console.log(`❌ Network error: ${error.message}`);
    }
    console.log('---');
  }
  
  console.log('\n❌ No working format found. Backend may have issues.');
  return null;
}

findCorrectFields().then(workingFormat => {
  if (workingFormat) {
    console.log('\n🎉 Working field format found:');
    console.log(JSON.stringify(workingFormat, null, 2));
  }
});