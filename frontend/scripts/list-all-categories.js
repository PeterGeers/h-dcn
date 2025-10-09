// Script om alle categorieën uit DynamoDB parameter tabel te tonen
const API_BASE_URL = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function listAllCategories() {
  try {
    const response = await fetch(`${API_BASE_URL}/parameters`);
    const data = await response.json();
    
    console.log('Alle categorieën in DynamoDB parameter tabel:');
    console.log('==============================================');
    
    // Groepeer parameters per categorie
    const categories = {};
    
    data.forEach(item => {
      const categoryName = item.name;
      if (!categories[categoryName]) {
        categories[categoryName] = {
          description: item.description,
          created_at: item.created_at,
          parameter_id: item.parameter_id
        };
      }
    });
    
    // Toon alle categorieën
    Object.entries(categories).forEach(([name, info]) => {
      console.log(`📁 ${name}`);
      console.log(`   Beschrijving: ${info.description || 'Geen beschrijving'}`);
      console.log(`   Aangemaakt: ${info.created_at ? new Date(info.created_at).toLocaleDateString('nl-NL') : 'Onbekend'}`);
      console.log(`   ID: ${info.parameter_id}`);
      console.log('');
    });
    
    console.log(`Totaal aantal categorieën: ${Object.keys(categories).length}`);
    
  } catch (error) {
    console.error('Fout bij ophalen categorieën:', error);
  }
}

listAllCategories();