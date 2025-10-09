// Backend debugging tool
const API_BASE = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function debugBackend() {
  console.log('🔍 Backend Debugging Tool\n');

  // Test different payload formats
  const payloads = [
    {
      name: 'Dutch fields (expected)',
      data: {
        naam: "Test Event",
        datum_van: "2024-12-25",
        locatie: "Test Location"
      }
    },
    {
      name: 'English fields (maybe expected?)',
      data: {
        title: "Test Event",
        start_date: "2024-12-25", 
        location: "Test Location"
      }
    },
    {
      name: 'Mixed fields',
      data: {
        naam: "Test Event",
        title: "Test Event",
        datum_van: "2024-12-25",
        start_date: "2024-12-25",
        locatie: "Test Location",
        location: "Test Location"
      }
    }
  ];

  for (const payload of payloads) {
    console.log(`\n📦 Testing: ${payload.name}`);
    console.log('Payload:', JSON.stringify(payload.data, null, 2));
    
    try {
      const response = await fetch(`${API_BASE}/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload.data)
      });
      
      console.log(`Status: ${response.status}`);
      const responseText = await response.text();
      console.log('Response:', responseText);
      
      if (response.ok) {
        console.log('✅ SUCCESS!');
        const data = JSON.parse(responseText);
        if (data.event_id) {
          // Clean up - delete the test event
          await fetch(`${API_BASE}/events/${data.event_id}`, { method: 'DELETE' });
          console.log('🗑️ Test event cleaned up');
        }
        break; // Stop testing once we find a working format
      } else {
        console.log('❌ Failed');
      }
    } catch (error) {
      console.log(`❌ Error: ${error.message}`);
    }
    console.log('---');
  }

  // Test if there's a specific endpoint structure issue
  console.log('\n🔗 Testing endpoint variations:');
  const endpoints = [
    '/events',
    '/event', 
    '/Events'
  ];

  for (const endpoint of endpoints) {
    try {
      const response = await fetch(`${API_BASE}${endpoint}`);
      console.log(`${endpoint}: ${response.status} ${response.statusText}`);
    } catch (error) {
      console.log(`${endpoint}: Error - ${error.message}`);
    }
  }
}

debugBackend();