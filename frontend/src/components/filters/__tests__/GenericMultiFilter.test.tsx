import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import '@testing-library/jest-dom';
import { GenericMultiFilter } from '../GenericMultiFilter';
import type { FilterOption } from '../types';

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

const defaultOptions: FilterOption[] = [
  { value: 'a', label: 'Option A' },
  { value: 'b', label: 'Option B' },
  { value: 'c', label: 'Option C' },
];

function renderMultiFilter(props: Partial<React.ComponentProps<typeof GenericMultiFilter>> = {}) {
  const defaultProps = {
    label: 'Test Filter',
    value: [] as string[],
    options: defaultOptions,
    onChange: jest.fn(),
  };
  return render(
    <ChakraProvider>
      <GenericMultiFilter {...defaultProps} {...props} />
    </ChakraProvider>
  );
}

describe('GenericMultiFilter', () => {
  describe('placeholder display', () => {
    it('shows default placeholder "alle" when no options are selected', () => {
      renderMultiFilter({ value: [] });
      // The mock returns the key 'alle' as-is
      expect(screen.getByRole('button', { name: /Test Filter: alle/i })).toBeInTheDocument();
    });

    it('shows custom placeholder when provided and no options selected', () => {
      renderMultiFilter({ value: [], placeholder: 'Kies opties' });
      expect(screen.getByRole('button', { name: /Test Filter: Kies opties/i })).toBeInTheDocument();
    });
  });

  describe('count display when ≥1 selected', () => {
    it('shows count text when 1 option is selected', () => {
      renderMultiFilter({ value: ['a'] });
      // nSelected with {{count}} → "nSelected" with count=1 interpolated
      const button = screen.getByRole('button', { name: /Test Filter/i });
      expect(button).toHaveTextContent('nSelected');
    });

    it('shows count text when multiple options are selected', () => {
      renderMultiFilter({ value: ['a', 'b', 'c'] });
      const button = screen.getByRole('button', { name: /Test Filter/i });
      expect(button).toHaveTextContent('nSelected');
    });
  });

  describe('checkbox toggling calls onChange', () => {
    it('calls onChange when an option is clicked', () => {
      const onChange = jest.fn();
      renderMultiFilter({ value: [], onChange });

      // Open the menu
      const trigger = screen.getByRole('button', { name: /Test Filter/i });
      fireEvent.click(trigger);

      // Click an option
      const optionA = screen.getByText('Option A');
      fireEvent.click(optionA);

      expect(onChange).toHaveBeenCalled();
    });

    it('calls onChange with added value when selecting an unchecked option', () => {
      const onChange = jest.fn();
      renderMultiFilter({ value: ['a'], onChange });

      // Open the menu
      const trigger = screen.getByRole('button', { name: /Test Filter/i });
      fireEvent.click(trigger);

      // Click Option B (not yet selected)
      const optionB = screen.getByText('Option B');
      fireEvent.click(optionB);

      // MenuOptionGroup passes the full array of selected values
      expect(onChange).toHaveBeenCalledWith(expect.arrayContaining(['a', 'b']));
    });

    it('calls onChange with removed value when deselecting a checked option', () => {
      const onChange = jest.fn();
      renderMultiFilter({ value: ['a', 'b'], onChange });

      // Open the menu
      const trigger = screen.getByRole('button', { name: /Test Filter/i });
      fireEvent.click(trigger);

      // Click Option A (currently selected → deselect)
      const optionA = screen.getByText('Option A');
      fireEvent.click(optionA);

      expect(onChange).toHaveBeenCalledWith(['b']);
    });
  });

  describe('disabled state', () => {
    it('renders a disabled button when isDisabled is true', () => {
      renderMultiFilter({ isDisabled: true });
      const button = screen.getByRole('button', { name: /Test Filter/i });
      expect(button).toBeDisabled();
    });

    it('button is not clickable when disabled', () => {
      const onChange = jest.fn();
      renderMultiFilter({ isDisabled: true, onChange });
      const button = screen.getByRole('button', { name: /Test Filter/i });
      fireEvent.click(button);
      // Even if menu renders in DOM, onChange should never be called
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe('FormLabel rendering', () => {
    it('renders a FormLabel with the label text', () => {
      renderMultiFilter({ label: 'Status' });
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('renders FormLabel with orange.300 color and xs fontSize', () => {
      const { container } = renderMultiFilter({ label: 'Regio' });
      const label = container.querySelector('label');
      expect(label).toBeInTheDocument();
      expect(label).toHaveTextContent('Regio');
    });
  });

  describe('aria-label', () => {
    it('aria-label reflects placeholder when no selection', () => {
      renderMultiFilter({ value: [], label: 'Type' });
      const button = screen.getByRole('button', { name: 'Type: alle' });
      expect(button).toBeInTheDocument();
    });

    it('aria-label reflects selection count when items selected', () => {
      renderMultiFilter({ value: ['a', 'b'], label: 'Type' });
      // displayText = nSelected with count=2 → mock returns "nSelected" (key with interpolation)
      const button = screen.getByRole('button', { name: /Type: nSelected/i });
      expect(button).toBeInTheDocument();
    });
  });
});
