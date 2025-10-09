// Script om categorieën uit DynamoDB te tonen
const API_BASE_URL = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function listCategories() {
  try {
    const response = await fetch(`${API_BASE_URL}/parameters`);
    const data = await response.json();
    
    console.log('Categorieën in DynamoDB:');
    console.log('========================');
    
    data.forEach(item => {
      console.log(`- ${item.name} (ID: ${item.id})`);
    });
    
  } catch (error) {
    console.error('Fout bij ophalen categorieën:', error);
  }
}

listCategories();