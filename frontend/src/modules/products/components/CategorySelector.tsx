import { Box, Button, VStack, HStack, Text, Input, Collapse, useDisclosure } from '@chakra-ui/react';
import { ChevronDownIcon, ChevronRightIcon as ChevronRight } from '@chakra-ui/icons';

export interface CategoryStructure {
  [key: string]: {
    children?: {
      [key: string]: any;
    };
  };
}

interface CategoryDisplayProps {
  groep: string;
  subgroep: string;
  onClick: () => void;
  readOnly: boolean;
}

/**
 * Inline display for selected category (clickable to open modal).
 */
export function CategoryDisplay({ groep, subgroep, onClick, readOnly }: CategoryDisplayProps) {
  const displayText = groep && subgroep
    ? `${groep} - ${subgroep}`
    : groep
      ? groep
      : 'Selecteer categorie...';

  return (
    <Box
      height="40px"
      px={4}
      py={2}
      bg="gray.600"
      borderRadius="md"
      border="1px solid"
      borderColor="gray.500"
      cursor={readOnly ? 'default' : 'pointer'}
      onClick={readOnly ? undefined : onClick}
      _hover={readOnly ? {} : { borderColor: 'gray.400' }}
      display="flex"
      alignItems="center"
      fontSize="md"
      width="100%"
      _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 1px #3182ce' }}
    >
      <Text color={groep ? 'white' : 'gray.300'}>
        {displayText}
      </Text>
    </Box>
  );
}

interface CategorySelectorProps {
  setFieldValue: (field: string, value: any) => void;
  categoryStructure: CategoryStructure;
  selectedCategory: { groep: string; subgroep: string };
  setSelectedCategory: (cat: { groep: string; subgroep: string }) => void;
  readOnly: boolean;
  onCategoryModalClose: () => void;
}

interface GroupItemProps {
  groupName: string;
  groupData: {
    children?: {
      [key: string]: any;
    };
  };
  selectedCategory: { groep: string; subgroep: string };
  setSelectedCategory: (cat: { groep: string; subgroep: string }) => void;
  setFieldValue: (field: string, value: any) => void;
  readOnly: boolean;
  onCategoryModalClose: () => void;
}

function GroupItem({ groupName, groupData, selectedCategory, setSelectedCategory, setFieldValue, readOnly, onCategoryModalClose }: GroupItemProps) {
  const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: selectedCategory.groep === groupName });
  const hasChildren = groupData.children && Object.keys(groupData.children).length > 0;

  return (
    <Box>
      <Button
        variant="ghost"
        justifyContent="flex-start"
        width="full"
        size="sm"
        fontSize="md"
        py={2}
        leftIcon={hasChildren ? (isOpen ? <ChevronDownIcon /> : <ChevronRight />) : undefined}
        onClick={() => {
          if (hasChildren) {
            onToggle();
          } else if (!readOnly) {
            setSelectedCategory({ groep: groupName, subgroep: '' });
            setFieldValue('groep', groupName);
            setFieldValue('subgroep', '');
            onCategoryModalClose();
          }
        }}
        color="white"
        bg={selectedCategory.groep === groupName && !selectedCategory.subgroep ? 'orange.600' : 'transparent'}
        _hover={{ bg: readOnly ? 'transparent' : 'gray.700' }}
        isDisabled={readOnly}
        fontWeight={selectedCategory.groep === groupName ? 'bold' : 'normal'}
      >
        {groupName}
        {!hasChildren && <Text fontSize="xs" color="gray.500" ml={2}>(geen subgroepen)</Text>}
      </Button>

      {hasChildren && (
        <Collapse in={isOpen}>
          <VStack align="stretch" pl={6} spacing={1} mt={1}>
            {Object.entries(groupData.children!).map(([subgroup]) => (
              <Button
                key={subgroup}
                variant="ghost"
                size="sm"
                fontSize="sm"
                py={2}
                justifyContent="flex-start"
                onClick={() => {
                  if (!readOnly) {
                    setSelectedCategory({ groep: groupName, subgroep: subgroup });
                    setFieldValue('groep', groupName);
                    setFieldValue('subgroep', subgroup);
                    onCategoryModalClose();
                  }
                }}
                color="white"
                bg={selectedCategory.groep === groupName && selectedCategory.subgroep === subgroup ? 'orange.700' : 'transparent'}
                _hover={{ bg: readOnly ? 'transparent' : 'gray.700' }}
                isDisabled={readOnly}
                fontWeight={selectedCategory.groep === groupName && selectedCategory.subgroep === subgroup ? 'bold' : 'normal'}
                borderLeft="2px solid"
                borderColor="orange.400"
                borderRadius="0"
                ml={2}
              >
                📁 {subgroup}
              </Button>
            ))}
          </VStack>
        </Collapse>
      )}
    </Box>
  );
}

/**
 * Category tree selector for ProductCard.
 * Renders existing categories with expand/collapse and allows adding new ones.
 */
export function CategorySelector({ setFieldValue, categoryStructure, selectedCategory, setSelectedCategory, readOnly, onCategoryModalClose }: CategorySelectorProps) {
  return (
    <Box p={3} bg="gray.800" borderRadius="md" border="1px solid" borderColor="gray.600" maxH="400px" overflowY="auto">
      <Text fontSize="md" fontWeight="bold" mb={3} color="white">
        {readOnly ? 'Categorie (alleen-lezen):' : 'Selecteer Categorie:'}
      </Text>

      <VStack align="stretch" spacing={1}>
        {Object.keys(categoryStructure).length === 0 ? (
          <Text fontSize="sm" color="gray.500" textAlign="center" py={4}>
            Geen categorieën beschikbaar
          </Text>
        ) : (
          Object.entries(categoryStructure).map(([groupName, groupData]) => (
            <GroupItem
              key={groupName}
              groupName={groupName}
              groupData={groupData}
              selectedCategory={selectedCategory}
              setSelectedCategory={setSelectedCategory}
              setFieldValue={setFieldValue}
              readOnly={readOnly}
              onCategoryModalClose={onCategoryModalClose}
            />
          ))
        )}
      </VStack>

      {/* New group/subgroup inputs */}
      {!readOnly && (
        <Box mt={4} pt={3} borderTop="1px solid" borderColor="gray.300">
          <Text fontSize="sm" fontWeight="bold" color="gray.200" mb={2}>Nieuwe categorie toevoegen:</Text>
          <HStack spacing={2} mb={2}>
            <Input
              size="sm"
              placeholder="Nieuwe groep"
              bg="gray.600"
              color="white"
              borderColor="gray.500"
              _placeholder={{ color: 'gray.300' }}
              id="new-group-input"
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                if (e.key === 'Enter') {
                  const val = (e.target as HTMLInputElement).value.trim();
                  if (val) {
                    setSelectedCategory({ groep: val, subgroep: '' });
                    setFieldValue('groep', val);
                    setFieldValue('subgroep', '');
                    onCategoryModalClose();
                  }
                }
              }}
            />
            <Button size="sm" colorScheme="orange" onClick={() => {
              const input = document.getElementById('new-group-input') as HTMLInputElement;
              const val = input?.value?.trim();
              if (val) {
                setSelectedCategory({ groep: val, subgroep: '' });
                setFieldValue('groep', val);
                setFieldValue('subgroep', '');
                onCategoryModalClose();
              }
            }}>+</Button>
          </HStack>
          <HStack spacing={2}>
            <Input
              size="sm"
              placeholder="Nieuwe subgroep"
              bg="gray.600"
              color="white"
              borderColor="gray.500"
              _placeholder={{ color: 'gray.300' }}
              id="new-subgroup-input"
              isDisabled={!selectedCategory.groep}
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                if (e.key === 'Enter' && selectedCategory.groep) {
                  const val = (e.target as HTMLInputElement).value.trim();
                  if (val) {
                    setSelectedCategory({ groep: selectedCategory.groep, subgroep: val });
                    setFieldValue('groep', selectedCategory.groep);
                    setFieldValue('subgroep', val);
                    onCategoryModalClose();
                  }
                }
              }}
            />
            <Button size="sm" colorScheme="orange" isDisabled={!selectedCategory.groep} onClick={() => {
              const input = document.getElementById('new-subgroup-input') as HTMLInputElement;
              const val = input?.value?.trim();
              if (val && selectedCategory.groep) {
                setSelectedCategory({ groep: selectedCategory.groep, subgroep: val });
                setFieldValue('groep', selectedCategory.groep);
                setFieldValue('subgroep', val);
                onCategoryModalClose();
              }
            }}>+</Button>
          </HStack>
          <Text fontSize="xs" color="gray.500" mt={1}>Typ een naam en druk Enter of klik +</Text>
        </Box>
      )}
    </Box>
  );
}
