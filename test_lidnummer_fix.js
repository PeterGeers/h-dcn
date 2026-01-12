// Test script to verify the lidnummer fix
// This simulates how the frontend processes member data

// Mock member data similar to what comes from the database
const mockMember = {
  member_id: "be203ea1-c545-469d-b8f3-da5759c0fe45",
  voornaam: "Rene",
  achternaam: "Paulssen",
  lidmaatschap: "Gewoon lid",
  status: "Actief",
  lidnummer: "6084", // This should be preserved, not overwritten with 0
  email: "renepaulssen@home.nl",
  regio: "Brabant/Zeeland"
};

// Simulate the nextLidnummer function fix
function nextLidnummer(existingLidnummer) {
  // If member already has a lidnummer, preserve it
  if (existingLidnummer !== undefined && existingLidnummer !== null && existingLidnummer !== '') {
    return existingLidnummer;
  }
  
  // For new members without lidnummer, return 0 as placeholder
  return 0;
}

// Test the function
console.log("=== Testing LidNummer Fix ===");
console.log("Original member lidnummer:", mockMember.lidnummer);
console.log("After nextLidnummer function:", nextLidnummer(mockMember.lidnummer));

// Test with empty/null values (new member scenario)
console.log("\n=== Testing New Member Scenario ===");
console.log("nextLidnummer(null):", nextLidnummer(null));
console.log("nextLidnummer(undefined):", nextLidnummer(undefined));
console.log("nextLidnummer(''):", nextLidnummer(''));

// Test with various existing values
console.log("\n=== Testing Various Existing Values ===");
console.log("nextLidnummer('6084'):", nextLidnummer('6084'));
console.log("nextLidnummer(6084):", nextLidnummer(6084));
console.log("nextLidnummer('0'):", nextLidnummer('0'));
console.log("nextLidnummer(0):", nextLidnummer(0));