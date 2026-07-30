/**
 * Bug Condition Exploration Property Test — CalendarLocationLink
 *
 * **Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3**
 *
 * Property 1: Bug Condition — Location rendered as plain text instead of clickable map link
 *
 * For any event with a non-empty trimmed location string rendered in EventCalendarPage
 * or EventDetailModal, the component SHOULD render a link element with href pointing
 * to Google Maps search URL.
 *
 * EXPECTED TO FAIL on unfixed code — failure confirms the bug exists:
 * both views render location as plain <Text> with no <a> element.
 */

import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as fc from 'fast-check';

// --- Mocks ---

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
    Box: ({ children, onClick, cursor, ...rest }: any) =>
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
    Input: ({ type, value, onChange }: any) => R.createElement('input', { type, value, onChange }),
    Button: ({ children, onClick }: any) => R.createElement('button', { onClick }, children),
    Spinner: () => R.createElement('div', { 'data-testid': 'loading-spinner' }),
    Center: ({ children }: any) => R.createElement('div', null, children),
    Alert: ({ children }: any) => R.createElement('div', { role: 'alert' }, children),
    AlertIcon: () => R.createElement('span', null),
    Link: ({ children, href, isExternal, onClick, ...rest }: any) =>
      R.createElement('a', {
        href,
        onClick,
        target: isExternal ? '_blank' : undefined,
        rel: isExternal ? 'noopener noreferrer' : undefined,
      }, children),
    Icon: ({ children, viewBox, ...rest }: any) => R.createElement('svg', { viewBox }, children),
    Modal: ({ children, isOpen }: any) =>
      isOpen ? R.createElement('div', { 'data-testid': 'modal', role: 'dialog' }, children) : null,
    ModalOverlay: () => R.createElement('div', null),
    ModalContent: ({ children }: any) => R.createElement('div', null, children),
    ModalCloseButton: () => R.createElement('button', { 'data-testid': 'modal-close' }, '×'),
    ModalBody: ({ children }: any) => R.createElement('div', null, children),
    Wrap: ({ children }: any) => R.createElement('div', null, children),
    WrapItem: ({ children }: any) => R.createElement('div', null, children),
    Select: ({ children, onChange, value }: any) => R.createElement('select', { onChange, value }, children),
  };
});

// eslint-disable-next-line import/first
import EventCalendarPage from '../EventCalendarPage';
// eslint-disable-next-line import/first
import EventDetailModal from '../EventDetailModal';

// --- Generators ---

/**
 * Generate a non-empty trimmed location string.
 * Uses printable ASCII strings with at least one non-whitespace character.
 */
const nonEmptyLocationArbitrary = fc
  .string({ minLength: 1, maxLength: 50 })
  .filter((s) => s.trim().length > 0)
  .map((s) => s.trim());

// --- Helpers ---

function makeEvent(location: string) {
  return {
    event_id: 'evt-test',
    name: 'Test Event',
    slug: 'test-event',
    event_type: 'ride',
    location,
    start_date: '2099-06-15',
    end_date: '2099-06-16',
    poster_url: undefined,
    description: undefined,
    linked_regio: undefined,
  };
}

function expectedMapsUrl(location: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location.trim())}`;
}

// --- Property Tests ---

describe('Property 1: Bug Condition — Location rendered as clickable map link', () => {
  jest.setTimeout(60000);

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  afterEach(() => {
    cleanup();
  });

  /**
   * EventCalendarPage: For any non-empty trimmed location string, the calendar card
   * must render a link element (role="link") with href containing the Google Maps
   * search URL with the encoded location.
   *
   * Renders the full page with mocked fetch. Uses act() to flush async state updates.
   *
   * **Validates: Requirements 1.1, 1.3, 2.1, 2.3**
   */
  it('EventCalendarPage renders a Google Maps link for non-empty locations', async () => {
    await fc.assert(
      fc.asyncProperty(nonEmptyLocationArbitrary, async (location) => {
        cleanup();
        const event = makeEvent(location);

        // Mock fetch — resolves immediately
        global.fetch = jest.fn().mockImplementation(
          () =>
            Promise.resolve({
              ok: true,
              json: () => Promise.resolve([event]),
            })
        );

        const { container, unmount } = render(<EventCalendarPage />);

        // Wait for the clickable card to appear (proves fetch resolved + rendered)
        await screen.findByTestId('clickable-card', {}, { timeout: 5000 });

        // Find all links in the rendered output
        const links = container.querySelectorAll('a[href]');
        const mapsUrl = expectedMapsUrl(location);

        // Assert: there must be a link whose href matches the Google Maps URL
        const mapsLink = Array.from(links).find(
          (link) => link.getAttribute('href') === mapsUrl
        );

        expect(mapsLink).toBeTruthy();

        unmount();
      }),
      { numRuns: 10 }
    );
  });

  /**
   * EventDetailModal: For any non-empty trimmed location string, the modal
   * must render a link element with href containing the Google Maps search URL.
   *
   * **Validates: Requirements 1.2, 1.3, 2.2, 2.3**
   */
  it('EventDetailModal renders a Google Maps link for non-empty locations', async () => {
    await fc.assert(
      fc.asyncProperty(nonEmptyLocationArbitrary, async (location) => {
        const event = makeEvent(location);

        const { container, unmount } = render(
          <EventDetailModal
            event={event as any}
            isOpen={true}
            onClose={jest.fn()}
          />
        );

        // Find all links in the rendered output
        const links = container.querySelectorAll('a[href]');
        const mapsUrl = expectedMapsUrl(location);

        // Assert: there must be a link whose href matches the Google Maps URL
        const mapsLink = Array.from(links).find(
          (link) => link.getAttribute('href') === mapsUrl
        );

        expect(mapsLink).toBeTruthy();

        unmount();
      }),
      { numRuns: 10 }
    );
  });
});
