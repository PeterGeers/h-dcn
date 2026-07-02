import { HStack, IconButton, Text, Tooltip } from '@chakra-ui/react';
import { DeleteIcon, CheckIcon, CopyIcon, NotAllowedIcon } from '@chakra-ui/icons';
import { Product } from '../../../types';
import { isActive } from '../../../utils/productHelpers';
import { useTranslation } from 'react-i18next';

interface ProductCardActionsProps {
  product: Product;
  readOnly: boolean;
  onDelete: (id: string) => void;
  onNew: () => void;
  onCopy?: (product: Product) => void;
  onDeactivate?: (product: Product) => void;
  onActivate?: (product: Product) => void;
  onHardDelete?: (product: Product) => void;
}

/**
 * Action buttons for ProductCard: save, deactivate/activate, hard-delete, copy.
 * Renders read-only message when user has no edit permissions.
 */
export function ProductCardActions({
  product,
  readOnly,
  onDelete,
  onNew,
  onCopy,
  onDeactivate,
  onActivate,
  onHardDelete,
}: ProductCardActionsProps) {
  const { t } = useTranslation('products');
  const productId = product.product_id || product.id;

  return (
    <HStack spacing={3} flexWrap="wrap">
      {!readOnly && (
        <Tooltip label="Opslaan">
          <IconButton
            icon={<CheckIcon />}
            colorScheme="orange"
            size="sm"
            type="submit"
            aria-label="Opslaan"
            _hover={{ bg: 'orange.600' }}
          />
        </Tooltip>
      )}
      {!readOnly && onCopy && (
        <Tooltip label="Kopieer product">
          <IconButton
            icon={<CopyIcon />}
            colorScheme="green"
            size="sm"
            onClick={() => onCopy(product)}
            aria-label="Kopieer product"
            _hover={{ bg: 'green.600' }}
          />
        </Tooltip>
      )}
      {!readOnly && productId && isActive(product) && onDeactivate && (
        <Tooltip label={t('management.deactivate')}>
          <IconButton
            icon={<NotAllowedIcon />}
            colorScheme="yellow"
            size="sm"
            variant="outline"
            onClick={() => onDeactivate(product)}
            aria-label={t('management.deactivate')}
          />
        </Tooltip>
      )}
      {!readOnly && productId && !isActive(product) && onActivate && (
        <Tooltip label={t('management.activate')}>
          <IconButton
            icon={<CheckIcon />}
            colorScheme="green"
            size="sm"
            variant="outline"
            onClick={() => onActivate(product)}
            aria-label={t('management.activate')}
          />
        </Tooltip>
      )}
      {!readOnly && productId && onHardDelete && (
        <Tooltip label={t('management.hard_delete')}>
          <IconButton
            icon={<DeleteIcon />}
            colorScheme="red"
            size="sm"
            variant="outline"
            onClick={() => onHardDelete(product)}
            aria-label={t('management.hard_delete')}
          />
        </Tooltip>
      )}
      {readOnly && (
        <Text fontSize="sm" color="gray.600" fontStyle="italic">
          Alleen-lezen modus - geen bewerkingsrechten
        </Text>
      )}
    </HStack>
  );
}
