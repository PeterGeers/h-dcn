import { buildClubbladRows, CLUBBLAD_COLUMNS } from '../components/ClubbladExport';
import { Event } from '../../../types';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    event_id: 'evt-1',
    name: 'Test Event',
    event_type: 'alv',
    event_category: 'vergadering',
    participation: 'open',
    linked_regio: 'regio_all',
    status: 'published',
    start_date: '2026-06-20',
    end_date: '2026-06-21',
    location: 'Amsterdam',
    slug: 'test-event',
    ...overrides,
  };
}

describe('buildClubbladRows', () => {
  it('keeps published events that start on the from date (inclusive)', () => {
    const rows = buildClubbladRows([makeEvent({ start_date: '2026-06-20' })], '2026-06-20');
    expect(rows).toHaveLength(1);
  });

  it('keeps published events that start after the from date', () => {
    const rows = buildClubbladRows([makeEvent({ start_date: '2026-07-01' })], '2026-06-20');
    expect(rows).toHaveLength(1);
  });

  it('excludes events that start before the from date', () => {
    const rows = buildClubbladRows([makeEvent({ start_date: '2026-06-19' })], '2026-06-20');
    expect(rows).toHaveLength(0);
  });

  it('excludes events that are not published', () => {
    const rows = buildClubbladRows(
      [
        makeEvent({ event_id: 'draft', status: 'draft' }),
        makeEvent({ event_id: 'archived', status: 'archived' }),
        makeEvent({ event_id: 'published', status: 'published' }),
      ],
      '2026-01-01'
    );

    expect(rows).toHaveLength(1);
    expect(rows[0].status).toBe('published');
  });

  it('excludes events without a start_date', () => {
    const rows = buildClubbladRows([makeEvent({ start_date: undefined })], '2026-01-01');
    expect(rows).toHaveLength(0);
  });

  it('returns an empty list when no from date is given', () => {
    expect(buildClubbladRows([makeEvent()], '')).toEqual([]);
  });

  it('uses the required column order as headers', () => {
    const rows = buildClubbladRows([makeEvent()], '2026-01-01');

    expect(Object.keys(rows[0])).toEqual([...CLUBBLAD_COLUMNS]);
    expect(Object.keys(rows[0])).toEqual([
      'start_date',
      'end_date',
      'name',
      'event_category',
      'event_type',
      'linked_regio',
      'location',
      'participation',
      'slug',
      'status',
    ]);
  });

  it('renders missing values as empty strings', () => {
    const rows = buildClubbladRows(
      [makeEvent({ slug: undefined, location: undefined, event_category: undefined })],
      '2026-01-01'
    );

    expect(rows[0].slug).toBe('');
    expect(rows[0].location).toBe('');
    expect(rows[0].event_category).toBe('');
  });

  it('sorts rows by start_date ascending', () => {
    const rows = buildClubbladRows(
      [
        makeEvent({ event_id: 'b', start_date: '2026-09-01' }),
        makeEvent({ event_id: 'a', start_date: '2026-07-01' }),
      ],
      '2026-01-01'
    );

    expect(rows.map((row) => row.start_date)).toEqual(['2026-07-01', '2026-09-01']);
  });
});