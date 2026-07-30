import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import LocationMapLink from '../components/LocationMapLink';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (key === 'location.openInMaps' && opts?.location) {
        return `Open ${opts.location} in Google Maps (opens in new tab)`;
      }
      return key;
    },
    i18n: { language: 'en' },
  }),
}));

const renderWithChakra = (ui: React.ReactElement) =>
  render(<ChakraProvider>{ui}</ChakraProvider>);

describe('LocationMapLink', () => {
  describe('renders link with correct href for a valid location', () => {
    it('constructs a Google Maps search URL with encoded location', () => {
      renderWithChakra(<LocationMapLink location="Amsterdam" />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'href',
        'https://www.google.com/maps/search/?api=1&query=Amsterdam'
      );
    });

    it('trims whitespace before constructing the URL', () => {
      renderWithChakra(<LocationMapLink location="  Den Bosch  " />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'href',
        'https://www.google.com/maps/search/?api=1&query=Den%20Bosch'
      );
    });
  });

  describe('renders nothing for invalid locations', () => {
    it('renders nothing for null', () => {
      renderWithChakra(<LocationMapLink location={null} />);
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });

    it('renders nothing for undefined', () => {
      renderWithChakra(<LocationMapLink location={undefined} />);
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });

    it('renders nothing for empty string', () => {
      renderWithChakra(<LocationMapLink location="" />);
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });

    it('renders nothing for whitespace-only string', () => {
      renderWithChakra(<LocationMapLink location="   " />);
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });

    it('renders nothing for tab/newline whitespace', () => {
      renderWithChakra(<LocationMapLink location={'\t\n  '} />);
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });
  });

  describe('encodes special characters correctly', () => {
    it('encodes spaces as %20', () => {
      renderWithChakra(<LocationMapLink location="Den Bosch" />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'href',
        'https://www.google.com/maps/search/?api=1&query=Den%20Bosch'
      );
    });

    it('encodes accented characters (Café)', () => {
      renderWithChakra(<LocationMapLink location="Café 't Centrum" />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'href',
        `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent("Café 't Centrum")}`
      );
    });

    it('encodes umlauts (ü)', () => {
      renderWithChakra(<LocationMapLink location="Mühlenbergstraße" />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'href',
        `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent('Mühlenbergstraße')}`
      );
    });
  });

  describe('event propagation', () => {
    it('calls stopPropagation on click', () => {
      renderWithChakra(<LocationMapLink location="Amsterdam" />);

      const link = screen.getByRole('link');
      const clickEvent = new MouseEvent('click', { bubbles: true });
      const stopPropagationSpy = jest.spyOn(clickEvent, 'stopPropagation');

      fireEvent(link, clickEvent);

      expect(stopPropagationSpy).toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('aria-label contains the location text', () => {
      renderWithChakra(<LocationMapLink location="Clubhuis H-DCN" />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'aria-label',
        'Open Clubhuis H-DCN in Google Maps (opens in new tab)'
      );
    });

    it('aria-label uses trimmed location text', () => {
      renderWithChakra(<LocationMapLink location="  Amsterdam  " />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'aria-label',
        'Open Amsterdam in Google Maps (opens in new tab)'
      );
    });
  });

  describe('map pin icon', () => {
    it('renders an SVG icon with the map pin path', () => {
      renderWithChakra(<LocationMapLink location="Amsterdam" />);

      const link = screen.getByRole('link');
      const svg = link.querySelector('svg');
      expect(svg).toBeInTheDocument();

      const path = svg?.querySelector('path');
      expect(path).toBeInTheDocument();
      expect(path).toHaveAttribute('fill', 'currentColor');
    });
  });

  describe('external link attributes', () => {
    it('sets target="_blank"', () => {
      renderWithChakra(<LocationMapLink location="Amsterdam" />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('target', '_blank');
    });

    it('sets rel containing noopener', () => {
      renderWithChakra(<LocationMapLink location="Amsterdam" />);

      const link = screen.getByRole('link');
      const rel = link.getAttribute('rel');
      expect(rel).toContain('noopener');
    });
  });
});
