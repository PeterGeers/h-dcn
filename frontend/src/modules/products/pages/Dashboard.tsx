import React, { useEffect, useState, useMemo } from 'react';
import { scanProducts, updateProduct, deleteProduct, insertProduct } from '../api/productApi';
import ProductTable from '../components/ProductTable';
import ProductCard from '../components/ProductCard';
import Header from '../components/Header';
import { cleanupUnusedImages } from '../services/s3Upload';
import { Button, Box, HStack } from '@chakra-ui/react';
import { Product } from '../../../types';
import { FilterPanel, GenericFilter } from '../../../components/filters';

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
    const { opties, ...cleanData } = data as any;
    const processedData = {
      ...cleanData,
      prijs: cleanData.prijs ? cleanData.prijs.toString() : cleanData.prijs
    };
    const productId = data.product_id || data.id;
    if (productId) {
      updateProduct(productId, processedData)
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

  const [selectedGroep, setSelectedGroep] = useState<string>('');
  const [selectedSubgroep, setSelectedSubgroep] = useState<string>('');
  const [cleaning, setCleaning] = useState(false);

  const { groepOptions, subgroepOptions } = useMemo(() => {
    const groups = new Set<string>();
    const subgroups = new Set<string>();
    products.forEach(p => {
      if (p.groep) groups.add(p.groep);
      if (p.subgroep && (!selectedGroep || p.groep === selectedGroep)) {
        subgroups.add(p.subgroep);
      }
    });
    return {
      groepOptions: Array.from(groups).sort().map(g => ({ value: g, label: g })),
      subgroepOptions: Array.from(subgroups).sort().map(s => ({ value: s, label: s })),
    };
  }, [products, selectedGroep]);

  const filteredProducts = products.filter((p: Product) => {
    if (selectedGroep && p.groep !== selectedGroep) return false;
    if (selectedSubgroep && p.subgroep !== selectedSubgroep) return false;
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
        <Box w="300px">
          <FilterPanel
            hasActiveFilters={!!selectedGroep || !!selectedSubgroep}
            onReset={() => { setSelectedGroep(''); setSelectedSubgroep(''); }}
          >
            <GenericFilter
              label="Groep"
              value={selectedGroep}
              options={groepOptions}
              onChange={(v) => { setSelectedGroep(v); setSelectedSubgroep(''); }}
              placeholder="Alle groepen"
            />
            {subgroepOptions.length > 0 && (
              <GenericFilter
                label="Subgroep"
                value={selectedSubgroep}
                options={subgroepOptions}
                onChange={setSelectedSubgroep}
                placeholder="Alle subgroepen"
              />
            )}
          </FilterPanel>
        </Box>
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
          onNew={() => setSelected({ product_id: '', naam: '', prijs: '', groep: '', subgroep: '' })}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
