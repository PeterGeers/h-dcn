import React, { useMemo, useState } from 'react';
import { HStack, Input, Text } from '@chakra-ui/react';
import CSVExportButton from './CSVExportButton';
import { Event } from '../../../types';

/**
 * Clubblad export — "evenementen administratie >> Evenementen".
 *
 * Produces `evenementen_clubblad.csv` with a fixed column order, containing only
 * events that are published and have a start_date on or after a selected date.
 */

/** Fixed column order required by the clubblad export. */
export const CLUBBLAD_COLUMNS = [
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
] as const;

/** Today as YYYY-MM-DD — the format `<input type="date">` uses. */
export function todayIso(): string {
  return new Date().toISOString().split('T')[0];
}

/**
 * Build the clubblad CSV rows.
 *
 * Selector: `status === 'published'` AND `start_date` on or after `fromDate`
 * (inclusive — "events starting from date"). ISO dates (YYYY-MM-DD) compare
 * correctly as plain strings, so no Date parsing is needed.
 */
export function buildClubbladRows(events: Event[], fromDate: string): Record<string, string>[] {
  if (!fromDate) return [];

  return events
    .filter(
      (event) =>
        event.status === 'published' &&
        typeof event.start_date === 'string' &&
        event.start_date !== '' &&
        event.start_date >= fromDate
    )
    .sort((a, b) => (a.start_date || '').localeCompare(b.start_date || ''))
    .map((event) => {
      const source = event as Record<string, unknown>;
      const row: Record<string, string> = {};
      CLUBBLAD_COLUMNS.forEach((column) => {
        const value = source[column];
        row[column] = value === undefined || value === null ? '' : String(value);
      });
      return row;
    });
}

interface ClubbladExportProps {
  events: Event[];
  canExport: boolean;
}

function ClubbladExport({ events, canExport }: ClubbladExportProps) {
  const [fromDate, setFromDate] = useState<string>(todayIso());

  const rows = useMemo(() => buildClubbladRows(events, fromDate), [events, fromDate]);

  return (
    <HStack spacing={2} align="center" flexWrap="wrap">
      <Text fontSize="sm" color="gray.300" whiteSpace="nowrap">
        Publicaties vanaf
      </Text>
      <Input
        type="date"
        size="sm"
        w="150px"
        aria-label="Publicaties vanaf"
        value={fromDate}
        onChange={(e) => setFromDate(e.target.value)}
        bg="gray.700"
        color="white"
        borderColor="orange.400"
      />
      <CSVExportButton
        data={rows}
        filename="evenementen_clubblad"
        columns={[...CLUBBLAD_COLUMNS]}
        includeDate={false}
        label="Export clubblad CSV"
        disabled={!canExport || rows.length === 0}
        title={
          !canExport
            ? 'Je hebt geen export-rechten voor evenementen.'
            : `${rows.length} gepubliceerde evenementen vanaf ${fromDate}`
        }
      />
      <Text fontSize="xs" color="gray.400" whiteSpace="nowrap">
        {rows.length} evenement(en)
      </Text>
    </HStack>
  );
}

export default ClubbladExport;
