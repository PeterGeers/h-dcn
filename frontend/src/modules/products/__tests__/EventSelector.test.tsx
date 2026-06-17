import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import '@testing-library/jest-dom';
import EventSelector, {
  filterEvents,
  getSelectedEventTags,
} from '../components/EventSelector';
import { Event as HDCNEvent } from '../../../types';

// --- Test data ---

const mockEvents: HDCNEvent[] = [
  { event_id: 'evt-1', title: 'Zomerrit 2025' },
  { event_id: 'evt-2', title: 'Wintermeeting' },
  { event_id: 'evt-3', title: 'Nationale Dag' },
];

const renderSelector = (
  props: Partial<React.ComponentProps<typeof EventSelector>> = {}
) => {
  const defaultProps = {
    events: mockEvents,
    selectedIds: [] as string[],
    onChange: jest.fn(),
  };
  return render(
    <ChakraProvider>
      <EventSelector {...defaultProps} {...props} />
    </ChakraProvider>
  );
};

// --- Unit Tests ---

describe('EventSelector', () => {
  describe('checkbox rendering', () => {
    it('renders a checkbox for each event plus the Webshop option', () => {
      renderSelector();
      // Webshop (algemeen) is always first
      expect(screen.getByText('Webshop (algemeen)')).toBeInTheDocument();
      // Each event renders a checkbox with its title
      expect(screen.getByText('Zomerrit 2025')).toBeInTheDocument();
      expect(screen.getByText('Wintermeeting')).toBeInTheDocument();
      expect(screen.getByText('Nationale Dag')).toBeInTheDocument();
      // Total checkboxes: 1 (webshop) + 3 (events) = 4
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes).toHaveLength(4);
    });

    it('renders selected events as checked', () => {
      renderSelector({ selectedIds: ['evt-1', 'evt-webshop'] });
      const checkboxes = screen.getAllByRole('checkbox');
      // Webshop checkbox (first) should be checked
      expect(checkboxes[0]).toBeChecked();
      // evt-1 (Zomerrit 2025) should be checked
      expect(checkboxes[1]).toBeChecked();
      // evt-2, evt-3 should not be checked
      expect(checkboxes[2]).not.toBeChecked();
      expect(checkboxes[3]).not.toBeChecked();
    });

    it('renders empty state text when search finds no events', () => {
      renderSelector();
      const input = screen.getByPlaceholderText('Zoek evenement...');
      fireEvent.change(input, { target: { value: 'xyz-nomatch' } });
      expect(screen.getByText('Geen evenementen gevonden')).toBeInTheDocument();
    });
  });

  describe('search filtering', () => {
    it('filters events by search text (case-insensitive)', () => {
      renderSelector();
      const input = screen.getByPlaceholderText('Zoek evenement...');
      fireEvent.change(input, { target: { value: 'winter' } });
      // Only Wintermeeting should remain (plus Webshop always shows)
      expect(screen.getByText('Wintermeeting')).toBeInTheDocument();
      expect(screen.queryByText('Zomerrit 2025')).not.toBeInTheDocument();
      expect(screen.queryByText('Nationale Dag')).not.toBeInTheDocument();
      // Webshop is always visible regardless of search
      expect(screen.getByText('Webshop (algemeen)')).toBeInTheDocument();
    });
  });

  describe('onChange behavior', () => {
    it('calls onChange with added event id when checkbox is checked', () => {
      const onChange = jest.fn();
      renderSelector({ onChange, selectedIds: [] });
      // Click the first event checkbox (after Webshop)
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[1]); // evt-1
      expect(onChange).toHaveBeenCalledWith(['evt-1']);
    });

    it('calls onChange without the event id when checkbox is unchecked', () => {
      const onChange = jest.fn();
      renderSelector({ onChange, selectedIds: ['evt-1', 'evt-2'] });
      // Uncheck evt-1
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[1]); // evt-1
      expect(onChange).toHaveBeenCalledWith(['evt-2']);
    });

    it('calls onChange when Webshop checkbox is toggled', () => {
      const onChange = jest.fn();
      renderSelector({ onChange, selectedIds: [] });
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]); // Webshop
      expect(onChange).toHaveBeenCalledWith(['evt-webshop']);
    });
  });

  describe('loading state', () => {
    it('shows loading spinner when isLoading is true', () => {
      renderSelector({ isLoading: true });
      expect(screen.getByText('Events laden...')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText('Zoek evenement...')).not.toBeInTheDocument();
    });
  });
});

// --- Collapsed state display utility tests ---

describe('getSelectedEventTags', () => {
  it('returns tags for selected events that exist in events list', () => {
    const tags = getSelectedEventTags(mockEvents, ['evt-1', 'evt-3']);
    expect(tags).toEqual([
      { id: 'evt-1', label: 'Zomerrit 2025' },
      { id: 'evt-3', label: 'Nationale Dag' },
    ]);
  });

  it('returns empty array when no events are selected (placeholder case)', () => {
    const tags = getSelectedEventTags(mockEvents, []);
    expect(tags).toEqual([]);
  });

  it('omits tags for selected ids that do not exist in events array', () => {
    const tags = getSelectedEventTags(mockEvents, ['evt-1', 'evt-unknown']);
    expect(tags).toEqual([{ id: 'evt-1', label: 'Zomerrit 2025' }]);
  });

  it('uses naam field when title is not available', () => {
    const eventsWithNaam: HDCNEvent[] = [
      { event_id: 'evt-a', naam: 'Herfstrit' },
    ];
    const tags = getSelectedEventTags(eventsWithNaam, ['evt-a']);
    expect(tags).toEqual([{ id: 'evt-a', label: 'Herfstrit' }]);
  });
});

// --- filterEvents utility tests ---

describe('filterEvents', () => {
  it('returns all events when search is empty', () => {
    const result = filterEvents(mockEvents, '');
    expect(result).toEqual(mockEvents);
  });

  it('returns all events when search is whitespace only', () => {
    const result = filterEvents(mockEvents, '   ');
    expect(result).toEqual(mockEvents);
  });

  it('filters by case-insensitive substring match on title', () => {
    const result = filterEvents(mockEvents, 'zomer');
    expect(result).toEqual([{ event_id: 'evt-1', title: 'Zomerrit 2025' }]);
  });

  it('returns empty array when no events match', () => {
    const result = filterEvents(mockEvents, 'xyz-nomatch');
    expect(result).toEqual([]);
  });
});
