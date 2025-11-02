import React, { useEffect, useState } from 'react';
import { scanProducts, updateProduct, deleteProduct, insertProduct } from '../api/productApi';
import ProductTable from '../components/ProductTable';
import ProductCard from '../components/ProductCard';
import ProductFilter from '../components/ProductFilter';
import Header from '../components/Header';
import { cleanupUnusedImages } from '../services/s3Upload';
import { Button, Box, HStack } from '@chakra-ui/react';
import { Product } from '../../../types';

interface FilterOption {
  type: 'group' | 'subgroup';
  value: string;
  group?: string;
}

export default function Dashboard(): React.ReactElement {
  const [products, setProducts] = useState<Product[]>([]);
  const [selected, setSelected] = useState<Product | null>(null);

  useEffect(() => {
    scanProducts()
      .then(res => {
        setProducts(res.data || []);
      })
      .catch((error: any) => {
        console.error('Error loading products:', error);
        setProducts([]);
      });
  }, []);

  const handleSave = (data: Product) => {
    console.log('Saving product data:', data);
    const processedData = {
      ...data,
      prijs: data.prijs ? data.prijs.toString() : data.prijs
    };
    if (data.id) {
      updateProduct(data.id, processedData)
        .then(() => refresh())
        .catch((error: any) => {
          console.error('Update error:', error.response?.data || error.message);
        });
    } else {
      insertProduct(processedData)
        .then(() => refresh())
        .catch((error: any) => {
          console.error('Insert error:', error.response?.data || error.message);
        });
    }
  };

  const handleDelete = (id: string) => {
    deleteProduct(id).then(() => refresh());
  };

  const refresh = () => {
    scanProducts().then(res => setProducts(res.data));
    setSelected(null);
  };

  const [selectedFilter, setSelectedFilter] = useState<FilterOption | null>(null);
  const [cleaning, setCleaning] = useState(false);

  const filteredProducts = products.filter((p: Product) => {
    if (!selectedFilter) return true;
    if (selectedFilter.type === 'group') {
      return p.groep === selectedFilter.value;
    }
    if (selectedFilter.type === 'subgroup') {
      return p.groep === selectedFilter.group && p.subgroep === selectedFilter.value;
    }
    return true;
  });



  const handleCleanup = async () => {
    setCleaning(true);
    try {
      const deletedCount = await cleanupUnusedImages(products);
      alert(`${deletedCount} ongebruikte afbeeldingen verwijderd uit S3`);
    } catch (error: any) {
      alert('Cleanup failed: ' + error.message);
    } finally {
      setCleaning(false);
    }
  };

  return (
    <>
      <Header />
      <Box p={4}>
        <Button
          colorScheme="red"
          onClick={handleCleanup}
          isLoading={cleaning}
          loadingText="Cleaning..."
          mb={4}
        >
          Opschonen Afbeeldingen
        </Button>
      </Box>
      <HStack align="start" spacing={6}>
        <ProductFilter
          products={products}
          selectedFilter={selectedFilter}
          onFilterChange={setSelectedFilter}
        />
        <Box flex={1}>
          <ProductTable
            products={filteredProducts}
            onSelect={setSelected}
          />
        </Box>
      </HStack>
      {selected && (
        <ProductCard
          key={selected.id}
          product={selected}
          products={products}
          filteredProducts={filteredProducts}
          onSave={handleSave}
          onDelete={handleDelete}
          onNew={() => setSelected({ id: '', name: '', naam: '', price: 0, category: '', groep: '', subgroep: '', opties: [] })}
          onClose={() => setSelected(null)}
          onNavigate={setSelected}
        />
      )}
    </>
  );
}
