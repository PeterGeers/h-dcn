import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  VStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  HStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Input: ({ placeholder, value, onChange, maxLength, size, ...props }: any) => (
    <input placeholder={placeholder} value={value} onChange={onChange} maxLength={maxLength} {...props} />
  ),
  Button: ({ children, onClick, isDisabled, leftIcon, ...props }: any) => (
    <button onClick={onClick} disabled={isDisabled} {...props}>{children}</button>
  ),
  IconButton: ({ 'aria-label': ariaLabel, onClick, isDisabled, ...props }: any) => (
    <button aria-label={ariaLabel} onClick={onClick} disabled={isDisabled} {...props} />
  ),
  Text: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  FormControl: ({ children, isInvalid, ...props }: any) => (
    <div data-invalid={isInvalid} {...props}>{children}</div>
  ),
  FormErrorMessage: ({ children, ...props }: any) => <span role="alert" {...props}>{children}</span>,
  Tag: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  TagLabel: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  TagCloseButton: ({ onClick, ...props }: any) => (
    <button aria-label="close" onClick={onClick} {...props} />
  ),
  Badge: ({ children, ...props }: any) => <span {...props}>{children}</span>,
}));

jest.mock('@chakra-ui/icons', () => ({
  AddIcon: () => <span data-testid="add-icon" />,
  DeleteIcon: () => <span data-testid="delete-icon" />,
  ArrowUpIcon: () => <span data-testid="arrow-up-icon" />,
  ArrowDownIcon: () => <span data-testid="arrow-down-icon" />,
}));

import VariantSchemaEditor from '../components/VariantSchemaEditor';
import { VariantSchema } from '../../webshop/types/unifiedProduct.types';

const renderEditor = (
  value: VariantSchema = {},
  onChange = jest.fn(),
  errors?: Record<string, string>
) => {
  return render(
    <VariantSchemaEditor value={value} onChange={onChange} errors={errors} />
  );
};

describe('VariantSchemaEditor', () => {
  it('renders add axis button', () => {
    renderEditor();
    expect(screen.getByText('As toevoegen')).toBeInTheDocument();
  });

  it('calls onChange when adding a new axis', () => {
    const onChange = jest.fn();
    renderEditor({}, onChange);
    fireEvent.click(screen.getByText('As toevoegen'));
    expect(onChange).toHaveBeenCalledWith({ '': [] });
  });

  it('renders existing axes with their values', () => {
    renderEditor({ Maat: ['S', 'M', 'L'] });
    expect(screen.getByDisplayValue('Maat')).toBeInTheDocument();
    expect(screen.getByText('S')).toBeInTheDocument();
    expect(screen.getByText('M')).toBeInTheDocument();
    expect(screen.getByText('L')).toBeInTheDocument();
  });

  it('calls onChange when renaming an axis', () => {
    const onChange = jest.fn();
    renderEditor({ Maat: ['S', 'M'] }, onChange);
    fireEvent.change(screen.getByDisplayValue('Maat'), { target: { value: 'Kleur' } });
    expect(onChange).toHaveBeenCalledWith({ Kleur: ['S', 'M'] });
  });

  it('calls onChange when removing an axis', () => {
    const onChange = jest.fn();
    renderEditor({ Maat: ['S'], Kleur: ['Rood'] }, onChange);
    const deleteButtons = screen.getAllByLabelText('As verwijderen');
    fireEvent.click(deleteButtons[0]);
    expect(onChange).toHaveBeenCalledWith({ Kleur: ['Rood'] });
  });

  it('disables add axis button when 5 axes exist', () => {
    const schema: VariantSchema = {
      As1: ['a'], As2: ['b'], As3: ['c'], As4: ['d'], As5: ['e'],
    };
    renderEditor(schema);
    expect(screen.getByText('As toevoegen')).toBeDisabled();
    expect(screen.getByText('Maximaal 5 assen')).toBeInTheDocument();
  });

  it('displays error badge when combinations exceed 100', () => {
    // 5 * 5 * 5 = 125 > 100
    const schema: VariantSchema = {
      A: ['1', '2', '3', '4', '5'],
      B: ['1', '2', '3', '4', '5'],
      C: ['1', '2', '3', '4', '5'],
    };
    renderEditor(schema);
    expect(screen.getByText(/Te veel combinaties: 125/)).toBeInTheDocument();
  });

  it('displays total combinations count when within limit', () => {
    const schema: VariantSchema = { Maat: ['S', 'M', 'L'], Kleur: ['Rood', 'Blauw'] };
    renderEditor(schema);
    expect(screen.getByText('Totaal combinaties: 6')).toBeInTheDocument();
  });

  it('calls onChange when adding a value to an axis', () => {
    const onChange = jest.fn();
    renderEditor({ Maat: ['S'] }, onChange);
    const input = screen.getByPlaceholderText('Waarde toevoegen');
    fireEvent.change(input, { target: { value: 'M' } });
    fireEvent.click(screen.getByText('Toevoegen'));
    expect(onChange).toHaveBeenCalledWith({ Maat: ['S', 'M'] });
  });

  it('calls onChange when removing a value from an axis', () => {
    const onChange = jest.fn();
    renderEditor({ Maat: ['S', 'M', 'L'] }, onChange);
    // Find the close button inside the 'M' tag
    const closeButtons = screen.getAllByLabelText('close');
    fireEvent.click(closeButtons[1]); // Second value = 'M'
    expect(onChange).toHaveBeenCalledWith({ Maat: ['S', 'L'] });
  });

  it('supports reordering axes down', () => {
    const onChange = jest.fn();
    renderEditor({ Maat: ['S'], Kleur: ['Rood'] }, onChange);
    const downButtons = screen.getAllByLabelText('As omlaag');
    fireEvent.click(downButtons[0]);
    expect(onChange).toHaveBeenCalledWith({ Kleur: ['Rood'], Maat: ['S'] });
  });

  it('supports reordering axes up', () => {
    const onChange = jest.fn();
    renderEditor({ Maat: ['S'], Kleur: ['Rood'] }, onChange);
    const upButtons = screen.getAllByLabelText('As omhoog');
    fireEvent.click(upButtons[1]);
    expect(onChange).toHaveBeenCalledWith({ Kleur: ['Rood'], Maat: ['S'] });
  });

  it('supports adding a value via Enter key', () => {
    const onChange = jest.fn();
    renderEditor({ Maat: ['S'] }, onChange);
    const input = screen.getByPlaceholderText('Waarde toevoegen');
    fireEvent.change(input, { target: { value: 'XL' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onChange).toHaveBeenCalledWith({ Maat: ['S', 'XL'] });
  });
});
