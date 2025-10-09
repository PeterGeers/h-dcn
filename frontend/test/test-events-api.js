// Test script for Events API
const API_BASE = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function testAPI() {
  console.log('🧪 Testing Events API...\n');

  // Test 1: GET /events
  console.log('1️⃣ Testing GET /events');
  try {
    const response = await fetch(`${API_BASE}/events`);
    console.log(`Status: ${response.status}`);
    console.log(`Headers:`, Object.fromEntries(response.headers.entries()));
    
    if (response.ok) {
      const data = await response.json();
      console.log(`✅ Success: Found ${data.length} events`);
      console.log('Sample event:', data[0] || 'No events found');
    } else {
      console.log(`❌ Failed: ${response.statusText}`);
      const errorText = await response.text();
      console.log('Error response:', errorText);
    }
  } catch (error) {
    console.log(`❌ Network error: ${error.message}`);
  }
  console.log('\n---\n');

  // Test 2: POST /events
  console.log('2️⃣ Testing POST /events');
  const testEvent = {
    naam: "Test Evenement",
    datum_van: "2024-12-25",
    locatie: "Test Locatie",
    aantal_deelnemers: 10,
    kosten: 100.50,
    inkomsten: 250.00,
    opmerkingen: "Test evenement via API"
  };
  
  console.log('Sending data:', JSON.stringify(testEvent, null, 2));

  try {
    const response = await fetch(`${API_BASE}/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(testEvent)
    });
    
    console.log(`Status: ${response.status}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Success: Event created');
      console.log('Created event:', data);
      
      // Test 3: DELETE the test event
      if (data.event_id) {
        console.log('\n3️⃣ Testing DELETE /events/{id}');
        const deleteResponse = await fetch(`${API_BASE}/events/${data.event_id}`, {
          method: 'DELETE'
        });
        
        console.log(`Delete Status: ${deleteResponse.status}`);
        if (deleteResponse.ok || deleteResponse.status === 204) {
          console.log('✅ Success: Test event deleted');
        } else {
          console.log('❌ Failed to delete test event');
        }
      }
    } else {
      console.log(`❌ Failed: ${response.statusText}`);
      const errorText = await response.text();
      console.log('Error response:', errorText);
    }
  } catch (error) {
    console.log(`❌ Network error: ${error.message}`);
  }
  console.log('\n---\n');

  // Test 4: Check CORS headers
  console.log('4️⃣ Testing CORS');
  try {
    const response = await fetch(`${API_BASE}/events`, {
      method: 'OPTIONS'
    });
    console.log(`OPTIONS Status: ${response.status}`);
    console.log('CORS Headers:');
    console.log('  Access-Control-Allow-Origin:', response.headers.get('Access-Control-Allow-Origin'));
    console.log('  Access-Control-Allow-Methods:', response.headers.get('Access-Control-Allow-Methods'));
    console.log('  Access-Control-Allow-Headers:', response.headers.get('Access-Control-Allow-Headers'));
  } catch (error) {
    console.log(`❌ CORS test error: ${error.message}`);
  }

  console.log('\n🏁 API Test Complete');
}

// Run the test
testAPI();