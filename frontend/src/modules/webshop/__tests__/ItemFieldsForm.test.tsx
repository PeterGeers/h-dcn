/**
 * ItemFieldsForm Component Tests
 *
 * Tests for field rendering per type, required validation,
 * constraint validation, and multi-item sets.
 * Validates: Requirements 8.1–8.5
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      if (params) {
        return Object.entries(params).reduce(
          (str, [k, v]) => str.replace(`{{${k}}}`, String(v)),
          key
        );
      }
      return key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI components - no out-of-scope variable references allowed
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  VStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  FormControl: ({ children, isInvalid, isRequired, ...props }: any) => (
    <div data-invalid={isInvalid} data-required={isRequired} {...props}>
      {children}
    </div>
  ),
  FormLabel: ({ children, ...props }: any) => <label {...props}>{children}</label>,
  FormErrorMessage: ({ children, ...props }: any) => (
    <span role="alert" {...props}>{children}</span>
  ),
  Input: ({ type, value, onChange, placeholder, maxLength, ...props }: any) => (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      maxLength={maxLength}
      {...props}
    />
  ),
  Select: ({ children, placeholder, value, onChange, ...props }: any) => (
    <select value={value} onChange={onChange} {...props}>
      {placeholder && <option value="">{placeholder}</option>}
      {children}
    </select>
  ),
  NumberInput: ({ value, onChange, min, max, size, ...props }: any) => (
    <input
      type="number"
      value={value}
      onChange={(e: any) => onChange(e.target.value)}
      min={min}
      max={max}
      data-testid="number-input"
    />
  ),
  NumberInputField: () => null,
  NumberInputStepper: () => null,
  NumberIncrementStepper: () => null,
  NumberDecrementStepper: () => null,
  Heading: ({ children, ...props }: any) => <h4 {...props}>{children}</h4>,
  Divider: () => <hr />,
}));

import ItemFieldsForm, {
  ItemFieldsFormProps,
  validateItemFields,
  ItemFieldError,
} from '../components/ItemFieldsForm';
import { OrderItemField, ItemFieldsEntry } from '../types/unifiedProduct.types';

// --- Test helpers ---

const textField: OrderItemField = {
  id: 'name',
  label: 'Naam deelnemer',
  type: 'text',
  required: true,
  validation: { min_length: 2, max_length: 50 },
};

const selectField: OrderItemField = {
  id: 'dietary',
  label: 'Dieetwensen',
  type: 'select',
  required: false,
  options: ['Geen', 'Vegetarisch', 'Veganistisch'],
};

const numberField: OrderItemField = {
  id: 'age',
  label: 'Leeftijd',
  type: 'number',
  required: true,
  validation: { minimum: 18, maximum: 120 },
};

const emailField: OrderItemField = {
  id: 'email',
  label: 'E-mailadres',
  type: 'email',
  required: true,
};

const dateField: OrderItemField = {
  id: 'arrival',
  label: 'Aankomstdatum',
  type: 'date',
  required: false,
};

const renderComponent = (props: Partial<ItemFieldsFormProps> = {}) => {
  const defaultProps: ItemFieldsFormProps = {
    fields: [textField, selectField],
    quantity: 1,
    values: [{ field_values: {} }],
    onChange: jest.fn(),
    ...props,
  };

  let result: ReturnType<typeof render>;
  act(() => {
    result = render(<ItemFieldsForm {...defaultProps} />);
  });
  return { ...result!, props: defaultProps };
};

describe('ItemFieldsForm', () => {
  describe('field rendering per type', () => {
    it('renders text input for text-type fields', () => {
      renderComponent({ fields: [textField] });
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('type', 'text');
    });

    it('renders select for select-type fields with options', () => {
      renderComponent({ fields: [selectField] });
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
      expect(screen.getByText('Geen')).toBeInTheDocument();
      expect(screen.getByText('Vegetarisch')).toBeInTheDocument();
      expect(screen.getByText('Veganistisch')).toBeInTheDocument();
    });

    it('renders date input for date-type fields', () => {
      renderComponent({ fields: [dateField] });
      const input = screen.getByDisplayValue('');
      expect(input).toHaveAttribute('type', 'date');
    });

    it('renders email input for email-type fields', () => {
      renderComponent({ fields: [emailField] });
      const input = screen.getByPlaceholderText('item_fields.email_placeholder');
      expect(input).toHaveAttribute('type', 'email');
    });

    it('renders field labels', () => {
      renderComponent({ fields: [textField, selectField] });
      expect(screen.getByText('Naam deelnemer')).toBeInTheDocument();
      expect(screen.getByText('Dieetwensen')).toBeInTheDocument();
    });

    it('returns null when no fields are provided', () => {
      const { container } = renderComponent({ fields: [] });
      expect(container.firstChild).toBeNull();
    });

    it('returns null when quantity is 0', () => {
      const { container } = renderComponent({ quantity: 0 });
      expect(container.firstChild).toBeNull();
    });
  });

  describe('multi-item sets', () => {
    it('renders sequential item labels for multiple items', () => {
      renderComponent({ quantity: 3 });
      expect(screen.getAllByText('item_fields.item_label')).toHaveLength(3);
    });

    it('renders independent field sets for each item', () => {
      renderComponent({
        fields: [textField],
        quantity: 2,
        values: [
          { field_values: { name: 'Jan' } },
          { field_values: { name: 'Piet' } },
        ],
      });

      const inputs = screen.getAllByRole('textbox');
      expect(inputs).toHaveLength(2);
      expect(inputs[0]).toHaveValue('Jan');
      expect(inputs[1]).toHaveValue('Piet');
    });

    it('calls onChange with updated values for specific item', () => {
      const onChange = jest.fn();
      renderComponent({
        fields: [textField],
        quantity: 2,
        values: [{ field_values: { name: 'Jan' } }, { field_values: { name: 'Piet' } }],
        onChange,
      });

      const inputs = screen.getAllByRole('textbox');
      fireEvent.change(inputs[1], { target: { value: 'Klaas' } });

      expect(onChange).toHaveBeenCalledWith([
        { field_values: { name: 'Jan' } },
        { field_values: { name: 'Klaas' } },
      ]);
    });
  });

  describe('interaction', () => {
    it('calls onChange when text field value changes', () => {
      const onChange = jest.fn();
      renderComponent({
        fields: [textField],
        quantity: 1,
        values: [{ field_values: {} }],
        onChange,
      });

      fireEvent.change(screen.getByRole('textbox'), {
        target: { value: 'Test' },
      });

      expect(onChange).toHaveBeenCalledWith([
        { field_values: { name: 'Test' } },
      ]);
    });

    it('calls onChange when select field value changes', () => {
      const onChange = jest.fn();
      renderComponent({
        fields: [selectField],
        quantity: 1,
        values: [{ field_values: {} }],
        onChange,
      });

      fireEvent.change(screen.getByRole('combobox'), {
        target: { value: 'Vegetarisch' },
      });

      expect(onChange).toHaveBeenCalledWith([
        { field_values: { dietary: 'Vegetarisch' } },
      ]);
    });
  });

  describe('error display', () => {
    it('displays error messages when validateOnSubmit is true and errors are provided', () => {
      const errors: ItemFieldError[] = [
        { itemIndex: 0, fieldId: 'name', message: 'Dit veld is verplicht' },
      ];

      renderComponent({
        fields: [textField],
        quantity: 1,
        values: [{ field_values: {} }],
        errors,
        validateOnSubmit: true,
      });

      expect(screen.getByText('Dit veld is verplicht')).toBeInTheDocument();
    });

    it('does not display errors when validateOnSubmit is false', () => {
      const errors: ItemFieldError[] = [
        { itemIndex: 0, fieldId: 'name', message: 'Dit veld is verplicht' },
      ];

      renderComponent({
        fields: [textField],
        quantity: 1,
        values: [{ field_values: {} }],
        errors,
        validateOnSubmit: false,
      });

      expect(screen.queryByText('Dit veld is verplicht')).not.toBeInTheDocument();
    });
  });
});

describe('validateItemFields', () => {
  describe('required validation', () => {
    it('returns error for empty required text field', () => {
      const errors = validateItemFields(
        [textField],
        [{ field_values: { name: '' } }],
        1
      );
      expect(errors).toHaveLength(1);
      expect(errors[0]).toMatchObject({
        itemIndex: 0,
        fieldId: 'name',
        message: 'Dit veld is verplicht',
      });
    });

    it('returns error for whitespace-only required text field', () => {
      const errors = validateItemFields(
        [textField],
        [{ field_values: { name: '   ' } }],
        1
      );
      expect(errors[0].message).toBe('Dit veld is verplicht');
    });

    it('returns no error for filled required text field', () => {
      const errors = validateItemFields(
        [textField],
        [{ field_values: { name: 'Jan' } }],
        1
      );
      expect(errors).toHaveLength(0);
    });

    it('returns no error for empty non-required field', () => {
      const errors = validateItemFields(
        [selectField],
        [{ field_values: { dietary: '' } }],
        1
      );
      expect(errors).toHaveLength(0);
    });

    it('returns error for missing required number field', () => {
      const errors = validateItemFields(
        [numberField],
        [{ field_values: {} }],
        1
      );
      expect(errors[0].message).toBe('Dit veld is verplicht');
    });
  });

  describe('constraint validation', () => {
    it('returns error when text is shorter than min_length', () => {
      const errors = validateItemFields(
        [textField],
        [{ field_values: { name: 'J' } }],
        1
      );
      expect(errors[0].message).toBe('Minimaal 2 tekens');
    });

    it('returns error when text exceeds max_length', () => {
      const longField: OrderItemField = {
        ...textField,
        validation: { max_length: 5 },
      };
      const errors = validateItemFields(
        [longField],
        [{ field_values: { name: 'TooLongText' } }],
        1
      );
      expect(errors[0].message).toBe('Maximaal 5 tekens');
    });

    it('returns error when number is below minimum', () => {
      const errors = validateItemFields(
        [numberField],
        [{ field_values: { age: '15' } }],
        1
      );
      expect(errors[0].message).toBe('Minimale waarde is 18');
    });

    it('returns error when number exceeds maximum', () => {
      const errors = validateItemFields(
        [numberField],
        [{ field_values: { age: '150' } }],
        1
      );
      expect(errors[0].message).toBe('Maximale waarde is 120');
    });

    it('returns error for invalid email format', () => {
      const errors = validateItemFields(
        [emailField],
        [{ field_values: { email: 'not-an-email' } }],
        1
      );
      expect(errors[0].message).toBe('Ongeldig e-mailadres');
    });

    it('returns no error for valid email', () => {
      const errors = validateItemFields(
        [emailField],
        [{ field_values: { email: 'test@example.nl' } }],
        1
      );
      expect(errors).toHaveLength(0);
    });

    it('returns error when select value is not in options', () => {
      const requiredSelect: OrderItemField = { ...selectField, required: true };
      const errors = validateItemFields(
        [requiredSelect],
        [{ field_values: { dietary: 'Halal' } }],
        1
      );
      expect(errors[0].message).toBe('Selecteer een geldige optie');
    });

    it('returns error when pattern does not match', () => {
      const patternField: OrderItemField = {
        ...textField,
        validation: { pattern: '^[A-Z]' },
      };
      const errors = validateItemFields(
        [patternField],
        [{ field_values: { name: 'lowercase' } }],
        1
      );
      expect(errors[0].message).toBe('Waarde voldoet niet aan het vereiste formaat');
    });
  });

  describe('multi-item validation', () => {
    it('validates all items independently', () => {
      const errors = validateItemFields(
        [textField],
        [
          { field_values: { name: '' } },
          { field_values: { name: 'Valid' } },
          { field_values: { name: '' } },
        ],
        3
      );
      expect(errors).toHaveLength(2);
      expect(errors[0].itemIndex).toBe(0);
      expect(errors[1].itemIndex).toBe(2);
    });

    it('returns errors with correct item indices', () => {
      const errors = validateItemFields(
        [numberField],
        [
          { field_values: { age: '25' } },
          { field_values: { age: '15' } },
        ],
        2
      );
      expect(errors).toHaveLength(1);
      expect(errors[0].itemIndex).toBe(1);
      expect(errors[0].fieldId).toBe('age');
    });
  });
});
