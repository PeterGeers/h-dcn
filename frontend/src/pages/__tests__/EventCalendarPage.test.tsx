/**
 * EventCalendarPage unit tests — auth-aware behavior.
 *
 * Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
 */

import React from 'react';
import { render, screen, act, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';

// --- Mock data ---

const mockEvents = [
  {
    event_id: 'evt-1',
    name: 'Test Event',
    slug: 'test-event',
    event_type: 'ride',
    location: 'Amsterdam',
    start_date: '2099-06-15',
    end_date: '2099-06-16',
    poster_url: 'https://example.com/poster.jpg',
    description: 'A test event',
    linked_regio: 'Noord',
  },
];

// --- Mocks ---

const mockNavigate = jest.fn();
const mockUseAuth = jest.fn().mockReturnValue({ isAuthenticated: true });

jest.mock('../../context/AuthProvider', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

const stableT = (key: string) => key;

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: stableT,
  }),
}));

jest.mock('@chakra-ui/react', () => {
  const R = require('react'); // eslint-disable-line @typescript-eslint/no-var-requires
  return {
    Box: ({ children, onClick, cursor }: any) =>
      R.createElement('div', {
        onClick,
        ...(cursor === 'pointer' ? { 'data-testid': 'clickable-card' } : {}),
      }, children),
    Container: ({ children }: any) => R.createElement('div', null, children),
    Heading: ({ children }: any) => R.createElement('h1', null, children),
    Text: ({ children }: any) => R.createElement('span', null, children),
    Image: ({ alt, src }: any) => R.createElement('img', { alt, src }),
    SimpleGrid: ({ children }: any) => R.createElement('div', { 'data-testid': 'event-grid' }, children),
    VStack: ({ children }: any) => R.createElement('div', null, children),
    HStack: ({ children }: any) => R.createElement('div', null, children),
    Wrap: ({ children }: any) => R.createElement('div', null, children),
    WrapItem: ({ children }: any) => R.createElement('div', null, children),
    Select: ({ children, onChange, value }: any) => R.createElement('select', { onChange, value }, children),
    Input: ({ type, value, onChange }: any) => R.createElement('input', { type, value, onChange }),
    Button: ({ children, onClick }: any) => R.createElement('button', { onClick }, children),
    Spinner: () => R.createElement('div', { 'data-testid': 'loading-spinner' }),
    Center: ({ children }: any) => R.createElement('div', null, children),
    Alert: ({ children }: any) => R.createElement('div', { 'data-testid': 'error-alert', role: 'alert' }, children),
    AlertIcon: () => R.createElement('span', null),
  };
});

jest.mock('../../config/eventFields/eventTypes', () => ({
  EVENT_TYPES: ['ride', 'meeting', 'social'],
  EVENT_REGIOS: ['Noord', 'Zuid', 'Oost', 'West'],
}));

// eslint-disable-next-line import/first
import EventCalendarPage from '../EventCalendarPage';

// --- Test suite ---

describe('EventCalendarPage', () => {
  let mockWindowOpen: jest.Mock;
  const origOpen = window.open;
  const origConsoleError = console.error;

  beforeEach(() => {
    // Suppress expected error logs
    console.error = () => {};
    mockNavigate.mockClear();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    mockWindowOpen = jest.fn();
    window.open = mockWindowOpen;

    // Mock fetch with successful response
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockEvents),
      })
    ) as jest.Mock;
  });

  afterEach(() => {
    cleanup();
    window.open = origOpen;
    console.error = origConsoleError;
    jest.useRealTimers();
  });

  // --- Auth-based click behavior ---

  it('authenticated user click calls navigate("/events/{event_id}/booking") (Req 2.3)', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    render(<EventCalendarPage />);

    const card = await screen.findByTestId('clickable-card', {}, { timeout: 5000 });
    fireEvent.click(card);

    expect(mockNavigate).toHaveBeenCalledWith('/events/evt-1/booking');
    expect(mockWindowOpen).not.toHaveBeenCalled();
  });

  it('unauthenticated user click calls window.open("/events/{slug}/info", "_blank") (Req 2.4)', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
    render(<EventCalendarPage />);

    const card = await screen.findByTestId('clickable-card', {}, { timeout: 5000 });
    fireEvent.click(card);

    expect(mockWindowOpen).toHaveBeenCalledWith('/events/test-event/info', '_blank');
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // --- API endpoint ---

  it('uses /events-public endpoint regardless of auth state (Req 2.2)', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    render(<EventCalendarPage />);

    await screen.findByTestId('clickable-card', {}, { timeout: 5000 });
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/events-public');

    cleanup();
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(mockEvents) })
    ) as jest.Mock;
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
    render(<EventCalendarPage />);

    await screen.findByTestId('clickable-card', {}, { timeout: 5000 });
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/events-public');
  });

  // --- Error handling ---

  it('fetch failure shows error message and retry button (Req 2.5)', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('Network error'))) as jest.Mock;
    render(<EventCalendarPage />);

    const alert = await screen.findByTestId('error-alert', {}, { timeout: 5000 });
    expect(alert).toHaveTextContent('calendar.error');
    expect(screen.getByText('calendar.retry')).toBeInTheDocument();
  });

  it('retry button re-triggers fetch (Req 2.5)', async () => {
    let callCount = 0;
    global.fetch = jest.fn(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.reject(new Error('Network error'));
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockEvents),
      });
    }) as jest.Mock;

    render(<EventCalendarPage />);

    const retryBtn = await screen.findByText('calendar.retry', {}, { timeout: 5000 });

    await act(async () => {
      fireEvent.click(retryBtn);
    });

    await screen.findByText('Test Event', {}, { timeout: 5000 });
    expect(callCount).toBe(2);
  });

  it('10-second timeout triggers error state (Req 2.6)', async () => {
    jest.useFakeTimers();

    global.fetch = jest.fn((_url: string, options?: RequestInit) =>
      new Promise((_resolve, reject) => {
        const signal = options?.signal;
        if (signal) {
          signal.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'));
          });
        }
      })
    ) as jest.Mock;

    await act(async () => {
      render(<EventCalendarPage />);
    });

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

    await act(async () => {
      jest.advanceTimersByTime(10001);
    });

    // Give React time to process the state update from the rejected promise
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByTestId('error-alert')).toBeInTheDocument();
  });

  // --- Loading state ---

  it('shows loading spinner while fetching (Req 2.7)', () => {
    global.fetch = jest.fn(() => new Promise(() => {})) as jest.Mock;
    render(<EventCalendarPage />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });
});
