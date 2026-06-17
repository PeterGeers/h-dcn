/**
 * ProductCard Integration Unit Tests
 *
 * Tests:
 * - ProductCard renders VariantSubTable (Requirement 2.1)
 * - ProductCard does NOT render VariantSchemaEditor (Requirement 1.1)
 * - ProductCard has no navigation arrows (Requirement 11.2)
 * - Images wrapped in CollapsibleSection "Afbeeldingen" (Requirement 10.1)
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// --- Mock all heavy dependencies ---

// Mock Chakra UI — provide minimal pass-through implementations
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children }: any) => <div>{children}</div>,
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} aria-label={props['aria-label']}>{children}</button>
  ),
  IconButton: ({ onClick, ...props }: any) => (
    <button onClick={onClick} aria-label={props['aria-label']} />
  ),
  Input: ({ placeholder, ...props }: any) => <input placeholder={placeholder} />,
  InputGroup: ({ children }: any) => <div>{children}</div>,
  InputLeftAddon: ({ children }: any) => <span>{children}</span>,
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Image: ({ src }: any) => <img src={src} alt="" />,
  Badge: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children }: any) => <span>{children}</span>,
  TagLabel: ({ children }: any) => <span>{children}</span>,
  Wrap: ({ children }: any) => <div>{children}</div>,
  WrapItem: ({ children }: any) => <div>{children}</div>,
  FormControl: ({ children }: any) => <div>{children}</div>,
  FormErrorMessage: ({ children }: any) => <span>{children}</span>,
  Collapse: ({ children, in: isOpen }: any) => (isOpen ? <div>{children}</div> : null),
  Modal: ({ children, isOpen }: any) => (isOpen ? <div>{children}</div> : null),
  ModalOverlay: () => null,
  ModalContent: ({ children }: any) => <div>{children}</div>,
  ModalHeader: ({ children }: any) => <div>{children}</div>,
  ModalBody: ({ children }: any) => <div>{children}</div>,
  ModalFooter: ({ children }: any) => <div>{children}</div>,
  ModalCloseButton: () => null,
  useDisclosure: () => ({ isOpen: true, onOpen: jest.fn(), onClose: jest.fn(), onToggle: jest.fn() }),
  useToast: () => jest.fn(),
}))

jest.mock('@chakra-ui/icons', () => ({
  ChevronDownIcon: () => <span data-testid="chevron-down" />,
  ChevronRightIcon: () => <span data-testid="chevron-right" />,
  ChevronLeftIcon: () => <span data-testid="chevron-left" />,
  CloseIcon: () => <span data-testid="close-icon" />,
  DeleteIcon: () => <span data-testid="delete-icon" />,
  CheckIcon: () => <span data-testid="check-icon" />,
  AddIcon: () => <span data-testid="add-icon" />,
}));

// Mock Formik — render children with mock form context
jest.mock('formik', () => ({
  Formik: ({ children, initialValues }: any) => {
    const formikBag = {
      values: initialValues,
      setFieldValue: jest.fn(),
      errors: {},
      touched: {},
      isSubmitting: false,
      submitCount: 0,
    };
    return <div data-testid="formik-form">{typeof children === 'function' ? children(formikBag) : children}</div>;
  },
  Form: ({ children }: any) => <form>{children}</form>,
  Field: ({ name, placeholder, as: Component, ...props }: any) => {
    if (typeof Component === 'function' || typeof Component === 'object') {
      return <Component placeholder={placeholder} name={name} {...props} />;
    }
    // For render prop pattern
    if (props.children && typeof props.children === 'function') {
      return props.children({ field: { name, value: '' }, form: { setFieldValue: jest.fn() } });
    }
    return <input name={name} placeholder={placeholder} />;
  },
}));

// Mock Yup (avoid actual schema logic)
jest.mock('yup', () => ({
  object: () => ({ shape: () => ({}) }),
  mixed: () => ({ required: () => ({}) }),
  string: () => ({ required: () => ({}) }),
}));

// Mock s3Upload
jest.mock('../services/s3Upload', () => ({
  uploadToS3: jest.fn().mockResolvedValue('https://s3.example.com/img.jpg'),
}));

// Mock authHeaders
jest.mock('../../../utils/authHeaders', () => ({
  getAuthHeadersForGet: jest.fn().mockResolvedValue({ Authorization: 'Bearer test' }),
}));

// Mock API config
jest.mock('../../../config/api', () => ({
  API_URLS: {
    base: 'https://api.test.com',
    events: () => 'https://api.test.com/events',
  },
}));

// Mock productFields config
jest.mock('../../../config/productFields', () => ({
  getRequiredFields: () => ['naam', 'prijs', 'groep'],
  getProductField: (key: string) => ({ key, label: key, inputType: 'text' }),
}));

// Mock VariantSubTable — render identifiable element
jest.mock('../../webshop-management/components/VariantSubTable', () => ({
  VariantSubTable: (props: any) => (
    <div data-testid="variant-sub-table">VariantSubTable</div>
  ),
}));

// Mock VariantEditModal
jest.mock('../components/VariantEditModal', () => ({
  VariantEditModal: () => <div data-testid="variant-edit-modal" />,
}));

// Mock EventSelectorSection
jest.mock('../components/EventSelectorSection', () => ({
  __esModule: true,
  default: () => <div data-testid="event-selector-section">EventSelectorSection</div>,
}));

// Mock OrderItemFieldsEditor
jest.mock('../components/OrderItemFieldsEditor', () => ({
  __esModule: true,
  default: () => <div data-testid="order-item-fields-editor">OrderItemFieldsEditor</div>,
}));

// Mock PurchaseRulesEditor
jest.mock('../components/PurchaseRulesEditor', () => ({
  __esModule: true,
  default: () => <div data-testid="purchase-rules-editor">PurchaseRulesEditor</div>,
}));

// Mock global fetch
global.fetch = jest.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ variants: [] }),
});

// Import component after mocks
import ProductCard from '../components/ProductCard';
import { Product } from '../../../types';

// --- Test data ---

const mockParentProduct: Product = {
  product_id: 'prod_001',
  id: 'prod_001',
  naam: 'Test Product',
  prijs: '10.00',
  artikelcode: 'T1',
  groep: 'Kleding',
  subgroep: 'Shirts',
  images: ['https://s3.example.com/image1.jpg'],
  is_parent: true,
  active: true,
  event_ids: [],
};

const defaultProps = {
  product: mockParentProduct,
  products: [mockParentProduct],
  onSave: jest.fn(),
  onDelete: jest.fn(),
  onNew: jest.fn(),
  onClose: jest.fn(),
  filteredProducts: [mockParentProduct],
  readOnly: false,
};

// --- Tests ---

describe('ProductCard Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ variants: [] }),
    });
  });

  describe('Renders VariantSubTable (Requirement 2.1)', () => {
    it('renders VariantSubTable for parent products', () => {
      render(<ProductCard {...defaultProps} />);

      expect(screen.getByTestId('variant-sub-table')).toBeInTheDocument();
    });

    it('renders "Varianten" section header for parent products', () => {
      render(<ProductCard {...defaultProps} />);

      expect(screen.getByText('Varianten')).toBeInTheDocument();
    });
  });

  describe('Does NOT render VariantSchemaEditor (Requirement 1.1)', () => {
    it('does not render VariantSchemaEditor text or component', () => {
      render(<ProductCard {...defaultProps} />);

      expect(screen.queryByText('VariantSchemaEditor')).not.toBeInTheDocument();
      expect(screen.queryByText('Sync varianten')).not.toBeInTheDocument();
    });
  });

  describe('No navigation arrows (Requirement 11.2)', () => {
    it('does not render ChevronLeftIcon navigation arrow', () => {
      render(<ProductCard {...defaultProps} />);

      expect(screen.queryByTestId('chevron-left')).not.toBeInTheDocument();
    });

    it('does not render navigation arrow buttons with left/right labels', () => {
      render(<ProductCard {...defaultProps} />);

      expect(screen.queryByLabelText('Vorig product')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Volgend product')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Previous')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Next')).not.toBeInTheDocument();
    });
  });

  describe('Images wrapped in CollapsibleSection (Requirement 10.1)', () => {
    it('renders "Afbeeldingen" CollapsibleSection title', () => {
      render(<ProductCard {...defaultProps} />);

      expect(screen.getByText('Afbeeldingen')).toBeInTheDocument();
    });

    it('renders image upload button inside the Afbeeldingen section', () => {
      render(<ProductCard {...defaultProps} />);

      // The "+ Afbeeldingen" upload button is inside the CollapsibleSection
      expect(screen.getByText('+ Afbeeldingen')).toBeInTheDocument();
    });
  });
});
