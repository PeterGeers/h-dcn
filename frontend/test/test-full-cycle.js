// Test full CRUD cycle to see what field names are returned
const API_BASE = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function testFullCycle() {
  console.log('🔄 Testing full CRUD cycle...\n');

  // 1. Create an event
  console.log('1️⃣ Creating event...');
  const eventData = {
    title: "Test Evenement",
    event_date: "2024-12-25",
    location: "Test Locatie",
    participants: 15,
    cost: 150.75,
    revenue: 375.00,
    notes: "Test evenement voor API verificatie"
  };

  let eventId = null;
  try {
    const createResponse = await fetch(`${API_BASE}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(eventData)
    });

    if (createResponse.ok) {
      const createResult = await createResponse.json();
      console.log('✅ Event created:', createResult);
      eventId = createResult.event_id;
    } else {
      console.log('❌ Create failed:', await createResponse.text());
      return;
    }
  } catch (error) {
    console.log('❌ Create error:', error.message);
    return;
  }

  // 2. Get all events to see the structure
  console.log('\n2️⃣ Getting all events...');
  try {
    const getResponse = await fetch(`${API_BASE}/events`);
    if (getResponse.ok) {
      const events = await getResponse.json();
      console.log('✅ Events retrieved:', events.length);
      if (events.length > 0) {
        console.log('Sample event structure:');
        console.log(JSON.stringify(events[0], null, 2));
      }
    } else {
      console.log('❌ Get failed:', await getResponse.text());
    }
  } catch (error) {
    console.log('❌ Get error:', error.message);
  }

  // 3. Update the event
  if (eventId) {
    console.log('\n3️⃣ Updating event...');
    const updateData = {
      title: "Updated Test Evenement",
      event_date: "2024-12-26",
      location: "Updated Locatie",
      participants: 20,
      cost: 200.00,
      revenue: 500.00,
      notes: "Updated test evenement"
    };

    try {
      const updateResponse = await fetch(`${API_BASE}/events/${eventId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      if (updateResponse.ok) {
        const updateResult = await updateResponse.json();
        console.log('✅ Event updated:', updateResult);
      } else {
        console.log('❌ Update failed:', await updateResponse.text());
      }
    } catch (error) {
      console.log('❌ Update error:', error.message);
    }

    // 4. Delete the event
    console.log('\n4️⃣ Deleting event...');
    try {
      const deleteResponse = await fetch(`${API_BASE}/events/${eventId}`, {
        method: 'DELETE'
      });

      if (deleteResponse.ok || deleteResponse.status === 204) {
        console.log('✅ Event deleted successfully');
      } else {
        console.log('❌ Delete failed:', await deleteResponse.text());
      }
    } catch (error) {
      console.log('❌ Delete error:', error.message);
    }
  }

  console.log('\n🏁 Full cycle test complete');
}

testFullCycle();