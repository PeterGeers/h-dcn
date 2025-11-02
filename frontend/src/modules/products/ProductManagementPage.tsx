import { useEffect, useState } from 'react';
import { scanProducts, updateProduct, deleteProduct, insertProduct } from './api/productApi';
import ProductTable from './components/ProductTable';
import ProductCard from './components/ProductCard';
import ProductFilter from './components/ProductFilter';
import Header from './components/Header';
import { Product } from '../../types';

import { Button, Box, HStack, Stack } from '@chakra-ui/react';

interface FilterOption {
  type: 'group' | 'subgroup';
  value: string;
  group?: string;
}

export default function ProductManagementPage() {
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

  return (
    <>
      <Header />
      <Stack direction={{ base: 'column', lg: 'row' }} align="start" spacing={6}>
        <Box w={{ base: 'full', lg: '300px' }}>
          <ProductFilter
            products={products}
            selectedFilter={selectedFilter}
            onFilterChange={setSelectedFilter}
          />
        </Box>
        <Box flex={1}>
          <ProductTable
            products={filteredProducts}
            onSelect={setSelected}
          />
        </Box>
      </Stack>
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
