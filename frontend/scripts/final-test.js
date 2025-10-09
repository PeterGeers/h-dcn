// Final end-to-end test
const API_BASE = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function finalTest() {
  console.log('🎯 Final End-to-End Test\n');

  // Test the exact format your frontend will send
  console.log('1️⃣ Testing frontend format (CREATE)...');
  const frontendData = {
    title: "Voorjaarsrit 2024",
    event_date: "2024-04-15", 
    end_date: "2024-04-15",
    location: "Café De Biker",
    participants: "25",
    cost: "150.50",
    revenue: "375.00",
    notes: "Mooi weer gehad"
  };

  console.log('Sending:', JSON.stringify(frontendData, null, 2));

  let eventId = null;
  try {
    const response = await fetch(`${API_BASE}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(frontendData)
    });

    console.log(`Status: ${response.status}`);
    if (response.ok) {
      const result = await response.json();
      console.log('✅ CREATE Success:', result);
      eventId = result.event_id;
    } else {
      console.log('❌ CREATE Failed:', await response.text());
      return;
    }
  } catch (error) {
    console.log('❌ CREATE Error:', error.message);
    return;
  }

  // Test GET to see what comes back
  console.log('\n2️⃣ Testing GET (what frontend will receive)...');
  try {
    const response = await fetch(`${API_BASE}/events`);
    if (response.ok) {
      const events = await response.json();
      console.log('✅ GET Success - Events received:');
      events.forEach((event, index) => {
        console.log(`Event ${index + 1}:`, JSON.stringify(event, null, 2));
      });
    } else {
      console.log('❌ GET Failed:', await response.text());
    }
  } catch (error) {
    console.log('❌ GET Error:', error.message);
  }

  // Test UPDATE
  if (eventId) {
    console.log('\n3️⃣ Testing UPDATE...');
    const updateData = {
      title: "Updated Voorjaarsrit 2024",
      event_date: "2024-04-16",
      location: "Updated Café De Biker", 
      participants: "30",
      cost: "200.00",
      revenue: "450.00",
      notes: "Updated notes"
    };

    try {
      const response = await fetch(`${API_BASE}/events/${eventId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      console.log(`Status: ${response.status}`);
      if (response.ok) {
        const result = await response.json();
        console.log('✅ UPDATE Success:', result);
      } else {
        console.log('❌ UPDATE Failed:', await response.text());
      }
    } catch (error) {
      console.log('❌ UPDATE Error:', error.message);
    }

    // Test DELETE
    console.log('\n4️⃣ Testing DELETE...');
    try {
      const response = await fetch(`${API_BASE}/events/${eventId}`, {
        method: 'DELETE'
      });

      console.log(`Status: ${response.status}`);
      if (response.ok || response.status === 204) {
        console.log('✅ DELETE Success');
      } else {
        console.log('❌ DELETE Failed:', await response.text());
      }
    } catch (error) {
      console.log('❌ DELETE Error:', error.message);
    }
  }

  console.log('\n🎉 All tests completed!');
  console.log('\n📋 Summary:');
  console.log('- Backend expects English field names (title, event_date, location, etc.)');
  console.log('- Backend returns English field names');
  console.log('- Frontend has been updated to use correct field names');
  console.log('- CRUD operations should now work properly');
}

finalTest();