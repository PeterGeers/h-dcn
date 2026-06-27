import { HStack, IconButton, Text } from '@chakra-ui/react';
import { DeleteIcon, CheckIcon, CopyIcon } from '@chakra-ui/icons';
import { Product } from '../../../types';

interface ProductCardActionsProps {
  product: Product;
  readOnly: boolean;
  onDelete: (id: string) => void;
  onNew: () => void;
  onCopy?: (product: Product) => void;
}

/**
 * Action buttons for ProductCard: save, delete, copy.
 * Renders read-only message when user has no edit permissions.
 */
export function ProductCardActions({ product, readOnly, onDelete, onNew, onCopy }: ProductCardActionsProps) {
  return (
    <HStack spacing={4}>
      {!readOnly && (
        <IconButton
          icon={<CheckIcon />}
          colorScheme="orange"
          size="sm"
          type="submit"
          aria-label="Opslaan"
          isDisabled={false}
          _hover={{ bg: 'orange.600' }}
        />
      )}
      {!readOnly && product.id && (
        <IconButton
          icon={<DeleteIcon />}
          colorScheme="red"
          size="sm"
          onClick={() => onDelete(product.id)}
          aria-label="Verwijder product"
          _hover={{ bg: 'red.600' }}
        />
      )}
      {!readOnly && (
        <IconButton
          icon={<CopyIcon />}
          colorScheme="green"
          size="sm"
          onClick={() => onCopy ? onCopy(product) : onNew()}
          aria-label="Kopieer product"
          _hover={{ bg: 'green.600' }}
        />
      )}
      {readOnly && (
        <Text fontSize="sm" color="gray.600" fontStyle="italic">
          Alleen-lezen modus - geen bewerkingsrechten
        </Text>
      )}
    </HStack>
  );
}
