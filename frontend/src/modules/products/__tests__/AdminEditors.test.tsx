/**
 * Admin Editors Tests
 *
 * Tests for OrderItemFieldsEditor: field CRUD operations,
 * validation errors, and limit enforcement.
 *
 * Note: VariantSchemaEditor and PurchaseRulesEditor already have
 * dedicated test files. This file covers OrderItemFieldsEditor.
 *
 * Validates: Requirements 13.1, 13.3, 13.5, 13.7
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Button: ({ children, onClick, isDisabled, leftIcon, ...props }: any) => (
    <button onClick={onClick} disabled={isDisabled} {...props}>
      {children}
    </button>
  ),
  FormControl: ({ children, isInvalid, ...props }: any) => (
    <div data-invalid={isInvalid} {...props}>{children}</div>
  ),
  FormLabel: ({ children, ...props }: any) => <label {...props}>{children}</label>,
  FormErrorMessage: ({ children, ...props }: any) => (
    <span role="alert" {...props}>{children}</span>
  ),
  IconButton: ({ 'aria-label': ariaLabel, onClick, isDisabled, ...props }: any) => (
    <button aria-label={ariaLabel} onClick={onClick} disabled={isDisabled} {...props} />
  ),
  Input: ({ value, onChange, placeholder, maxLength, ...props }: any) => (
    <input value={value} onChange={onChange} placeholder={placeholder} maxLength={maxLength} {...props} />
  ),
  Select: ({ children, value, onChange, ...props }: any) => (
    <select value={value} onChange={onChange} {...props}>
      {children}
    </select>
  ),
  Switch: ({ isChecked, onChange, ...props }: any) => (
    <input type="checkbox" checked={isChecked} onChange={onChange} {...props} />
  ),
  VStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  HStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Text: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  Heading: ({ children, ...props }: any) => <h4 {...props}>{children}</h4>,
  Tag: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  TagLabel: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  TagCloseButton: ({ onClick, ...props }: any) => (
    <button aria-label="close" onClick={onClick} {...props} />
  ),
  Wrap: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  WrapItem: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

jest.mock('@chakra-ui/icons', () => ({
  AddIcon: () => <span data-testid="add-icon" />,
  DeleteIcon: () => <span data-testid="delete-icon" />,
}));

import OrderItemFieldsEditor, {
  OrderItemFieldsEditorProps,
  validateOrderItemFields,
} from '../components/OrderItemFieldsEditor';
import { OrderItemField } from '../../webshop/types/unifiedProduct.types';

// --- Test helpers ---

const createField = (overrides: Partial<OrderItemField> = {}): OrderItemField => ({
  id: 'test-field',
  label: 'Test Field',
  type: 'text',
  required: false,
  ...overrides,
});

const renderEditor = (
  value: OrderItemField[] = [],
  onChange = jest.fn(),
  errors: Record<string, string> = {}
) => {
  let result: ReturnType<typeof render>;
  act(() => {
    result = render(
      <OrderItemFieldsEditor value={value} onChange={onChange} errors={errors} />
    );
  });
  return { ...result!, onChange };
};

describe('OrderItemFieldsEditor', () => {
  describe('field CRUD operations', () => {
    it('renders add field button', () => {
      renderEditor();
      expect(screen.getByText('Veld toevoegen')).toBeInTheDocument();
    });

    it('calls onChange with a new empty field when add is clicked', () => {
      const onChange = jest.fn();
      renderEditor([], onChange);
      fireEvent.click(screen.getByText('Veld toevoegen'));

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({
          id: '',
          label: '',
          type: 'text',
          required: false,
        }),
      ]);
    });

    it('renders existing fields with their labels', () => {
      renderEditor([
        createField({ id: 'naam', label: 'Naam deelnemer' }),
        createField({ id: 'email', label: 'E-mailadres' }),
      ]);

      expect(screen.getByDisplayValue('Naam deelnemer')).toBeInTheDocument();
      expect(screen.getByDisplayValue('E-mailadres')).toBeInTheDocument();
    });

    it('renders field count indicator', () => {
      renderEditor([createField(), createField()]);
      expect(screen.getByText('Velden (2/20)')).toBeInTheDocument();
    });

    it('calls onChange with field removed when delete is clicked', () => {
      const onChange = jest.fn();
      renderEditor(
        [
          createField({ id: 'field1', label: 'Field 1' }),
          createField({ id: 'field2', label: 'Field 2' }),
        ],
        onChange
      );

      const deleteButtons = screen.getAllByLabelText('Veld verwijderen');
      fireEvent.click(deleteButtons[0]);

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({ id: 'field2', label: 'Field 2' }),
      ]);
    });

    it('calls onChange when label is modified', () => {
      const onChange = jest.fn();
      renderEditor([createField({ id: 'test', label: 'Test' })], onChange);

      const labelInput = screen.getByDisplayValue('Test');
      fireEvent.change(labelInput, { target: { value: 'Nieuwe Naam' } });

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({ label: 'Nieuwe Naam' }),
      ]);
    });

    it('auto-generates id from label when id matches previous label conversion', () => {
      const onChange = jest.fn();
      // Field where id matches the kebab-case of the label (auto-generated)
      renderEditor([createField({ id: '', label: '' })], onChange);

      const labelInputs = screen.getAllByPlaceholderText('Bijv. Naam deelnemer');
      fireEvent.change(labelInputs[0], { target: { value: 'Naam deelnemer' } });

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({
          label: 'Naam deelnemer',
          id: 'naam-deelnemer',
        }),
      ]);
    });

    it('calls onChange when type is changed', () => {
      const onChange = jest.fn();
      renderEditor([createField({ id: 'test', label: 'Test', type: 'text' })], onChange);

      const typeSelects = screen.getAllByRole('combobox');
      // Find the type select (the one with 'Tekst' option)
      const typeSelect = typeSelects.find((s) =>
        Array.from(s.querySelectorAll('option')).some((o) => o.textContent === 'Tekst')
      );
      fireEvent.change(typeSelect!, { target: { value: 'select' } });

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({ type: 'select', options: [] }),
      ]);
    });

    it('calls onChange when required toggle is changed', () => {
      const onChange = jest.fn();
      renderEditor([createField({ id: 'test', label: 'Test', required: false })], onChange);

      const checkbox = screen.getByRole('checkbox');
      fireEvent.click(checkbox);

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({ required: true }),
      ]);
    });
  });

  describe('limit enforcement', () => {
    it('disables add button when 20 fields exist', () => {
      const fields = Array.from({ length: 20 }, (_, i) =>
        createField({ id: `field_${i}`, label: `Field ${i}` })
      );
      renderEditor(fields);

      expect(screen.getByText('Veld toevoegen')).toBeDisabled();
    });

    it('displays max limit reached message when 20 fields exist', () => {
      const fields = Array.from({ length: 20 }, (_, i) =>
        createField({ id: `field_${i}`, label: `Field ${i}` })
      );
      renderEditor(fields);

      expect(
        screen.getByText('Maximum aantal velden (20) bereikt.')
      ).toBeInTheDocument();
    });

    it('enables add button when fewer than 20 fields exist', () => {
      renderEditor([createField()]);
      expect(screen.getByText('Veld toevoegen')).not.toBeDisabled();
    });

    it('shows empty state message when no fields are defined', () => {
      renderEditor([]);
      expect(
        screen.getByText(/Nog geen velden gedefinieerd/)
      ).toBeInTheDocument();
    });
  });

  describe('validation errors', () => {
    it('displays error for specific field when errors prop is provided', () => {
      renderEditor(
        [createField({ id: '', label: '' })],
        jest.fn(),
        { '0.label': 'Label is verplicht', '0.id': 'ID is verplicht' }
      );

      expect(screen.getByText('Label is verplicht')).toBeInTheDocument();
      expect(screen.getByText('ID is verplicht')).toBeInTheDocument();
    });

    it('displays options error for select field without options', () => {
      renderEditor(
        [createField({ id: 'sel', label: 'Select', type: 'select', options: [] })],
        jest.fn(),
        { '0.options': 'Selectie moet minimaal 1 optie hebben' }
      );

      expect(
        screen.getByText('Selectie moet minimaal 1 optie hebben')
      ).toBeInTheDocument();
    });
  });

  describe('select field options editor', () => {
    it('renders options input for select-type fields', () => {
      renderEditor([
        createField({ id: 'diet', label: 'Dieet', type: 'select', options: [] }),
      ]);

      expect(screen.getByPlaceholderText('Nieuwe optie...')).toBeInTheDocument();
    });

    it('adds option when add button is clicked', () => {
      const onChange = jest.fn();
      renderEditor(
        [createField({ id: 'diet', label: 'Dieet', type: 'select', options: [] })],
        onChange
      );

      const input = screen.getByPlaceholderText('Nieuwe optie...');
      fireEvent.change(input, { target: { value: 'Vegetarisch' } });
      fireEvent.click(screen.getByLabelText('Optie toevoegen'));

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({ options: ['Vegetarisch'] }),
      ]);
    });

    it('adds option when Enter is pressed', () => {
      const onChange = jest.fn();
      renderEditor(
        [createField({ id: 'diet', label: 'Dieet', type: 'select', options: [] })],
        onChange
      );

      const input = screen.getByPlaceholderText('Nieuwe optie...');
      fireEvent.change(input, { target: { value: 'Veganistisch' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({ options: ['Veganistisch'] }),
      ]);
    });

    it('displays existing options as tags', () => {
      renderEditor([
        createField({
          id: 'diet',
          label: 'Dieet',
          type: 'select',
          options: ['Geen', 'Vegetarisch'],
        }),
      ]);

      expect(screen.getByText('Geen')).toBeInTheDocument();
      expect(screen.getByText('Vegetarisch')).toBeInTheDocument();
    });

    it('removes an option when close button is clicked', () => {
      const onChange = jest.fn();
      renderEditor(
        [
          createField({
            id: 'diet',
            label: 'Dieet',
            type: 'select',
            options: ['Geen', 'Vegetarisch', 'Veganistisch'],
          }),
        ],
        onChange
      );

      const closeButtons = screen.getAllByLabelText('close');
      fireEvent.click(closeButtons[1]); // Remove 'Vegetarisch'

      expect(onChange).toHaveBeenCalledWith([
        expect.objectContaining({ options: ['Geen', 'Veganistisch'] }),
      ]);
    });
  });
});

describe('validateOrderItemFields', () => {
  it('returns error for empty label', () => {
    const errors = validateOrderItemFields([
      createField({ id: 'test', label: '' }),
    ]);
    expect(errors['0.label']).toBe('Label is verplicht');
  });

  it('returns error for empty id', () => {
    const errors = validateOrderItemFields([
      createField({ id: '', label: 'Test' }),
    ]);
    expect(errors['0.id']).toBe('ID is verplicht');
  });

  it('returns error for duplicate ids', () => {
    const errors = validateOrderItemFields([
      createField({ id: 'naam', label: 'Naam 1' }),
      createField({ id: 'naam', label: 'Naam 2' }),
    ]);
    expect(errors['1.id']).toBe('ID moet uniek zijn');
  });

  it('returns error for select field without options', () => {
    const errors = validateOrderItemFields([
      createField({ id: 'sel', label: 'Select', type: 'select', options: [] }),
    ]);
    expect(errors['0.options']).toBe('Selectie moet minimaal 1 optie hebben');
  });

  it('returns no errors for valid fields', () => {
    const errors = validateOrderItemFields([
      createField({ id: 'naam', label: 'Naam', type: 'text' }),
      createField({ id: 'email', label: 'E-mail', type: 'email' }),
      createField({
        id: 'diet',
        label: 'Dieet',
        type: 'select',
        options: ['Geen'],
      }),
    ]);
    expect(Object.keys(errors)).toHaveLength(0);
  });

  it('does not require options for non-select fields', () => {
    const errors = validateOrderItemFields([
      createField({ id: 'naam', label: 'Naam', type: 'text' }),
    ]);
    expect(errors['0.options']).toBeUndefined();
  });
});
