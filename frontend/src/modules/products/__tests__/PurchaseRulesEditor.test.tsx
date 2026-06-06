import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import '@testing-library/jest-dom';
import PurchaseRulesEditor from '../components/PurchaseRulesEditor';
import { PurchaseRules } from '../../webshop/types/unifiedProduct.types';

const renderEditor = (
  value: PurchaseRules = {},
  onChange = jest.fn(),
  errors?: Partial<Record<string, string>>
) => {
  return render(
    <ChakraProvider>
      <PurchaseRulesEditor value={value} onChange={onChange} errors={errors} />
    </ChakraProvider>
  );
};

describe('PurchaseRulesEditor', () => {
  it('renders all form labels', () => {
    renderEditor();
    expect(screen.getByText('Max per bestelling')).toBeInTheDocument();
    expect(screen.getByText('Max per lid')).toBeInTheDocument();
    expect(screen.getByText('Max per club')).toBeInTheDocument();
    expect(screen.getByText('Min per club')).toBeInTheDocument();
    expect(screen.getByText('Lidmaatschap vereist')).toBeInTheDocument();
    expect(screen.getByText('Bestelmodus')).toBeInTheDocument();
  });

  it('displays current values in number fields', () => {
    renderEditor({
      max_per_order: 5,
      max_per_member: 10,
      max_per_club: 50,
      min_per_club: 3,
    });
    expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    expect(screen.getByDisplayValue('10')).toBeInTheDocument();
    expect(screen.getByDisplayValue('50')).toBeInTheDocument();
    expect(screen.getByDisplayValue('3')).toBeInTheDocument();
  });

  it('calls onChange when max_per_order is modified', () => {
    const onChange = jest.fn();
    renderEditor({ max_per_order: 5 }, onChange);
    const input = screen.getByDisplayValue('5');
    fireEvent.change(input, { target: { value: '10' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ max_per_order: 10 }));
  });

  it('calls onChange with undefined when number field is cleared', () => {
    const onChange = jest.fn();
    renderEditor({ max_per_order: 5 }, onChange);
    const input = screen.getByDisplayValue('5');
    fireEvent.change(input, { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ max_per_order: undefined }));
  });

  it('shows requires_membership switch as checked when true', () => {
    renderEditor({ requires_membership: true });
    const switchInput = screen.getByRole('checkbox');
    expect(switchInput).toBeChecked();
  });

  it('calls onChange when requires_membership is toggled', () => {
    const onChange = jest.fn();
    renderEditor({ requires_membership: false }, onChange);
    const switchInput = screen.getByRole('checkbox');
    fireEvent.click(switchInput);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ requires_membership: true }));
  });

  it('displays order_mode select with correct value', () => {
    renderEditor({ order_mode: 'persistent' });
    const select = screen.getByRole('combobox');
    expect(select).toHaveValue('persistent');
  });

  it('calls onChange when order_mode is changed', () => {
    const onChange = jest.fn();
    renderEditor({ order_mode: 'single' }, onChange);
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'persistent' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ order_mode: 'persistent' }));
  });

  it('shows min_per_club > max_per_club validation error', () => {
    renderEditor({ min_per_club: 20, max_per_club: 10 });
    expect(
      screen.getByText('Minimum per club kan niet hoger zijn dan maximum per club')
    ).toBeInTheDocument();
  });

  it('does not show min/max error when min_per_club ≤ max_per_club', () => {
    renderEditor({ min_per_club: 5, max_per_club: 10 });
    expect(
      screen.queryByText('Minimum per club kan niet hoger zijn dan maximum per club')
    ).not.toBeInTheDocument();
  });

  it('does not show min/max error when only one is set', () => {
    renderEditor({ min_per_club: 5 });
    expect(
      screen.queryByText('Minimum per club kan niet hoger zijn dan maximum per club')
    ).not.toBeInTheDocument();
  });

  it('displays external errors from the errors prop', () => {
    renderEditor({}, jest.fn(), { max_per_order: 'Waarde is verplicht' });
    expect(screen.getByText('Waarde is verplicht')).toBeInTheDocument();
  });

  it('defaults order_mode to single when not set', () => {
    renderEditor({});
    const select = screen.getByRole('combobox');
    expect(select).toHaveValue('single');
  });
});
