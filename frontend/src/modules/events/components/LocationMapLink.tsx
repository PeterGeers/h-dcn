import React from 'react';
import { Link, Icon, Text, HStack } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';

/**
 * Custom map pin icon using Chakra UI's Icon component with a custom SVG path.
 * No external icon library dependencies needed.
 */
const MapPinIcon = (props: any) => (
  <Icon viewBox="0 0 24 24" {...props}>
    <path
      fill="currentColor"
      d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"
    />
  </Icon>
);

export interface LocationMapLinkProps {
  /** The raw location string from the event record */
  location: string | null | undefined;
  /** Font size to pass through to the link */
  fontSize?: string;
  /** Text color to pass through to the link */
  color?: string;
  /** Maximum width for truncation */
  maxW?: string;
  /** Whether to truncate the text */
  isTruncated?: boolean;
}

/**
 * LocationMapLink renders a clickable location that opens Google Maps search
 * in a new tab. Returns null if location is empty/null/whitespace-only.
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 3.1, 5.1, 5.2, 5.3, 5.4
 */
const LocationMapLink: React.FC<LocationMapLinkProps> = ({
  location,
  fontSize,
  color,
  maxW,
  isTruncated,
}) => {
  const { t } = useTranslation('eventBooking');

  // Guard: render nothing for null, undefined, empty, or whitespace-only
  if (!location || !location.trim()) {
    return null;
  }

  const trimmedLocation = location.trim();
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(trimmedLocation)}`;

  return (
    <Link
      href={mapsUrl}
      isExternal
      onClick={(e) => e.stopPropagation()}
      aria-label={t('location.openInMaps', { location: trimmedLocation })}
      fontSize={fontSize}
      color={color}
      _hover={{ textDecoration: 'underline' }}
      display="inline-flex"
      alignItems="center"
      maxW={maxW}
    >
      <HStack spacing={1} maxW={maxW}>
        <MapPinIcon boxSize="1em" flexShrink={0} />
        <Text
          as="span"
          isTruncated={isTruncated}
          maxW={maxW ? `calc(${maxW} - 1.2em)` : undefined}
        >
          {trimmedLocation}
        </Text>
      </HStack>
    </Link>
  );
};

export default LocationMapLink;
