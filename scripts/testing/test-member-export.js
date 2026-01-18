// Simple test for the new member export endpoint
// Much simpler than parquet files!

const API_BASE_URL = 'https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod';

async function testMemberExport() {
    try {
        console.log('🧪 Testing simple member export endpoint...');
        
        // You'll need to replace this with a real JWT token
        const token = 'YOUR_JWT_TOKEN_HERE';
        
        const response = await fetch(`${API_BASE_URL}/members/export`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        console.log('📡 Response status:', response.status);
        console.log('📡 Response headers:', Object.fromEntries(response.headers.entries()));
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Success! Member export data:');
            console.log('📊 Total members:', data.data?.length || 0);
            console.log('📅 Export date:', data.metadata?.export_date);
            console.log('👤 User email:', data.metadata?.user_email);
            console.log('🌍 Regional filtering applied:', data.metadata?.applied_filters?.regional);
            
            if (data.data && data.data.length > 0) {
                console.log('👥 Sample member:', data.data[0]);
            }
        } else {
            const errorText = await response.text();
            console.log('❌ Error response:', errorText);
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

console.log('🚀 Simple Member Export Test');
console.log('============================');
console.log('This is much simpler than parquet files!');
console.log('- Standard JSON API response');
console.log('- No binary data handling');
console.log('- No CORS issues');
console.log('- No web workers needed');
console.log('');

testMemberExport();