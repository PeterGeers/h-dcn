import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

const mockNavigate = jest.fn();

jest.mock('../../context/AuthProvider', () => ({
  useAuth: () => ({ isAuthenticated: true }),
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
  const R = require('react');
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

describe('Debug: EventCalendarPage location rendering', () => {
  it('renders location as a link', async () => {
    const event = {
      event_id: 'evt-test',
      name: 'Test Event',
      slug: 'test-event',
      event_type: 'ride',
      location: 'Amsterdam',
      start_date: '2099-06-15',
      end_date: '2099-06-16',
    };

    global.fetch = jest.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([event]),
      })
    );

    const { container } = render(<EventCalendarPage />);

    // Wait for the clickable card to appear (proves fetch resolved + state updated)
    const card = await screen.findByTestId('clickable-card', {}, { timeout: 5000 });
    expect(card).toBeInTheDocument();

    // Debug: print full HTML AFTER findByTestId resolves
    console.log('=== RENDERED HTML ===');
    console.log(container.innerHTML);
    console.log('=== END ===');
    console.log('Card found:', card.outerHTML.substring(0, 200));

    // Check for links
    const links = container.querySelectorAll('a[href]');
    console.log('Links found:', links.length);
    links.forEach((link) => {
      console.log('  href:', link.getAttribute('href'));
    });

    // Assert the maps link exists
    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent('Amsterdam')}`;
    const mapsLink = Array.from(links).find((link) => link.getAttribute('href') === mapsUrl);
    expect(mapsLink).toBeTruthy();
  });
});
