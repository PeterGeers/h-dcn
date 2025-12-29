// Test script to debug role detection for webmaster@h-dcn.nl

// Your actual roles from Cognito
const webmasterRoles = [
  'Events_CRUD_All',
  'hdcnLeden', 
  'System_User_Management',
  'System_Logs_Read',
  'Members_Read_All',
  'Members_CRUD_All',
  'Communication_CRUD_All',
  'Webshop_Management'
];

// Simulate the getAccessLevelSummary function
function getAccessLevelSummary(roles) {
  console.log('Input roles:', roles);
  
  if (!roles || roles.length === 0) {
    return {
      level: 'basic',
      description: 'Geen toegang',
      icon: '❌'
    };
  }
  
  // Check for system admin roles
  const systemRoles = roles.filter(role => 
    role.includes('System_') || 
    role.includes('Webmaster') || 
    role === 'hdcnAdmins'
  );
  
  console.log('System roles found:', systemRoles);
  
  if (systemRoles.length > 0) {
    return {
      level: 'system',
      description: 'Systeembeheerder - Volledige toegang',
      icon: '⚡'
    };
  }
  
  // Check for administrative roles
  const adminRoles = roles.filter(role => 
    role.includes('Members_CRUD_All') ||
    role.includes('National_') ||
    role.includes('Communication_CRUD_All') ||
    role.includes('Events_CRUD_All') ||
    role.includes('Products_CRUD_All')
  );
  
  console.log('Admin roles found:', adminRoles);
  
  if (adminRoles.length > 0) {
    return {
      level: 'administrative',
      description: 'Beheerder - Uitgebreide beheertoegang',
      icon: '🔧'
    };
  }
  
  // Check for functional roles
  const functionalRoles = roles.filter(role => 
    role.includes('Members_') || 
    role.includes('Events_') || 
    role.includes('Products_') ||
    role.includes('Communication_') ||
    role.includes('Regional_')
  );
  
  console.log('Functional roles found:', functionalRoles);
  
  if (functionalRoles.length > 0) {
    return {
      level: 'functional',
      description: 'Functionaris - Toegang tot specifieke functies',
      icon: '📋'
    };
  }
  
  // Basic member
  if (roles.includes('hdcnLeden')) {
    return {
      level: 'basic',
      description: 'Basis lid - Toegang tot persoonlijke gegevens en webshop',
      icon: '✓'
    };
  }
  
  return {
    level: 'basic',
    description: 'Beperkte toegang',
    icon: 'ℹ️'
  };
}

console.log('=== Testing Role Detection for webmaster@h-dcn.nl ===');
const result = getAccessLevelSummary(webmasterRoles);
console.log('Final result:', result);
console.log('Expected: System level access');
console.log('Actual:', result.level, '-', result.description);