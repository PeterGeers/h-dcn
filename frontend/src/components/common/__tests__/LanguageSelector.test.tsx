/**
 * LanguageSelector unit tests.
 *
 * Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { LanguageSelector } from '../LanguageSelector';
import {
  SUPPORTED_LOCALES,
  LOCALE_NAMES,
  LOCALE_FLAGS,
} from '../../../i18n/constants';

// --- Mocks ---

const mockChangeLanguage = jest.fn().mockResolvedValue(undefined);
const mockToast = jest.fn();
const mockPut = jest.fn();

let mockLanguage = 'nl';
let mockIsAuthenticated = true;

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: {
      get language() {
        return mockLanguage;
      },
      changeLanguage: mockChangeLanguage,
    },
    t: (key: string) => key,
  }),
}));

jest.mock('../../../context/AuthProvider', () => ({
  useAuth: () => ({
    isAuthenticated: mockIsAuthenticated,
  }),
}));

jest.mock('../../../services/apiService', () => ({
  ApiService: {
    put: (...args: any[]) => mockPut(...args),
  },
}));

jest.mock('@chakra-ui/react', () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const mockReact = require('react');
  return {
    Menu: ({ children }: any) => mockReact.createElement('div', { 'data-testid': 'menu' }, children),
    MenuButton: mockReact.forwardRef(({ children, as: _as, ...props }: any, ref: any) =>
      mockReact.createElement('button', { ref, role: 'button', ...props }, children)
    ),
    MenuList: ({ children }: any) => mockReact.createElement('div', { role: 'menu' }, children),
    MenuItem: ({ children, onClick, fontWeight, icon, ...props }: any) =>
      mockReact.createElement('div', { role: 'menuitem', onClick, style: { fontWeight }, ...props }, icon, children),
    Button: mockReact.forwardRef(({ children, ...props }: any, ref: any) =>
      mockReact.createElement('button', { ref, ...props }, children)
    ),
    Text: ({ children, ...props }: any) => mockReact.createElement('span', props, children),
    HStack: ({ children }: any) => mockReact.createElement('span', null, children),
    useToast: () => mockToast,
  };
});

jest.mock('@chakra-ui/icons', () => ({
  ChevronDownIcon: () => require('react').createElement('span', { 'data-testid': 'chevron-icon' }),
  CheckIcon: (props: any) => require('react').createElement('span', { 'data-testid': 'check-icon', ...props }),
}));

// --- Helpers ---

function renderComponent() {
  return render(<LanguageSelector />);
}

async function openMenu(user: ReturnType<typeof userEvent.setup>) {
  const button = screen.getByRole('button', { name: /select language/i });
  await user.click(button);
}

// --- Tests ---

describe('LanguageSelector', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLanguage = 'nl';
    mockIsAuthenticated = true;
    mockPut.mockResolvedValue({ success: true });
  });

  describe('Rendering all 8 locales with flags and native names (Req 3.2)', () => {
    it('renders the menu button with the active locale flag and name', () => {
      renderComponent();

      const button = screen.getByRole('button', { name: /select language/i });
      expect(button).toBeInTheDocument();
      expect(button).toHaveTextContent(LOCALE_FLAGS.nl);
      expect(button).toHaveTextContent(LOCALE_NAMES.nl);
    });

    it('displays all 8 locales in the expanded menu', async () => {
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const menuItems = screen.getAllByRole('menuitem');
      for (const locale of SUPPORTED_LOCALES) {
        const item = menuItems.find((el) =>
          el.textContent?.includes(LOCALE_NAMES[locale]) &&
          el.textContent?.includes(LOCALE_FLAGS[locale])
        );
        expect(item).toBeDefined();
      }
    });

    it('shows all 8 menu items', async () => {
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const menuItems = screen.getAllByRole('menuitem');
      expect(menuItems).toHaveLength(8);
    });
  });

  describe('Active locale highlighting (Req 3.3)', () => {
    it('shows the active locale with bold font weight', async () => {
      mockLanguage = 'en';
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const menuItems = screen.getAllByRole('menuitem');
      const englishItem = menuItems.find((item) =>
        item.textContent?.includes(LOCALE_NAMES.en)
      );
      expect(englishItem).toHaveStyle({ fontWeight: 'bold' });
    });

    it('shows non-active locales with normal font weight', async () => {
      mockLanguage = 'en';
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const menuItems = screen.getAllByRole('menuitem');
      const dutchItem = menuItems.find((item) =>
        item.textContent?.includes(LOCALE_NAMES.nl)
      );
      expect(dutchItem).toHaveStyle({ fontWeight: 'normal' });
    });

    it('sets aria-current="true" on the active locale menu item', async () => {
      mockLanguage = 'fr';
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const menuItems = screen.getAllByRole('menuitem');
      const frenchItem = menuItems.find((item) =>
        item.textContent?.includes(LOCALE_NAMES.fr)
      );
      expect(frenchItem).toHaveAttribute('aria-current', 'true');
    });

    it('does not set aria-current on non-active locales', async () => {
      mockLanguage = 'fr';
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const menuItems = screen.getAllByRole('menuitem');
      const dutchItem = menuItems.find((item) =>
        item.textContent?.includes(LOCALE_NAMES.nl)
      );
      expect(dutchItem).not.toHaveAttribute('aria-current');
    });

    it('displays the collapsed button with the current active locale', () => {
      mockLanguage = 'de';
      renderComponent();

      const button = screen.getByRole('button', { name: /select language/i });
      expect(button).toHaveTextContent(LOCALE_FLAGS.de);
      expect(button).toHaveTextContent(LOCALE_NAMES.de);
    });
  });

  describe('Keyboard navigation accessibility (Req 3.5)', () => {
    it('menu button is focusable with keyboard', () => {
      renderComponent();

      const button = screen.getByRole('button', { name: /select language/i });
      button.focus();
      expect(button).toHaveFocus();
    });

    it('menu button has accessible aria-label', () => {
      renderComponent();

      const button = screen.getByRole('button', { name: /select language/i });
      expect(button).toHaveAttribute('aria-label', 'Select language');
    });

    it('menu opens on Enter key press', async () => {
      const user = userEvent.setup();
      renderComponent();

      const button = screen.getByRole('button', { name: /select language/i });
      button.focus();
      await user.keyboard('{Enter}');

      // Menu should be open — menu items visible
      await waitFor(() => {
        expect(screen.getAllByRole('menuitem').length).toBe(8);
      });
    });
  });

  describe('Language switch triggers i18n.changeLanguage (Req 3.4)', () => {
    it('calls i18n.changeLanguage with selected locale', async () => {
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const frenchItem = screen.getByText(LOCALE_NAMES.fr).closest('[role="menuitem"]');
      await user.click(frenchItem!);

      expect(mockChangeLanguage).toHaveBeenCalledWith('fr');
    });

    it('does not call changeLanguage when selecting the already active locale', async () => {
      mockLanguage = 'nl';
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const menuItems = screen.getAllByRole('menuitem');
      const dutchItem = menuItems.find((item) =>
        item.textContent?.includes(LOCALE_NAMES.nl)
      );
      await user.click(dutchItem!);

      expect(mockChangeLanguage).not.toHaveBeenCalled();
    });

    it('persists language preference via API when authenticated', async () => {
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const germanItem = screen.getByText(LOCALE_NAMES.de).closest('[role="menuitem"]');
      await user.click(germanItem!);

      await waitFor(() => {
        expect(mockPut).toHaveBeenCalledWith('/members/me', {
          preferred_language: 'de',
        });
      });
    });

    it('does not call API when user is not authenticated', async () => {
      mockIsAuthenticated = false;
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const englishItem = screen.getByText(LOCALE_NAMES.en).closest('[role="menuitem"]');
      await user.click(englishItem!);

      expect(mockChangeLanguage).toHaveBeenCalledWith('en');
      expect(mockPut).not.toHaveBeenCalled();
    });
  });

  describe('Error toast on persist failure (Req 3.6)', () => {
    it('shows a toast when API persist fails with unsuccessful response', async () => {
      mockPut.mockResolvedValue({ success: false, error: 'Server error' });
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const spanishItem = screen.getByText(LOCALE_NAMES.es).closest('[role="menuitem"]');
      await user.click(spanishItem!);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 'warning',
            isClosable: true,
          })
        );
      });
    });

    it('shows a toast when API persist throws an exception', async () => {
      mockPut.mockRejectedValue(new Error('Network error'));
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const italianItem = screen.getByText(LOCALE_NAMES.it).closest('[role="menuitem"]');
      await user.click(italianItem!);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 'warning',
            isClosable: true,
          })
        );
      });
    });

    it('still applies language change locally even when persist fails', async () => {
      mockPut.mockRejectedValue(new Error('Network error'));
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const swedishItem = screen.getByText(LOCALE_NAMES.sv).closest('[role="menuitem"]');
      await user.click(swedishItem!);

      // changeLanguage is called BEFORE the API call (instant feedback)
      expect(mockChangeLanguage).toHaveBeenCalledWith('sv');
    });

    it('does not show toast when API persist succeeds', async () => {
      mockPut.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      renderComponent();
      await openMenu(user);

      const danishItem = screen.getByText(LOCALE_NAMES.da).closest('[role="menuitem"]');
      await user.click(danishItem!);

      await waitFor(() => {
        expect(mockPut).toHaveBeenCalled();
      });

      expect(mockToast).not.toHaveBeenCalled();
    });
  });
});
