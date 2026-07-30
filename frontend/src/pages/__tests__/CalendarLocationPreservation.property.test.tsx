/**
 * Property-based preservation tests for empty-location fallback behavior.
 *
 * These tests encode the CURRENT baseline behavior on UNFIXED code:
 * - EventCalendarPage with null/empty location renders t('calendar.card.noLocation') fallback
 * - EventDetailModal with null/empty location renders "—" fallback
 * - No link (LocationMapLink) is present for empty/null/whitespace locations
 * - Card click still opens the modal
 *
 * Uses fast-check to generate empty-ish location strings.
 *
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
 */

import React from 'react'; // eslint-disable-line @typescript-eslint/no-unused-vars
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as fc from 'fast-check';

// Increase timeout for property-based tests
jest.setTimeout(60000);

// --- Mocks (same pattern as CalendarLocationLink.property.test.tsx) ---

const mockNavigate = jest.fn();
const mockUseAuth = jest.fn().mockReturnValue({ isAuthenticated: true });

jest.mock('../../context/AuthProvider', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

jest.mock('react-i18next', () => {
  const stableT = (key: string, fallback?: any) => {
    if (typeof fallback === 'string') return fallback;
    if (typeof fallback === 'object' && fallback?.location) return `Open ${fallback.location} in Maps`;
    return key;
  };
  const stableI18n = { language: 'en', changeLanguage: () => {} };
  const stableResult = { t: stableT, i18n: stableI18n };
  return {
    useTranslation: () => stableResult,
  };
});

jest.mock('../../config/eventFields/eventTypes', () => ({
  EVENT_TYPES: ['ride', 'meeting', 'social'],
  EVENT_REGIOS: ['Noord', 'Zuid'],
}));

jest.mock('../../components/filters/FilterPanel', () => ({
  FilterPanel: () => null,
}));

jest.mock('../../config/api', () => ({
  API_CONFIG: { BASE_URL: 'http://localhost' },
}));

jest.mock('@chakra-ui/react', () => {
  const R = require('react'); // eslint-disable-line @typescript-eslint/no-var-requires
  return {
    Box: ({ children, onClick, cursor }: any) =>
      R.createElement('div', { onClick, 'data-testid': cursor === 'pointer' ? 'clickable-card' : undefined }, children),
    Container: ({ children }: any) => R.createElement('div', null, children),
    Heading: ({ children, as }: any) => R.createElement(as || 'h1', null, children),
    Text: ({ children }: any) => R.createElement('span', null, children),
    Image: ({ alt, src }: any) => R.createElement('img', { alt, src }),
    SimpleGrid: ({ children }: any) => R.createElement('div', { 'data-testid': 'event-grid' }, children),
    VStack: ({ children }: any) => R.createElement('div', null, children),
    HStack: ({ children }: any) => R.createElement('div', null, children),
    FormControl: ({ children }: any) => R.createElement('div', null, children),
    FormLabel: ({ children }: any) => R.createElement('label', null, children),
    Select: ({ children, onChange, value }: any) => R.createElement('select', { onChange, value }, children),
    Input: ({ type, value, onChange }: any) => R.createElement('input', { type, value, onChange }),
    Button: ({ children, onClick }: any) => R.createElement('button', { onClick }, children),
    Spinner: () => R.createElement('div', { 'data-testid': 'loading-spinner' }),
    Center: ({ children }: any) => R.createElement('div', null, children),
    Alert: ({ children }: any) => R.createElement('div', { role: 'alert' }, children),
    AlertIcon: () => R.createElement('span', null),
    Icon: ({ viewBox }: any) => R.createElement('svg', { viewBox }),
    Link: ({ children, href, onClick, isExternal }: any) =>
      R.createElement('a', { href, onClick, role: 'link', target: isExternal ? '_blank' : undefined }, children),
    Modal: ({ children, isOpen }: any) =>
      isOpen ? R.createElement('div', { 'data-testid': 'event-detail-modal', role: 'dialog' }, children) : null,
    ModalOverlay: () => R.createElement('div', null),
    ModalContent: ({ children }: any) => R.createElement('div', null, children),
    ModalCloseButton: () => R.createElement('button', { 'data-testid': 'modal-close' }, '\u00d7'),
    ModalBody: ({ children }: any) => R.createElement('div', null, children),
    Wrap: ({ children }: any) => R.createElement('div', null, children),
    WrapItem: ({ children }: any) => R.createElement('div', null, children),
  };
});

// eslint-disable-next-line import/first
import EventCalendarPage from '../EventCalendarPage';
// eslint-disable-next-line import/first
import EventDetailModal from '../EventDetailModal';

// --- Helpers ---

function makeEvent(location: string | null | undefined) {
  return {
    event_id: 'evt-preserve-1',
    name: 'Preservation Test Event',
    slug: 'preserve-test',
    event_type: 'ride',
    location: location as string,
    start_date: '2099-06-15',
    end_date: '2099-06-16',
    poster_url: undefined,
    description: undefined,
    linked_regio: undefined,
  };
}

/**
 * Helper to render EventCalendarPage with a mocked fetch that returns the given event.
 * Uses findByTestId to wait for the card to appear after async state updates.
 */
async function renderCalendarWithEvent(event: ReturnType<typeof makeEvent>) {
  global.fetch = jest.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve([event]),
    })
  );

  const result = render(<EventCalendarPage />);

  // Wait for the clickable card to appear (proves fetch resolved + rendered)
  await screen.findByTestId('clickable-card', {}, { timeout: 5000 });

  return result;
}

// --- Generators ---

/**
 * Generates falsy location values: null, undefined, "".
 * On UNFIXED code: `event.location || fallback` evaluates to `fallback`.
 */
const falsyLocationArbitrary = fc.oneof(
  fc.constant(null as string | null),
  fc.constant(undefined as unknown as string | null),
  fc.constant(''),
);

/**
 * Generates whitespace-only location strings (non-empty but only whitespace).
 * On UNFIXED code: "   " is truthy, so `"   " || fallback` renders whitespace.
 * Key preservation assertion: no link (LocationMapLink) is rendered.
 */
const whitespaceLocationArbitrary = fc.stringOf(
  fc.constantFrom(' ', '\t', '\n'),
  { minLength: 1, maxLength: 10 },
);

/**
 * Combined generator for all empty-ish locations.
 */
const emptyishLocationArbitrary = fc.oneof(
  falsyLocationArbitrary,
  whitespaceLocationArbitrary,
);

// --- Tests ---

describe('Property 2: Preservation — Empty location fallback text unchanged', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  afterEach(() => {
    cleanup();
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * EventCalendarPage with falsy location (null, undefined, "") renders
   * the t('calendar.card.noLocation') fallback text in the card.
   */
  it('EventCalendarPage renders fallback text for falsy locations', async () => {
    await fc.assert(
      fc.asyncProperty(falsyLocationArbitrary, async (location) => {
        cleanup();
        const event = makeEvent(location);
        const { unmount } = await renderCalendarWithEvent(event);

        // The fallback text key should be present
        expect(screen.getByText('calendar.card.noLocation')).toBeInTheDocument();

        // No link role should exist (no LocationMapLink rendered)
        const links = screen.queryAllByRole('link');
        expect(links.length).toBe(0);

        unmount();
      }),
      { numRuns: 10 },
    );
  });

  /**
   * **Validates: Requirements 3.2**
   *
   * EventDetailModal with falsy location (null, undefined, "") renders "—" fallback.
   * Directly renders EventDetailModal for isolation.
   */
  it('EventDetailModal renders "\u2014" fallback for falsy locations', async () => {
    await fc.assert(
      fc.asyncProperty(falsyLocationArbitrary, async (location) => {
        cleanup();
        const event = makeEvent(location);

        const { unmount } = render(
          <EventDetailModal
            event={event as any}
            isOpen={true}
            onClose={jest.fn()}
          />
        );

        // The modal should be open
        expect(screen.getByTestId('event-detail-modal')).toBeInTheDocument();

        // The "—" em-dash fallback should be present
        expect(screen.getByText('\u2014')).toBeInTheDocument();

        // No link role should exist
        const links = screen.queryAllByRole('link');
        expect(links.length).toBe(0);

        unmount();
      }),
      { numRuns: 10 },
    );
  });

  /**
   * **Validates: Requirements 3.1, 3.2**
   *
   * For all empty-ish locations (including whitespace-only), no LocationMapLink
   * (link role) is rendered in the card view.
   */
  it('no LocationMapLink (link role) rendered for any empty-ish location (card view)', async () => {
    await fc.assert(
      fc.asyncProperty(emptyishLocationArbitrary, async (location) => {
        cleanup();
        const event = makeEvent(location);
        const { unmount } = await renderCalendarWithEvent(event);

        // No link role should exist (LocationMapLink would render an <a> with role="link")
        const links = screen.queryAllByRole('link');
        expect(links.length).toBe(0);

        unmount();
      }),
      { numRuns: 20 },
    );
  });

  /**
   * **Validates: Requirements 3.2**
   *
   * For all empty-ish locations, no LocationMapLink is rendered in the modal.
   */
  it('no LocationMapLink (link role) rendered for any empty-ish location (modal view)', async () => {
    await fc.assert(
      fc.asyncProperty(emptyishLocationArbitrary, async (location) => {
        cleanup();
        const event = makeEvent(location);

        const { unmount } = render(
          <EventDetailModal
            event={event as any}
            isOpen={true}
            onClose={jest.fn()}
          />
        );

        // Modal should be present
        expect(screen.getByTestId('event-detail-modal')).toBeInTheDocument();

        // No link role should exist
        const links = screen.queryAllByRole('link');
        expect(links.length).toBe(0);

        unmount();
      }),
      { numRuns: 20 },
    );
  });

  /**
   * **Validates: Requirements 3.3**
   *
   * Card click still opens EventDetailModal for empty-location events.
   * setSelectedEvent is triggered and modal renders.
   */
  it('card click still opens EventDetailModal for empty-ish location events', async () => {
    await fc.assert(
      fc.asyncProperty(emptyishLocationArbitrary, async (location) => {
        cleanup();
        const event = makeEvent(location);
        const { unmount } = await renderCalendarWithEvent(event);

        // Click the card
        const card = screen.getByTestId('clickable-card');
        fireEvent.click(card);

        // Modal should open
        expect(screen.getByTestId('event-detail-modal')).toBeInTheDocument();

        // The event name should appear in the modal (appears at least twice: card + modal)
        const eventNames = screen.getAllByText('Preservation Test Event');
        expect(eventNames.length).toBeGreaterThanOrEqual(2);

        unmount();
      }),
      { numRuns: 10 },
    );
  });

  /**
   * **Validates: Requirements 3.1, 3.2**
   *
   * Specific observation: null location renders correct fallback in both views.
   */
  it('observation: null location \u2014 card shows fallback, modal shows "\u2014"', async () => {
    const { unmount } = await renderCalendarWithEvent(makeEvent(null));

    expect(screen.getByText('calendar.card.noLocation')).toBeInTheDocument();
    expect(screen.queryAllByRole('link').length).toBe(0);

    // Click card to open modal
    const card = screen.getByTestId('clickable-card');
    fireEvent.click(card);

    expect(screen.getByTestId('event-detail-modal')).toBeInTheDocument();
    expect(screen.getByText('\u2014')).toBeInTheDocument();
    expect(screen.queryAllByRole('link').length).toBe(0);

    unmount();
  });

  /**
   * **Validates: Requirements 3.1, 3.2**
   *
   * Specific observation: empty string location renders correct fallback in both views.
   */
  it('observation: empty string location \u2014 card shows fallback, modal shows "\u2014"', async () => {
    const { unmount } = await renderCalendarWithEvent(makeEvent(''));

    expect(screen.getByText('calendar.card.noLocation')).toBeInTheDocument();
    expect(screen.queryAllByRole('link').length).toBe(0);

    // Click card to open modal
    const card = screen.getByTestId('clickable-card');
    fireEvent.click(card);

    expect(screen.getByTestId('event-detail-modal')).toBeInTheDocument();
    expect(screen.getByText('\u2014')).toBeInTheDocument();
    expect(screen.queryAllByRole('link').length).toBe(0);

    unmount();
  });

  /**
   * **Validates: Requirements 3.1, 3.2**
   *
   * Specific observation: whitespace-only location ("   ") does not render as a link.
   * On unfixed code, whitespace-only is truthy so it renders the raw whitespace,
   * but crucially no LocationMapLink (link role) is present.
   */
  it('observation: whitespace-only location \u2014 no link rendered in either view', async () => {
    const { unmount } = await renderCalendarWithEvent(makeEvent('   '));

    // No link should be present
    expect(screen.queryAllByRole('link').length).toBe(0);

    // Click card to open modal
    const card = screen.getByTestId('clickable-card');
    fireEvent.click(card);

    expect(screen.getByTestId('event-detail-modal')).toBeInTheDocument();
    expect(screen.queryAllByRole('link').length).toBe(0);

    unmount();
  });
});
